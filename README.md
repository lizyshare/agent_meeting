# 安装环境

pip install funasr

# 执行命令

python main.py

## 结果展示

语音转文字完成，内容长度: 2212, 耗时: 12.13秒
开始文本预处理...
Processing chunk 1/1...
预处理完成, 耗时: 474.89秒
开始生成会议摘要...
摘要生成完成!, 耗时: 95.23秒
开始生成会议介绍...
会议介绍生成完成!, 耗时: 98.81秒

# 子模块运行
python .\meeting\asr.py
python .\meeting\preprocess.py 
python .\meeting\introduction.py
python .\meeting\summary.py

# 接口测试
```
curl --location 'http://localhost:8001/introduction' \
--header 'Content-Type: application/json' \
--data '{
    "meeting_text": "日期：2025-08-26 \n 00:05 发言人1: 大家好，我们开始今天的会议\n00:15 发言人2: 我先介绍一下项目进度\n05:30 发言人1: 这个方案需要修改\n12:45 发言人3: 我同意这个观点\n18:20 发言人2: 预算方面可能有问题\n25:10 发言人1: 我们下次会议再讨论细节 啊哈哈"
  }'
```
