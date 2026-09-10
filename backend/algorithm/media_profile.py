"""用于笔记处理的轻量视频：720p / 10 fps，原子替换且保留音轨。"""
import json
import math
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from fractions import Fraction

from backend.runtime import paths

PROFILE = '720p-10fps-h264-v2'
THREADS = max(1, min(4, (os.cpu_count() or 4) // 2))
# 课件视频帧率降到 10 后，CRF 28 + medium 的画质与 CRF 24 + veryfast 相当或更好，
# 体积却小两成以上（AV1、低码率源尤其明显）。若 CRF 28 结果仍大于原文件，再试一次
# CRF 32；都不行则保留原件，避免"压缩"反而撑大存储或过度损伤画质。
ENCODE_ATTEMPTS = ((28, 'medium'), (32, 'medium'))


def ffmpeg_command(*args):
    # -threads 在 -i 前约束解码器；编码器线程须在输出选项处另行设置。
    prefix = ['nice', '-n', '10'] if os.name == 'posix' and shutil.which('nice') else []
    return prefix + [paths.ffmpeg_path(), '-hide_banner', '-nostdin', '-y',
                     '-threads', str(THREADS), '-filter_threads', '1'] + list(args)


def probe_video(path):
    result = subprocess.run(
        [paths.ffprobe_path(), '-v', 'error', '-show_streams', '-show_format',
         '-of', 'json', str(path)], capture_output=True, text=True, timeout=30,
    )
    if result.returncode:
        raise RuntimeError(f'无法读取视频信息: {result.stderr[-1000:]}')
    data = json.loads(result.stdout)
    video = next((s for s in data['streams'] if s['codec_type'] == 'video'
                  and not s.get('disposition', {}).get('attached_pic')), None)
    if not video:
        raise ValueError('文件不包含可处理的视频轨')
    audio = next((s for s in data['streams'] if s['codec_type'] == 'audio'), None)
    duration = float(video.get('duration') or data['format'].get('duration') or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('视频时长无效')
    rate = video.get('avg_frame_rate') or video.get('r_frame_rate') or '0/1'
    try:
        fps = float(Fraction(rate))
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    rotation = next((float(s['rotation']) for s in video.get('side_data_list', [])
                     if 'rotation' in s), float(video.get('tags', {}).get('rotate', 0)))
    width, height = int(video['width']), int(video['height'])
    try:
        sar = float(Fraction(video.get('sample_aspect_ratio', '1:1').replace(':', '/')))
    except (ValueError, ZeroDivisionError):
        sar = 1.0
    width = max(1, round(width * (sar or 1)))
    if round(rotation) % 180:
        width, height = height, width
    return dict(width=width, height=height, fps=fps, duration=duration,
                video_codec=video['codec_name'], has_audio=audio is not None,
                audio_codec=audio['codec_name'] if audio else None,
                rotation=rotation, sar=sar, format=data['format'].get('format_name', ''))


def run_ffmpeg(command, duration, progress=None):
    """读取真实编码进度；stderr 独立落临时文件，避免管道塞满而挂起。"""
    with tempfile.TemporaryFile() as errors:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors, text=True)
        lines = queue.Queue()

        def read_progress():
            for line in proc.stdout:
                lines.put(line.strip())

        reader = threading.Thread(target=read_progress, daemon=True)
        reader.start()
        deadline = time.monotonic() + max(120, duration * 4)
        try:
            while proc.poll() is None or not lines.empty():
                if time.monotonic() > deadline:
                    raise TimeoutError('视频处理超时')
                try:
                    line = lines.get(timeout=.2)
                except queue.Empty:
                    continue
                if progress and line.startswith('out_time_us='):
                    try:
                        progress(min(.99, max(0, int(line.split('=', 1)[1]) / 1e6 / duration)))
                    except ValueError:
                        pass
            if proc.wait() != 0:
                errors.seek(0, 2)
                errors.seek(max(0, errors.tell() - 2000))
                raise RuntimeError('FFmpeg 处理失败: ' + errors.read().decode(errors='replace'))
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            reader.join(timeout=2)
            proc.stdout.close()


def _attempt_progress(progress, index):
    """把第 N 次编码的进度映射到整体区间，避免重试时进度条回跳。"""
    if not progress:
        return None
    total = len(ENCODE_ATTEMPTS)

    def report(fraction):
        progress(min(.99, (index + fraction) / total))
    return report


def prepare_video(source, destination, progress=None):
    """源文件可与目标相同；永远先写新文件，校验成功后再替换目标 inode。"""
    source, destination = Path(source), Path(destination)
    info = probe_video(source)
    original_bytes = source.stat().st_size
    compliant = (info['width'] <= 1280 and info['height'] <= 720
                 and info['width'] % 2 == 0 and info['height'] % 2 == 0
                 and abs(info['fps'] - 10) < .01 and info['video_codec'] == 'h264'
                 and (not info['has_audio'] or info['audio_codec'] == 'aac')
                 and info['rotation'] % 360 == 0 and info['sar'] == 1
                 and 'mp4' in info['format'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    if compliant and source.resolve() == destination.resolve():
        if progress:
            progress(1.0)
        return dict(path=str(destination), profile=PROFILE, original_bytes=original_bytes,
                    size=original_bytes, reused=True, **info)
    fd, name = tempfile.mkstemp(prefix='.prepare-', suffix='.mp4', dir=destination.parent)
    os.close(fd)
    temporary = Path(name)
    attempts = []
    try:
        if compliant:
            shutil.copy2(source, temporary)
        else:
            factor = min(1, 1280 / info['width'], 720 / info['height'])
            width = max(2, int(info['width'] * factor) // 2 * 2)
            height = max(2, int(info['height'] * factor) // 2 * 2)
            audio_args = (['-c:a', 'copy'] if info['audio_codec'] == 'aac'
                          else ['-c:a', 'aac', '-b:a', '128k'])
            best = None
            for index, (crf, preset) in enumerate(ENCODE_ATTEMPTS):
                fd2, name2 = tempfile.mkstemp(prefix='.encode-', suffix='.mp4',
                                              dir=destination.parent)
                os.close(fd2)
                attempt = Path(name2)
                attempts.append(attempt)
                command = ffmpeg_command(
                    '-i', str(source), '-map', '0:v:0', '-map', '0:a:0?',
                    '-vf', f'fps=10,scale={width}:{height}:flags=lanczos,setsar=1',
                    '-c:v', 'libx264', '-preset', preset, '-crf', str(crf),
                    '-pix_fmt', 'yuv420p', '-threads:v', str(THREADS),
                    *audio_args, '-sn', '-dn', '-movflags', '+faststart',
                    '-progress', 'pipe:1', '-nostats', str(attempt),
                )
                run_ffmpeg(command, info['duration'],
                           _attempt_progress(progress, index) if progress else None)
                size = attempt.stat().st_size
                if best is None or size < best[1]:
                    best = (attempt, size)
                if size < original_bytes:
                    break
            if best[1] >= original_bytes and 'mp4' in info['format']:
                # 源本身已高度压缩（如低码率屏幕录制），加强 CRF 也压不小；
                # 此时保留原文件，宁可不做无损的"压缩"也不撑大存储。
                if source.resolve() != destination.resolve():
                    shutil.copy2(source, destination)
                if progress:
                    progress(1.0)
                return dict(path=str(destination), profile=PROFILE + '-source',
                            original_bytes=original_bytes,
                            size=destination.stat().st_size, reused=False,
                            fallback='encode-not-smaller', **info)
            shutil.move(str(best[0]), str(temporary))
        prepared = probe_video(temporary)
        if (abs(prepared['duration'] - info['duration']) > max(.5, 1 / max(info['fps'], 1))
                or prepared['has_audio'] != info['has_audio']):
            raise RuntimeError('压缩结果的时长或音轨校验失败，原视频已保留')
        os.replace(temporary, destination)
        if progress:
            progress(1.0)
        return dict(path=str(destination), profile=PROFILE, original_bytes=original_bytes,
                    size=destination.stat().st_size, reused=compliant, **prepared)
    finally:
        temporary.unlink(missing_ok=True)
        for attempt in attempts:
            attempt.unlink(missing_ok=True)
