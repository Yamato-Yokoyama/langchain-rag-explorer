"""
src/chainlit_app.py

Chainlit + RAG pipeline 統合。
- @cl.on_chat_start: LLM・インデックス(collection: レシート+LinkedInを格納したChromaDB)・
  receipt DataFrame(df: レシートのみ)を1回だけ構築、session に保存
- @cl.on_message: session から取り出して LangGraph(graph_router.build_router_graph)に
  intent 判定 → semantic/aggregation/table_display/linkedin_table への振り分けを委譲(Issue #29)
"""
import os
from pathlib import Path
import chainlit as cl
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from src.rag_pipeline import build_index
from src.load_receipts import load_receipts_as_dataframe
from src.load_linkedin import load_connections_as_dataframe
from src.graph_router import build_router_graph

load_dotenv()

RECEIPT_PATHS = sorted(
    str(p) for p in Path("data/tuebingen").glob("receipts_*.json")
)
LINKEDIN_PATHS = sorted(
    str(p) for p in Path("data/linkedin").glob("*.csv")
)
CONNECTIONS_PATHS = [p for p in LINKEDIN_PATHS if "Connections" in p]
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
collection = build_index(SEMANTIC_PATHS)
# aggregation branch(df)は load_receipts_as_dataframe が JSON 専用のため、
# レシートのみを渡す(LinkedIn CSV は含めない)
df = load_receipts_as_dataframe(RECEIPT_PATHS)
# linkedin_table branch(linkedin_df)は Connections のみを渡す(Shares は含めない)
linkedin_df = load_connections_as_dataframe(CONNECTIONS_PATHS)
# LangGraphのグラフもモジュールレベルで1回だけ組み立てる(collection等と同じ理由)。
# Checkpointerはまだ無い(Issue #21 stage 2、会話履歴の保存は次段階)。
graph = build_router_graph(collection, df, linkedin_df, llm)


@cl.on_chat_start
async def start():
    cl.user_session.set("graph", graph)

    await cl.Message(content="RAG pipeline 準備完了。質問をどうぞ。").send()



@cl.on_message
async def on_message(msg: cl.Message):
    graph = cl.user_session.get("graph")

    # LangGraphに一本化: intent 判定 → semantic / aggregation / table_display / linkedin_table に振り分け
    result = graph.invoke({"query": msg.content, "answer": ""})
    answer = result["answer"]

    await cl.Message(content=answer).send()
    

