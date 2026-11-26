# -*- coding: utf-8 -*-
"""mini-e-commerce 电商客服 RAG 项目 - 终端交互入口"""
import os
import sys
import warnings

from langchain_core._api.deprecation import LangChainDeprecationWarning

from .service import CustomerService

warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)


def main() -> None:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise SystemExit(
            "未找到环境变量 DASHSCOPE_API_KEY。\n"
            "请在 PowerShell 执行：setx DASHSCOPE_API_KEY \"你的真实Key\"\n"
            "然后重新打开终端再运行。"
        )

    print("正在构建电商客服知识库（首次运行需调用嵌入模型）...", flush=True)
    try:
        service = CustomerService(api_key, session_id="terminal-user")
    except Exception as e:
        raise SystemExit(f"初始化失败：{type(e).__name__}: {e}")

    print("\n" + "=" * 50)
    print("  小蜜 - 电商智能客服（RAG + 意图识别 + 记忆摘要）")
    print("  输入问题后回车发送；输入 exit / quit 退出")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input("用户: ")
        except (KeyboardInterrupt, EOFError):
            print("\n对话结束！拜拜~")
            break

        if user_input.strip().lower() in ("exit", "quit"):
            print("客服: 感谢您的咨询，再见！")
            break
        if not user_input.strip():
            print("请勿输入空白字符！")
            continue

        print("客服: ", end="", flush=True)
        try:
            for chunk in service.reply(user_input):
                print(chunk, end="", flush=True)
            print()
        except Exception as e:
            print(f"\n[出错] {type(e).__name__}: {e}")
            print("请稍后重试或输入 exit 退出。")


if __name__ == "__main__":
    main()
