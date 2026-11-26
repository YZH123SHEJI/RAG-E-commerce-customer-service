# -*- coding: utf-8 -*-
"""意图识别模块：识别用户意图 + 抽取槽位（订单号/新地址）"""
import json
import re
from dataclasses import dataclass
from typing import Any

from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .prompt import INTENT_RECOGNIZE_PROMPT

FALLBACK = {"intents": ["general"], "slots": {}, "confidence": 0.0}


@dataclass(frozen=True)
class IntentResult:
    intents: list
    slots: dict
    confidence: float


class IntentRecognizer:
    """通过 LLM 识别意图，输出 JSON 字符串并容错解析"""

    def __init__(self, llm: ChatTongyi) -> None:
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", INTENT_RECOGNIZE_PROMPT),
        ])
        self._chain = self._prompt | llm | StrOutputParser()

    def recognize(self, user_input: str, chat_history: str = "") -> IntentResult:
        text = self._chain.invoke(
            input={"history": chat_history or "", "user_input": user_input}
        )
        data = self._parse(text)

        intents = data.get("intents")
        if not isinstance(intents, list) or not intents:
            intents = ["general"]

        slots = data.get("slots") if isinstance(data.get("slots"), dict) else {}
        slots.setdefault("order_id", None)
        slots.setdefault("new_address", None)

        try:
            confidence = float(data.get("confidence"))
        except (ValueError, TypeError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))

        return IntentResult(intents=intents, slots=slots, confidence=confidence)

    @staticmethod
    def _parse(text: str) -> dict:
        if not text or not text.strip():
            return dict(FALLBACK)
        text = text.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return dict(FALLBACK)
