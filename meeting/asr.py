from funasr import AutoModel
from datetime import datetime
import os

# 初始化模型
model = AutoModel(
    model="paraformer-zh", model_revision="v2.0.4",
    vad_model="fsmn-vad", vad_model_revision="v2.0.4",
    punc_model="ct-punc-c", punc_model_revision="v2.0.4",
    spk_model="cam++", spk_model_revision="v2.0.2",
)

def audio_to_text(audio_path: str, output_txt: str = "output/interview.txt") -> str:
    """
    语音转文字核心函数
    :param audio_path: 音频文件路径（如 "dataset/interview.m4a"）
    :param output_txt: 输出文本文件路径（默认保存到 output/interview.txt）
    :return: 带时间戳和发言人的识别文本内容
    """
    # 获取当前日期
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # 调用模型识别音频
    res = model.generate(
        input=audio_path,
        batch_size_s=300,
        hotword=''
    )
    
    # 检查是否有说话人信息
    if 'sentence_info' not in res[0]:
        raise ValueError("未检测到说话人信息，请检查：\n1. 模型配置是否包含spk_embed_postnet设置\n2. 音频是否包含多人对话")
    
    # 写入识别结果到文件并拼接返回文本
    full_text = []
    # 写入日期作为第一行
    full_text.append(f"日期：{current_date}")
    
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write(f"日期：{current_date}\n")
    
    # 处理每条语句
    for sentence in res[0]['sentence_info']:
        # 转换开始时间为 MM:SS 格式
        start_seconds = sentence['start'] / 1000.0
        minutes = int(start_seconds // 60)
        seconds = int(start_seconds % 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"
        
        # 生成文本行
        line = f"{timestamp} 发言人{sentence['spk']}: {sentence['text']}"
        full_text.append(line)
        
        # 追加到文件
        with open(output_txt, 'a', encoding='utf-8') as f:
            f.write(f"{line}\n")
    
    # 返回完整文本（按行拼接）
    return '\n'.join(full_text)

if __name__ == "__main__":
    try:
        # 示例：处理默认音频文件
        result = audio_to_text("dataset/interview.m4a")
        print("语音转文字已完成!")
    except Exception as e:
        print(f"处理失败：{str(e)}")