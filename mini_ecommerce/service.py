# -*- coding: utf-8 -*-
"""客服主流程：意图识别 -> RAG 检索 -> 记忆 -> 摘要 -> 生成回答"""
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .intent import IntentRecognizer
from .memory import ChatHistoryManager
from .rag import KnowledgeBase
from .prompt import ANSWER_PROMPT

INTENT_LABELS = {
    "track_shipping": "物流查询",
    "change_address": "修改收货地址",
    "refund": "退货退款",
    "complaint": "投诉",
    "general": "其他/闲聊",
}


class CustomerService:
    def __init__(self, api_key: str, session_id: str = "default") -> None:
        self.llm = ChatTongyi(
            model="qwen-plus",
            streaming=True,
            dashscope_api_key=api_key,
        )
        self.intent_recognizer = IntentRecognizer(self.llm)
        self.memory = ChatHistoryManager(session_id)
        self.kb = KnowledgeBase(api_key)
        self.answer_chain = (
            ChatPromptTemplate.from_messages([("system", ANSWER_PROMPT)])
            | self.llm
            | StrOutputParser()
        )

    def reply(self, user_input: str):
        """流式生成回答，yield 文本块"""
        # 1. 意图识别（结合最近会话）
        result = self.intent_recognizer.recognize(
            user_input=user_input,
            chat_history=self.memory.format_history(),
        )

        # 2. 更新事实存储（订单号/地址可跨轮继承）
        self.memory.update_facts(result.slots)
        facts = self.memory.get_facts()
        if facts.get("order_id"):
            result.slots.setdefault("order_id", facts["order_id"])
        if facts.get("new_address"):
            result.slots.setdefault("new_address", facts["new_address"])

        # 3. RAG 检索：用用户输入 + 意图作为查询
        query = user_input + " " + " ".join(
            INTENT_LABELS.get(i, i) for i in result.intents
        )
        context = self.kb.retrieve(query, k=3)

        # 4. 构造生成 Prompt
        intent_info = (
            f"意图：{[INTENT_LABELS.get(i, i) for i in result.intents]}；"
            f"订单号：{result.slots.get('order_id') or '未提供'}；"
            f"新地址：{result.slots.get('new_address') or '未提供'}；"
            f"置信度：{result.confidence:.2f}"
        )
        recent = self.memory.format_history()

        # 5. 写入用户消息
        self.memory.add_user_message(user_input)

        # 6. 流式生成并收集完整回答
        full_reply = ""
        try:
            for chunk in self.answer_chain.stream({
                "context": context,
                "summary": self.memory.get_summary() or "（暂无）",
                "recent_history": recent or "（暂无）",
                "user_input": user_input,
                "intent_info": intent_info,
            }):
                full_reply += chunk
                yield chunk
        finally:
            if full_reply:
                self.memory.add_ai_message(full_reply)
                # 7. 达到阈值触发增量摘要
                self.memory.maybe_summarize(self.llm)

    def get_summary(self) -> str:
        return self.memory.get_summary()

    def get_facts(self) -> dict:
        return self.memory.get_facts()
