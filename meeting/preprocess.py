from fastapi import FastAPI, HTTPException
import requests
import os
from dotenv import load_dotenv
from pydantic import BaseModel

app = FastAPI()

# 加载环境变量
load_dotenv()

# 从环境变量获取API配置
api_key = os.getenv("DEFAULT_API_KEY")
endpoint = os.getenv("DEEPSEEK_ENDPOINT", "https://api.deepseek.com/chat/completions")

# 固定的提示词文件路径
prompt_file = "prompt/preprocess.txt"

# 定义请求体模型（已移除prompt_text参数）
class TextProcessingRequest(BaseModel):
    meeting_text: str  # 输入文本内容
    chunk_size: int = 100  # 每块的行数，默认100行

def split_text_into_chunks(text: str, chunk_size: int):
    """将文本按指定行数分割成块"""
    lines = text.split('\n')
    chunks = []
    
    for i in range(0, len(lines), chunk_size):
        chunk_lines = lines[i:i+chunk_size]
        chunks.append('\n'.join(chunk_lines))
    
    return chunks

def call_api(api_key, endpoint, user_input, system_prompt):
    """调用DeepSeek API处理文本"""
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

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API 调用失败，状态码: {response.status_code}, 响应: {response.text}")

def remove_empty_lines(text: str) -> str:
    """去除文本中的空行"""
    lines = text.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    return '\n'.join(non_empty_lines)

def load_prompt_from_file(file_path: str) -> str:
    """从文件加载提示词"""
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"提示词文件 {file_path} 不存在")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read().strip()

# 新增：允许外部调用的预处理函数
def preprocess_text(meeting_text: str, chunk_size: int = 100) -> str:
    """封装预处理逻辑，供外部调用"""
    try:
        # 复用原有逻辑（验证API密钥、加载提示词、分块处理等）
        if not api_key:
            raise ValueError("API密钥未配置")
        
        system_prompt = load_prompt_from_file(prompt_file)
        if not system_prompt:
            raise ValueError("提示词文件内容为空")
        
        if not meeting_text:
            raise ValueError("输入文本不能为空")
        
        chunks = split_text_into_chunks(meeting_text, chunk_size)
        if not chunks:
            return ""
        
        processed_results = []
        for chunk_num, chunk_content in enumerate(chunks):
            print(f"Processing chunk {chunk_num + 1}/{len(chunks)}...")
            result = call_api(api_key, endpoint, chunk_content, system_prompt)
            
            content_found = False
            for choice in result.get('choices', []):
                message_content = choice.get('message', {}).get('content')
                if message_content:
                    processed_results.append(message_content)
                    content_found = True
                    break
            
            if not content_found:
                processed_results.append("没有找到 'content' 字段")
        
        full_result = '\n'.join(processed_results)
        return remove_empty_lines(full_result)
    except Exception as e:
        raise ValueError(f"预处理失败: {str(e)}")

@app.post("/preprocess")
async def process_text(request: TextProcessingRequest):
    """
    处理文本的API接口
    
    参数:
    - meeting_text: 需要处理的文本内容
    - chunk_size: 每块的行数，默认100行
    
    返回:
    - 处理后的文本结果
    """
    try:
        # 验证API密钥
        if not api_key:
            raise HTTPException(status_code=500, detail="API密钥未配置")
        
        # 加载提示词
        system_prompt = load_prompt_from_file(prompt_file)
        if not system_prompt:
            raise HTTPException(status_code=400, detail="提示词文件内容为空")
        
        # 获取请求参数
        meeting_text = request.meeting_text
        chunk_size = request.chunk_size
        
        # 验证输入文本
        if not meeting_text:
            raise HTTPException(status_code=400, detail="输入文本不能为空")
        
        # 将文本分块
        chunks = split_text_into_chunks(meeting_text, chunk_size)
        if not chunks:
            return {"result": ""}
        
        # 处理每个块并收集结果
        processed_results = []
        for chunk_num, chunk_content in enumerate(chunks):
            print(f"Processing chunk {chunk_num + 1}/{len(chunks)}...")
            result = call_api(api_key, endpoint, chunk_content, system_prompt)
            
            content_found = False
            for choice in result.get('choices', []):
                message_content = choice.get('message', {}).get('content')
                if message_content:
                    processed_results.append(message_content)
                    content_found = True
                    break
            
            if not content_found:
                processed_results.append("没有找到 'content' 字段")
        
        # 合并所有结果
        full_result = '\n'.join(processed_results)
        
        # 去除空行
        cleaned_result = remove_empty_lines(full_result)
        
        return {"result": cleaned_result}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理出错: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
