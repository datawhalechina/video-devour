"""字幕块 ID 对齐：模型边界优先，失败时用无需模型的单调词汇对齐。"""
import json
import logging
import re


def extract_outline_alignment(response):
    """分离内部边界信息与可发布 Markdown，损坏或截断的元数据也不落入正文。"""
    marker = re.search(r"<!--\s*chapter-map\s*:", response, re.IGNORECASE)
    if not marker:
        return response.strip(), None
    end = response.find("-->", marker.end())
    markdown = (response[:marker.start()] + (response[end + 3:] if end >= 0 else "")).strip()
    try:
        metadata = json.loads(response[marker.end():end]) if end >= 0 else None
    except (TypeError, ValueError):
        metadata = None
    return markdown, metadata


def _outline_sections(outline):
    headings = []
    sections = []
    for line in outline.splitlines():
        match = re.match(r"^(#+)\s+(.+?)\s*$", line)
        if match:
            level, title = len(match[1]), match[2]
            headings.append(title)
            if level == 2:
                sections.append([title, title])
        elif sections:
            sections[-1][1] += " " + line
    return headings, sections


def _validated_starts(metadata, titles, chunk_count):
    if not isinstance(metadata, list) or len(metadata) != len(titles):
        return None
    starts = []
    for item, title in zip(metadata, titles):
        if not isinstance(item, dict) or item.get("title") != title:
            return None
        chunk_id = item.get("start_chunk_id")
        # bool 属于 int 子类，但不是有效的字幕块 ID。
        if type(chunk_id) is not int or not 1 <= chunk_id <= chunk_count:
            return None
        starts.append(chunk_id - 1)
    if not starts or starts[0] != 0 or any(a >= b for a, b in zip(starts, starts[1:])):
        return None
    return starts


def _terms(text):
    """英文按词、中文按相邻双字匹配，避免引入分词或向量模型依赖。"""
    words = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text.lower())
    terms = set()
    for word in words:
        if re.match(r"[\u4e00-\u9fff]", word) and len(word) > 1:
            terms.update(word[i:i + 2] for i in range(len(word) - 1))
        else:
            terms.add(word)
    return terms


def _local_starts(sections, dialogue):
    """O(章节数 × 字幕块数) 动态规划，每章连续且顺序不倒退。

    字幕足够时每章至少分配一块。无词汇信号时使用位置作为稳定的次级依据；
    字幕比章节少时允许空章节，保留全部字幕且不重复分配。
    """
    count, chapter_count = len(dialogue), len(sections)
    if count < chapter_count:
        return [(i * count + chapter_count - 1) // chapter_count for i in range(chapter_count)]
    section_terms = [_terms(content) for _, content in sections]
    previous = [float("-inf")] * chapter_count
    decisions = []
    for index, chunk in enumerate(dialogue):
        chunk_terms = _terms(chunk.get("text", ""))
        current = [float("-inf")] * chapter_count
        advanced = [False] * chapter_count
        for chapter in range(min(index + 1, chapter_count)):
            overlap = len(chunk_terms & section_terms[chapter])
            score = overlap / max(1, len(chunk_terms))
            # 小权重仅用于相似度打平时，避免所有无信息字幕被挤到一个章节。
            score -= 1e-6 * abs((index + 0.5) / count - (chapter + 0.5) / chapter_count)
            if index == 0 and chapter == 0:
                current[chapter] = score
            elif chapter > 0 and previous[chapter - 1] > previous[chapter]:
                current[chapter] = previous[chapter - 1] + score
                advanced[chapter] = True
            else:
                current[chapter] = previous[chapter] + score
        previous = current
        decisions.append(advanced)
    starts = [0] * chapter_count
    chapter = chapter_count - 1
    for index in range(count - 1, 0, -1):
        if decisions[index][chapter]:
            starts[chapter] = index
            chapter -= 1
    return starts


def align_outline_chunks(outline, dialogue, chapter_starts=None):
    """返回兼容现有流水线的 {标题: [原始字幕块]}，一级标题保持空列表。

    chapter_starts 来自 LLMHandler.chapter_starts。有效边界完整覆盖字幕；
    不可信或缺失的模型元数据完全弃用，使用本地词汇对齐。
    """
    headings, sections = _outline_sections(outline)
    result = {heading: [] for heading in headings}
    if not dialogue or not sections:
        return result
    titles = [title for title, _ in sections]
    starts = _validated_starts(chapter_starts, titles, len(dialogue))
    if starts is None:
        logging.info("章节边界缺失或无效，使用本地单调词汇对齐。")
        starts = _local_starts(sections, dialogue)
    else:
        logging.info("采用模型返回的字幕块边界，已验证顺序及完整覆盖。")
    for title, start, end in zip(titles, starts, starts[1:] + [len(dialogue)]):
        result[title].extend(dialogue[start:end])
    return result
