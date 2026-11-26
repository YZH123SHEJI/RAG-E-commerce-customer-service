# -*- coding: utf-8 -*-
"""记忆管理模块：会话隔离 + 最近 N 轮 + 增量摘要 + 事实存储"""
from typing import Dict, List

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage

from .prompt import SUMMARY_PROMPT

_session_store: Dict[str, BaseChatMessageHistory] = {}
_summary_store: Dict[str, str] = {}
_fact_store: Dict[str, dict] = {}
_counter_store: Dict[str, int] = {}

SUMMARY_THRESHOLD = 12  # 12 条消息 = 6 轮对话触发一次摘要
RECENT_N = 6            # 回答时携带最近 6 条消息


class ChatHistoryManager:
    """负责对话历史的存储与读取（按 chat_session_id 隔离）"""

    def __init__(self, chat_session_id: str) -> None:
        self.chat_session_id = chat_session_id

    def get_history(self) -> BaseChatMessageHistory:
        if self.chat_session_id not in _session_store:
            _session_store[self.chat_session_id] = InMemoryChatMessageHistory()
        return _session_store[self.chat_session_id]

    def get_messages(self) -> List[BaseMessage]:
        return self.get_history().messages

    def add_user_message(self, content: str) -> None:
        self.get_history().add_user_message(content)
        self._bump_counter()

    def add_ai_message(self, content: str) -> None:
        self.get_history().add_ai_message(content)
        self._bump_counter()

    def get_recent_messages(self, count: int = RECENT_N) -> List[BaseMessage]:
        messages = self.get_messages()
        return messages[-count:] if messages else []

    def get_summary(self) -> str:
        return _summary_store.get(self.chat_session_id, "")

    def get_facts(self) -> dict:
        return _fact_store.get(self.chat_session_id, {}).copy()

    def update_facts(self, slots: dict) -> None:
        facts = _fact_store.setdefault(self.chat_session_id, {})
        for key in ("order_id", "new_address"):
            if slots.get(key):
                facts[key] = slots[key]

    def format_history(self) -> str:
        """把最近消息拼成字符串，供意图识别使用"""
        lines = []
        for msg in self.get_recent_messages():
            role = "用户" if msg.type == "human" else "客服"
            content = msg.content
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            lines.append(f"{role}：{content}")
        return "\n".join(lines)

    def maybe_summarize(self, llm: ChatTongyi) -> bool:
        """达到阈值时生成/合并摘要，返回是否触发"""
        sid = self.chat_session_id
        if _counter_store.get(sid, 0) < SUMMARY_THRESHOLD:
            return False

        messages = self.get_messages()
        old_summary = self.get_summary()
        new_messages = "\n".join(
            f"{'用户' if m.type == 'human' else '客服'}：{m.content}"
            for m in messages
        )

        prompt = SUMMARY_PROMPT.format(
            old_summary=old_summary or "（无）",
            new_messages=new_messages,
        )
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        chain = (
            ChatPromptTemplate.from_messages([("system", prompt)])
            | llm
            | StrOutputParser()
        )
        summary = chain.invoke({})
        _summary_store[sid] = summary.strip()
        _counter_store[sid] = 0
        return True

    def clear(self) -> None:
        sid = self.chat_session_id
        _session_store[sid] = InMemoryChatMessageHistory()
        _summary_store.pop(sid, None)
        _fact_store.pop(sid, None)
        _counter_store.pop(sid, None)

    def _bump_counter(self) -> None:
        sid = self.chat_session_id
        _counter_store[sid] = _counter_store.get(sid, 0) + 1
