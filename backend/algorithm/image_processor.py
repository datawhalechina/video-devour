# backend/algorithm/image_processor.py
import os
import shutil
import logging
import config
import re

try:
    import cv2
    from skimage.metrics import structural_similarity as ssim
    import numpy as np

    IMAGE_LIBS_AVAILABLE = True
except ImportError:
    IMAGE_LIBS_AVAILABLE = False
def cv2_imread(filepath, flags=cv2.IMREAD_COLOR):
    """opencv中文路径读取"""
    try:
        return cv2.imdecode(np.fromfile(filepath, dtype=np.uint8), flags)
    except Exception as e:
        logging.error(f"读取图片失败 {filepath}: {e}")
        return None

def _process_single_directory(directory, similarity_threshold=0.8):
    """
    Processes images in a single directory: resize, compare, and delete redundant frames.
    """
    logging.info(f"开始处理目录: {directory}")
    
    image_files = sorted([f for f in os.listdir(directory) if f.endswith('.jpg')])
    
    if not image_files:
        logging.info("该目录下没有找到图片。")
        return

    # First, resize all images
    for filename in image_files:
        filepath = os.path.join(directory, filename)
        try:
            img = cv2_imread(filepath)
            if img is None: continue
            resized_img = cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2), interpolation=cv2.INTER_AREA)
            cv2.imwrite(filepath, resized_img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        except Exception as e:
            logging.error(f"处理图片 {filepath} 时出错: {e}")
            
    # Start deduplication
    i = 0
    while i < len(image_files) - 1:
        img1_path = os.path.join(directory, image_files[i])
        img2_path = os.path.join(directory, image_files[i+1])

        try:
            img1 = cv2_imread(img1_path, cv2.IMREAD_GRAYSCALE)
            img2 = cv2_imread(img2_path, cv2.IMREAD_GRAYSCALE)
            
            if img1 is None or img2 is None:
                i += 1
                continue
            
            similarity = ssim(img1, img2)
            
            if similarity > similarity_threshold:
                os.remove(img2_path)
                logging.info(f"删除冗余图片: {image_files[i+1]} (与 {image_files[i]} 相似度: {similarity:.2f})")
                image_files.pop(i + 1)
            else:
                i += 1
        except Exception as e:
            logging.error(f"比较图片 {image_files[i]} 和 {image_files[i+1]} 时出错: {e}")
            i += 1

    # Ensure at least one image remains
    if not os.listdir(directory) and image_files:
        # Restore the first image if all were deleted
        first_image_original_path = os.path.join(directory, image_files[0])
        # This part is tricky as the file might be gone. The logic should be to prevent deletion instead.
        # Let's adjust the loop condition to prevent deleting the last image.
        # The current logic will retain the first image if all others are similar to it.
        pass
    
    logging.info(f"目录 {directory} 处理完成")

def process_all_frames(output_dir=None):
    """
    处理所有提取的帧，检查依赖并进行去重
    
    Args:
        output_dir (str, optional): 输出目录路径（大文件夹）。如果未提供，使用默认输出目录
    """
    if not IMAGE_LIBS_AVAILABLE:
        logging.warning("跳过帧处理。请安装必要的库: pip install opencv-python-headless scikit-image numpy")
        print("跳过帧处理。请安装必要的库: pip install opencv-python-headless scikit-image numpy")
        return

    # 确定基础目录
    if output_dir is None:
        base_dir = config.OUTPUT_DIR
    else:
        base_dir = output_dir
    
    if not os.path.isdir(base_dir):
        logging.error(f"帧目录 '{base_dir}' 不存在。跳过帧处理。")
        return
        
    logging.info(f"--- 步骤 8: 开始处理和筛选帧 ---")
    logging.info(f"搜索帧目录: {base_dir}")
    
    # 查找所有 frames_ 开头的子目录
    processed_count = 0
    for dir_name in os.listdir(base_dir):
        if dir_name.startswith('frames_'):
            full_path = os.path.join(base_dir, dir_name)
            if os.path.isdir(full_path):
                _process_single_directory(full_path)
                processed_count += 1
    
    if processed_count > 0:
        logging.info(f"--- 图像处理和筛选完成，共处理 {processed_count} 个帧目录 ---")
    else:
        logging.warning("--- 未找到任何帧目录 ---")

def select_keyframes_with_vlm(headings_with_level, output_dir):
    """
    使用VLM为每个二级标题选择最相关的关键帧。

    Args:
        headings_with_level (list[tuple[int, str]]): 包含级别和标题的元组列表。
        output_dir (str): 主输出目录路径。

    Returns:
        dict: 一个字典，将二级标题映射到其选定的关键帧的相对路径。
    """
    logging.info("--- 步骤 9: 开始使用 VLM 选择关键帧 ---")
    try:
        from vlm_handler import VLMHandler
        vlm_handler = VLMHandler()
    except Exception as e:
        logging.error(f"无法初始化VLM处理器，跳过关键帧选择: {e}")
        return {}

    selected_keyframes = {}
    
    # 创建一个专门的目录来存放选定的关键帧
    keyframes_output_dir = os.path.join(output_dir, 'keyframes')
    os.makedirs(keyframes_output_dir, exist_ok=True)
    logging.info(f"选定的关键帧将被复制到: {keyframes_output_dir}")
    
    # 查找所有 frames_ 开头的子目录
    frame_dirs = {}
    for dir_name in os.listdir(output_dir):
        if dir_name.startswith('frames_') and os.path.isdir(os.path.join(output_dir, dir_name)):
            # 从 "frames_01_标题" 中提取 "标题"
            clean_name = '_'.join(dir_name.split('_')[2:])
            frame_dirs[clean_name] = os.path.join(output_dir, dir_name)

    for i, (level, heading) in enumerate(headings_with_level):
        if level != 2:
            continue

        safe_heading = re.sub(r'[\\/*?:"<>|]', "", heading).replace(" ", "_")
        
        # 找到对应的帧目录
        frame_dir = frame_dirs.get(safe_heading)
        if not frame_dir or not os.path.isdir(frame_dir):
            logging.warning(f"未找到标题 '{heading}' 对应的帧目录，跳过。")
            continue

        image_files = sorted([f for f in os.listdir(frame_dir) if f.endswith('.jpg')])

        if not image_files:
            logging.warning(f"目录 '{frame_dir}' 中没有找到图片，无法为标题 '{heading}' 选择关键帧。")
            continue

        if len(image_files) == 1:
            # 如果只有一帧，直接选择它
            best_frame = image_files[0]
            logging.info(f"标题 '{heading}' 只有一帧，直接选定: {best_frame}")
        else:
            # 如果有多帧，使用VLM进行批量评分
            best_score = -1
            best_frame = None
            logging.info(f"为标题 '{heading}' 的 {len(image_files)} 帧进行VLM评分...")

            # 准备所有图片路径
            image_paths = [os.path.join(frame_dir, img) for img in image_files]
            
            # 使用批量评分
            results = vlm_handler.score_frames_batch(image_paths, heading)
            
            # 找出最佳帧
            for image_file, (score, description) in zip(image_files, results):
                if score > best_score:
                    best_score = score
                    best_frame = image_file
            
            if best_frame:
                logging.info(f"为标题 '{heading}' 选定的最佳帧是 '{best_frame}' (得分: {best_score})")
            else:
                logging.warning(f"无法为标题 '{heading}' 确定最佳帧，将默认选择第一帧。")
                best_frame = image_files[0]

        if best_frame:
            source_path = os.path.join(frame_dir, best_frame)
            
            # 为关键帧创建一个清晰、有序的文件名
            keyframe_filename = f"{len(selected_keyframes) + 1:02d}_{safe_heading}.jpg"
            dest_path = os.path.join(keyframes_output_dir, keyframe_filename)
            
            try:
                # 复制文件
                shutil.copy(source_path, dest_path)
                
                # 存储用于Markdown的相对路径
                relative_path = os.path.join('keyframes', keyframe_filename)
                selected_keyframes[heading] = relative_path
                
            except Exception as e:
                logging.error(f"复制关键帧 '{source_path}' 到 '{dest_path}' 失败: {e}")

    logging.info(f"--- VLM 关键帧选择完成，共选定并复制 {len(selected_keyframes)} 帧 ---")
    return selected_keyframes
