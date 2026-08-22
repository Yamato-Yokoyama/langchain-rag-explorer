"""
src/chainlit_app.py

Chainlit + RAG pipeline 統合。
- @cl.on_chat_start: LLM・インデックス(split_docs, vectors)・receipt DataFrame(df)を1回だけ構築、session に保存
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

CORPUS_PATHS = sorted(
    str(p) for p in Path("data/tuebingen").glob("receipts_*.json")
)
@cl.on_chat_start
async def start():
    # TODO 1: LLM を作る(rag_pipeline.py の __main__ をコピペで OK)
    #LLMで回答生成
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        temperature=0.4,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )
    
    # TODO 2: build_index(CORPUS_PATH) を呼んで split_docs, vectors を得る
    split_docs, vectors = build_index(CORPUS_PATHS)
    df = load_receipts_as_dataframe(CORPUS_PATHS)
    
    # TODO 3: cl.user_session.set() で llm, split_docs, vectors を3つ保存
    cl.user_session.set("llm", llm)
    cl.user_session.set("split_docs", split_docs)
    cl.user_session.set("vectors", vectors)
    cl.user_session.set("df", df)

    # TODO 4: await cl.Message(content="...").send() で準備完了を通知
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
    

