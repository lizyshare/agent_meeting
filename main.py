import json
import time  # 导入时间模块
from meeting.preprocess import preprocess_text
from meeting.summary import generate_summary
from meeting.introduction import generate_intro
from meeting.asr import audio_to_text

def main():
    # 1. 语音转文字（示例：处理音频文件）
    try:
        print("开始语音转文字...")
        start_time = time.time()  # 记录开始时间
        
        meeting_text = audio_to_text("dataset/interview.m4a")  # 调用asr模块
        
        end_time = time.time()  # 记录结束时间
        elapsed = end_time - start_time  # 计算耗时
        print(f"语音转文字完成，内容长度: {len(meeting_text)}, 耗时: {elapsed:.2f}秒")
        
        # 将生成的文本保存到文件
        # meeting_text_file = "output/meeting_text.txt"
        # with open(meeting_text_file, 'w', encoding='utf-8') as f:
        #     f.write(meeting_text)
    except Exception as e:
        print(f"语音转文字失败: {e}")
        return

    # 2. 预处理文本
    try:
        print("开始文本预处理...")
        start_time = time.time()  # 记录开始时间
        
        processed_text = preprocess_text(
            meeting_text=meeting_text,
            chunk_size=120  # 可自定义分块大小
        )
        
        end_time = time.time()  # 记录结束时间
        elapsed = end_time - start_time  # 计算耗时
        print(f"预处理完成, 耗时: {elapsed:.2f}秒")
        
        # 将处理后的文本保存到文件
        processed_text_file = "output/processed_text.txt"
        with open(processed_text_file, 'w', encoding='utf-8') as f:
            f.write(processed_text)
    except Exception as e:
        print(f"预处理失败: {e}")
        return

    # 3. 生成会议摘要
    try:
        print("开始生成会议摘要...")
        start_time = time.time()  # 记录开始时间
        
        summary = generate_summary(
            meeting_text=processed_text,
            interval_minutes=30  # 时间间隔
        )
        
        end_time = time.time()  # 记录结束时间
        elapsed = end_time - start_time  # 计算耗时
        print(f"摘要生成完成!, 耗时: {elapsed:.2f}秒")
        
        summary_file = "output/summary_text.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(summary, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"摘要生成失败: {e}")
        return

    # 4. 生成会议介绍
    try:
        print("开始生成会议介绍...")
        start_time = time.time()  # 记录开始时间
        
        intro = generate_intro(
            meeting_text=processed_text,
            time_interval=25  # 章节间隔
        )
        
        end_time = time.time()  # 记录结束时间
        elapsed = end_time - start_time  # 计算耗时
        print(f"会议介绍生成完成!, 耗时: {elapsed:.2f}秒")
        
        intro_file = "output/introduction_text.txt"
        with open(intro_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(intro, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"会议介绍生成失败: {e}")
        return

if __name__ == "__main__":
    main()