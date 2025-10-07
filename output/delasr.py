import json

def extract_and_combine_sentences(json_file_path):
    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # 提取所有sentence并拼接
    all_sentences = []
    
    for item in data:
        if "transcript" in item and isinstance(item["transcript"], list):
            for transcript_item in item["transcript"]:
                if "sentence" in transcript_item:
                    all_sentences.append(transcript_item["sentence"])
    
    # 拼接所有句子
    combined_text = ''.join(all_sentences)
    return combined_text

# 使用示例
json_file_path = "asr_results_paraformer_v2.json"  # 替换为你的JSON文件路径
result = extract_and_combine_sentences(json_file_path)
print(result)