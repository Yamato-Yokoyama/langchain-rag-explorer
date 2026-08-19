"""
src/chainlit_app.py

Chainlit + RAG pipeline 統合。
- @cl.on_chat_start: LLM とインデックスを1回だけ構築、session に保存
- @cl.on_message: session から取り出して search → generate_answer
"""
import os
import chainlit as cl
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from src.rag_pipeline import build_index, search, generate_answer

load_dotenv()

CORPUS_PATH = "data/tuebingen/receipts_2026-04.json"
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
    split_docs, vectors = build_index(CORPUS_PATH)

    # TODO 3: cl.user_session.set() で llm, split_docs, vectors を3つ保存
    cl.user_session.set("llm", llm)
    cl.user_session.set("split_docs", split_docs)
    cl.user_session.set("vectors", vectors)
    
    
    # TODO 4: await cl.Message(content="...").send() で準備完了を通知
    await cl.Message(content="RAG pipeline 準備完了。質問をどうぞ。").send()



@cl.on_message
async def on_message(msg: cl.Message):
    # TODO 1: cl.user_session.get() で llm, split_docs, vectors を3つ取り出す
    llm = cl.user_session.get("llm")
    split_docs = cl.user_session.get("split_docs")
    vectors = cl.user_session.get("vectors")

    # TODO 2: search(msg.content, split_docs, vectors, top_k=5) を呼ぶ
    results = search(msg.content, split_docs, vectors, top_k=50, use_rewriting=False, llm=llm)
    # TODO 3: generate_answer(msg.content, results, llm) を呼ぶ
    answer = generate_answer(msg.content, results, llm)

    # TODO 4: await cl.Message(content=answer).send() で返信
    await cl.Message(content=answer).send()
    

