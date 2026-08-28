"""
src/chainlit_app.py

Chainlit + RAG pipeline 統合。
- @cl.on_chat_start: LLM・インデックス(split_docs, vectors: レシート+LinkedIn)・
  receipt DataFrame(df: レシートのみ)を1回だけ構築、session に保存
- @cl.on_message: session から取り出して router_answer(intent 判定 → semantic/aggregation/table_display)
"""
import os
from pathlib import Path
import chainlit as cl
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from src.rag_pipeline import build_index
from src.load_receipts import load_receipts_as_dataframe
from src.router import router_answer

load_dotenv()

RECEIPT_PATHS = sorted(
    str(p) for p in Path("data/tuebingen").glob("receipts_*.json")
)
LINKEDIN_PATHS = sorted(
    str(p) for p in Path("data/linkedin").glob("*.csv")
)
# semantic branch(build_index)はレシート + LinkedIn 全部を対象にする
SEMANTIC_PATHS = RECEIPT_PATHS + LINKEDIN_PATHS

# モジュールレベルで1プロセスにつき1回だけ構築する。
# @cl.on_chat_start 内で呼ぶと新しいチャットセッションが始まるたびに
# 全コーパス(レシート+LinkedIn、計1万件超)の埋め込みを同期的にやり直し、
# その間 asyncio イベントループがブロックされて他の接続を捌けなくなる
# (フロントエンド側で「サーバーに接続できませんでした」となる原因だった)。
llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
    temperature=0.4,
    google_api_key=os.getenv("GEMINI_API_KEY"),
)
split_docs, vectors = build_index(SEMANTIC_PATHS)
# aggregation branch(df)は load_receipts_as_dataframe が JSON 専用のため、
# レシートのみを渡す(LinkedIn CSV は含めない)
df = load_receipts_as_dataframe(RECEIPT_PATHS)


@cl.on_chat_start
async def start():
    cl.user_session.set("llm", llm)
    cl.user_session.set("split_docs", split_docs)
    cl.user_session.set("vectors", vectors)
    cl.user_session.set("df", df)

    await cl.Message(content="RAG pipeline 準備完了。質問をどうぞ。").send()



@cl.on_message
async def on_message(msg: cl.Message):
    llm = cl.user_session.get("llm")
    split_docs = cl.user_session.get("split_docs")
    vectors = cl.user_session.get("vectors")
    df = cl.user_session.get("df")

    # Router 層に一本化: intent 判定 → semantic / aggregation / table_display に振り分け
    answer = router_answer(msg.content, split_docs, vectors, df, llm)

    await cl.Message(content=answer).send()
    

