# mini-e-commerce 电商客服 RAG 项目



## 运行

1. 确认已设置环境变量 `DASHSCOPE_API_KEY`
2. 双击 `run.bat`（终端版交互客服）

输入问题回车发送，输入 `exit` 或 `quit` 退出。

## 项目结构

```
mini_ecommerce/
├── prompt.py     # 意图识别 / 摘要 / 回答 的 Prompt 模板
├── intent.py     # 意图识别：5 类意图 + 订单号/新地址槽位抽取 + JSON 容错解析
├── memory.py     # 记忆管理：会话隔离 + 最近 N 轮 + 每 6 轮增量摘要 + 事实存储
├── rag.py        # RAG：电商 FAQ 知识库 + DashScope 嵌入(text-embedding-v4) + FAISS 检索
├── service.py    # 主流程：意图识别 -> 事实继承 -> RAG 召回 -> 流式生成 -> 摘要
└── main.py       # 终端交互入口
```

## 核心流程

```
用户输入
  -> 意图识别（结合最近会话，输出 intents/slots/confidence）
  -> 事实存储（订单号、地址可跨轮继承）
  -> RAG 检索（用户问题 + 意图 -> FAISS 召回 top3 知识）
  -> 构造 Prompt（知识库 + 摘要 + 最近对话 + 意图槽位）
  -> 流式生成回答
  -> 写入历史；每 12 条消息触发一次增量摘要
```

## 已验证

- 意图识别：物流查询、改地址、退款等意图识别准确，订单号抽取正确，支持上下文继承
- RAG 召回：知识库规则正确体现在回答中
- 多轮对话：连续 4 轮问答（查物流 -> 改地址 -> 提供新地址 -> 退款）全流程通过
- 模型：`qwen-plus`（对话）+ `text-embedding-v4`（嵌入，1024 维）
