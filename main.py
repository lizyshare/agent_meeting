from funasr import AutoModel

model = AutoModel(model="paraformer-zh", model_revision="v2.0.4",
                  vad_model="fsmn-vad", vad_model_revision="v2.0.4",
                  punc_model="ct-punc-c", punc_model_revision="v2.0.4",
                  spk_model="cam++", spk_model_revision="v2.0.2",
                  )

res = model.generate(input="dataset/interview.m4a", 
            batch_size_s=300, 
            hotword='')

if 'sentence_info' in res[0]:
    for sentence in res[0]['sentence_info']:
        # 提取开始时间（秒）并转换为MM:SS格式
        start_seconds_ms = sentence['start']
        start_seconds = start_seconds_ms / 1000.0
        minutes = int(start_seconds // 60)
        seconds = int(start_seconds % 60)
        timestamp = f"{minutes:02d}:{seconds:02d}"
        
        # print(f"{timestamp} 发言人{sentence['spk']}: {sentence['text']}")
        # 将对话内容写入txt文件
        with open('dataset/interview.txt', 'a', encoding='utf-8') as f:
            f.write(f"{timestamp} 发言人{sentence['spk']}: {sentence['text']}\n")
else:
    print("未检测到说话人信息，请检查：\n1. 模型配置是否包含spk_embed_postnet设置\n2. 音频是否包含多人对话")