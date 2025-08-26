from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import re
import json
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
api_key = os.getenv("DEFAULT_API_KEY")
endpoint = "https://api.deepseek.com/chat/completions"

# 初始化FastAPI应用
app = FastAPI()

class IntroductionRequest(BaseModel):
    time_interval: int = 25
    meeting_text: str

def parse_meeting_content(content: str) -> list:
    """解析会议内容为（时间(总秒数), 发言人, 内容）条目"""
    entries = []
    lines = content.split('\n')
    
    # 解析每行（格式：MM:SS 发言人x: 内容，MM为分钟(无进制限制)，SS为秒(60进制)）
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 匹配时间格式(MM可以是1位或多位数字，SS是两位数字)
        match = re.match(r'^(\d+:\d{2}) 发言人(\d+): (.+)$', line)
        if not match:
            continue
        time_str, spk, content = match.groups()
        
        # 解析MM:SS为总秒数
        mm_ss = time_str.split(':')
        if len(mm_ss) != 2:
            continue  # 格式错误
        try:
            minutes = int(mm_ss[0])
            seconds = int(mm_ss[1])
            if seconds < 0 or seconds >= 60:
                continue  # 秒数必须是60进制(0-59)
        except ValueError:
            continue  # 转换失败
        
        total_seconds = minutes * 60 + seconds
        entries.append((total_seconds, f"发言人{spk}", content))
    
    # 按时间排序（确保条目顺序正确）
    return sorted(entries, key=lambda x: x[0])

def split_by_time_interval(entries: list, interval_minutes: int) -> list:
    """按时间间隔分割条目"""
    if not entries:
        return []
    
    segments = []
    current_segment = [entries[0]]
    start_time = entries[0][0]  # 起始时间(总秒数)
    interval_seconds = interval_minutes * 60  # 转换为秒
    
    for entry in entries[1:]:
        time_diff = entry[0] - start_time
        if time_diff >= interval_seconds:
            segments.append(current_segment)
            current_segment = [entry]
            start_time = entry[0]
        else:
            current_segment.append(entry)
    
    if current_segment:
        segments.append(current_segment)
    return segments

def format_segment(segment: list) -> str:
    """格式化时间段内容为文本"""
    formatted = []
    for total_seconds, speaker, content in segment:
        # 转换总秒数为MM:SS格式
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        time_str = f"{minutes}:{seconds:02d}"  # 秒数补零保持两位
        formatted.append(f"{speaker} {time_str}\n{content}")
    return "\n\n".join(formatted)

def call_api(system_prompt: str, user_input: str) -> dict:
    """调用DeepSeek API"""
    if not api_key:
        raise ValueError("API密钥未配置（请检查环境变量DEFAULT_API_KEY）")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-reasoner",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
    }
    response = requests.post(endpoint, json=data, headers=headers)
    if response.status_code != 200:
        raise Exception(f"API调用失败：状态码{response.status_code}，响应：{response.text}")
    return response.json()

def extract_section_summaries(api_response: dict, num_sections: int) -> list:
    """从API响应中提取指定数量的章节速览"""
    try:
        content = api_response.get('choices', [])[0].get('message', {}).get('content', '')
        start_idx = content.find("### 章节速览")
        if start_idx == -1:
            return []
        
        end_idx = content.find("### 要点回顾", start_idx)
        section_content = content[start_idx:end_idx] if end_idx != -1 else content[start_idx:]
        
        # 按章节分割（假设章节以数字编号）
        sections = re.split(r'\n\d+\.\s', section_content)
        # 过滤空内容并确保数量匹配
        valid_sections = [s.strip() for s in sections if s.strip()]
        
        # 如果提取的章节数与预期不符，返回可用的部分
        if len(valid_sections) > num_sections:
            return valid_sections[:num_sections]
        return valid_sections
        
    except Exception as e:
        print(f"提取章节速览时出错: {e}")
        return []

def generate_intro(meeting_text: str, time_interval: int = 25) -> dict:
    """
    生成会议介绍核心函数
    :param meeting_text: 会议文本内容（带时间戳和发言人）
    :param time_interval: 章节时间间隔（分钟）
    :return: 结构化的会议介绍JSON
    """
    # 加载提示词
    prompt_file = "prompt/introduction.txt"
    if not os.path.exists(prompt_file):
        raise FileNotFoundError(f"提示词文件不存在：{prompt_file}")
    with open(prompt_file, 'r', encoding='utf-8') as f:
        system_prompt = f.read()
    
    # 解析会议内容
    entries = parse_meeting_content(meeting_text)
    if not entries:
        raise ValueError("无法解析会议内容，未提取到有效条目")
    
    # 按时间间隔分割
    segments = split_by_time_interval(entries, time_interval)
    if not segments:
        raise ValueError("未生成有效时间段")
    
    # 仅调用一次API处理完整内容
    full_result = call_api(system_prompt, meeting_text)
    full_content = ""
    for choice in full_result.get('choices', []):
        full_content = choice.get('message', {}).get('content', '')
        break
    
    if not full_content:
        raise ValueError("API返回内容为空")
    
    # 从单次API响应中提取与段数匹配的章节速览
    section_summaries = extract_section_summaries(full_result, len(segments))
    
    # 组合章节速览（如果提取到了）
    if section_summaries:
        start_idx = full_content.find("### 章节速览")
        if start_idx != -1:
            end_idx = full_content.find("### 要点回顾", start_idx)
            if end_idx == -1:
                end_idx = len(full_content)
            
            # 格式化章节速览
            formatted_summaries = []
            for i, summary in enumerate(section_summaries, 1):
                # 获取该章节的时间范围
                start_time = segments[i-1][0][0]
                end_time = segments[i-1][-1][0]
                
                # 转换为MM:SS格式
                start_min = start_time // 60
                start_sec = start_time % 60
                end_min = end_time // 60
                end_sec = end_time % 60
                
                time_range = f"{start_min}:{start_sec:02d} - {end_min}:{end_sec:02d}"
                formatted_summaries.append(f"{i}. 时间段 {time_range}：\n{summary}")
            
            combined_summaries = "\n\n".join(formatted_summaries)
            full_content = (
                full_content[:start_idx] +
                "### 章节速览\n\n" +
                combined_summaries +
                "\n\n" +
                full_content[end_idx:]
            )
    
    # 解析为JSON返回
    try:
        return json.loads(full_content)
    except json.JSONDecodeError:
        raise ValueError("API返回内容不是有效的JSON格式")

# FastAPI接口
@app.post("/introduction")
async def introduction_api(request: IntroductionRequest):
    try:
        return generate_intro(request.meeting_text, request.time_interval)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 服务运行入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
    