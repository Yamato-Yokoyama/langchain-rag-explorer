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
# checkpointer(MemorySaver)はgraph_router.build_router_graph側のcompile()で付与済み
# (Issue #21 stage 2)。会話履歴はプロセスのメモリ上に保持されるだけなので、
# サーバー再起動で消える・複数プロセスでは共有されない点に注意(本番運用するなら
# 永続化されたcheckpointerへの差し替えが必要、長期のセッション管理はIssue #22の射程)。
graph = build_router_graph(collection, df, linkedin_df, llm)


@cl.set_starters
async def set_starters():
    """チャット開始画面にクリックできる例を並べる。何が聞けるか分からない問題への対処。"""
    return [
        cl.Starter(
            label="LinkedInのつながりを調べる",
            message="最近つながったSAPの人を3人教えて",
        ),
        cl.Starter(
            label="月ごとの支出を集計する",
            message="先月の合計支出は?",
        ),
        cl.Starter(
            label="授業ノートについて質問する",
            message="Q-principleって何?",
        ),
        cl.Starter(
            label="会社とのつながりを横断して調べる",
            message="DeepLとつながっている人はいる?",
        ),
    ]


@cl.on_chat_start
async def start():
    cl.user_session.set("graph", graph)

    await cl.Message(content=(
        "RAG pipeline 準備完了。以下のような質問に答えられます:\n\n"
        "- **LinkedInのつながり**: 「最近つながったSAPの人を3人教えて」\n"
        "- **月ごとの支出集計**: 「先月の合計支出は?」「一番高かった買い物は?」\n"
        "- **授業ノート(語用論)への質問**: 「Q-principleって何?」\n"
        "- **会社名での横断検索**: 「DeepLとつながっている人はいる?」\n\n"
        "下のStartersからも選べます。"
    )).send()



@cl.on_message
async def on_message(msg: cl.Message):
    graph = cl.user_session.get("graph")

    # LangGraphに一本化: intent 判定 → semantic / aggregation / table_display / linkedin_table に振り分け
    # thread_id を Chainlit のセッションID(cl.context.session.id、タブ単位で不変)に対応させることで、
    # 同じタブ内の会話historyがcheckpointerに保存・復元され、指示語解決(Issue #21 stage 2)が機能する
    config = {"configurable": {"thread_id": cl.context.session.id}}
    result = graph.invoke({"query": msg.content, "answer": "", "history": []}, config=config)
    answer = result["answer"]

    await cl.Message(content=answer).send()
    

