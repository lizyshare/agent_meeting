from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
import re
import json
import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel

# 加载环境变量
load_dotenv()
api_key = os.getenv("DEFAULT_API_KEY")
endpoint = "https://api.deepseek.com/chat/completions"

# 初始化FastAPI应用
app = FastAPI()

class SummaryRequest(BaseModel):
    # 将interval_minutes设为可选字段，提供默认值
    interval_minutes: int = 30
    meeting_text: str

def split_by_interval(content: str, interval_minutes: int = 30) -> list:
    """按时间间隔分割会议内容"""
    records = []
    lines = content.split('\n')
    date_str = None  # 初始化日期变量
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 匹配日期行
        date_match = re.match(r'^日期：(\d{4}-\d{2}-\d{2})$', line)
        if date_match:
            date_str = date_match.group(1)
            continue
        
        # 匹配时间、发言人和内容（时间格式为MM:SS）
        time_match = re.match(r'^(\d{2}:\d{2}) 发言人(\d+): (.+)$', line)
        if time_match and date_str:  # 确保已获取日期
            time_str, spk, content = time_match.groups()
            
            try:
                # 解析MM:SS格式的时间
                mm, ss = map(int, time_str.split(':'))
                
                # 验证秒数是否符合60进制
                if ss < 0 or ss >= 60:
                    raise ValueError(f"无效的秒数: {ss}")
                
                # 构建基础时间（日期 + 00:00:00）
                base_time = datetime.strptime(date_str, "%Y-%m-%d")
                
                # 计算实际时间：基础时间 + 分钟 + 秒
                actual_time = base_time + timedelta(minutes=mm, seconds=ss)
                
                records.append({
                    "name": f"发言人{spk}",
                    "time": actual_time,
                    "content": content
                })
            except ValueError as e:
                print(f"跳过格式错误的行: {line}, 错误: {e}")
                continue
    
    if not records:
        return []
    
    # 按时间间隔分组
    start_time = records[0]["time"]
    intervals = []
    current_interval = {
        "start": start_time,
        "end": start_time,
        "content": [],
        "reporters": set()
    }
    
    for record in records:
        # 计算与开始时间的分钟差
        time_diff = (record["time"] - start_time).total_seconds() / 60
        if time_diff > interval_minutes * (len(intervals) + 1):
            current_interval["end"] = record["time"]
            intervals.append(current_interval)
            current_interval = {
                "start": record["time"],
                "end": record["time"],
                "content": [record["content"]],
                "reporters": {record["name"]}
            }
        else:
            current_interval["content"].append(record["content"])
            current_interval["reporters"].add(record["name"])
            current_interval["end"] = record["time"]
    
    if current_interval["content"]:
        intervals.append(current_interval)
    
    # 格式化区间信息，显示为MM:SS格式
    formatted_intervals = []
    for i, interval in enumerate(intervals):
        # 格式化开始时间为MM:SS
        start_minute = interval["start"].hour * 60 + interval["start"].minute
        start_str = f"{start_minute:02d}:{interval['start'].second:02d}"
        
        # 格式化结束时间为MM:SS
        end_minute = interval["end"].hour * 60 + interval["end"].minute
        end_str = f"{end_minute:02d}:{interval['end'].second:02d}"
        
        formatted_intervals.append({
            "id": i + 1,
            "time_range": f"{start_str}-{end_str}",
            "content": "\n".join(interval["content"]),
            "reporters": list(interval["reporters"])
        })
    
    return formatted_intervals

def call_api(system_prompt: str, user_input: str) -> dict:
    """调用DeepSeek API（内部工具函数）"""
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

def generate_summary(meeting_text: str, interval_minutes: int = 30) -> dict:
    """生成会议摘要核心函数"""
    # 加载提示词
    prompt_file = "prompt/summary.txt"
    if not os.path.exists(prompt_file):
        # 为了测试方便，如果提示词文件不存在，使用默认提示词
        system_prompt = "请总结会议内容，提取关键议题、讨论结果和行动计划。"
    else:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            system_prompt = f.read()
    
    # 分割会议内容
    time_intervals = split_by_interval(meeting_text, interval_minutes)
    if not time_intervals:
        raise ValueError("无法解析会议内容，未提取到有效时间区间")
    
    # 构造API输入
    processed_input = (
        f"以下是按{interval_minutes}分钟区间划分的会议内容，请据此生成议题：\n"
        f"{json.dumps(time_intervals, ensure_ascii=False, indent=2)}\n\n"
        f"原始完整记录：\n{meeting_text}"
    )
    
    # 调用API并解析结果
    api_result = call_api(system_prompt, processed_input)
    for choice in api_result.get('choices', []):
        message_content = choice.get('message', {}).get('content')
        if message_content:
            try:
                return json.loads(message_content)
            except json.JSONDecodeError:
                # 如果返回的不是JSON，直接返回文本内容
                return {"summary": message_content}
    
    raise ValueError("API未返回有效内容")

# FastAPI接口
@app.post("/summary")
async def summary_api(request: SummaryRequest):
    try:
        return generate_summary(request.meeting_text, request.interval_minutes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 运行服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
