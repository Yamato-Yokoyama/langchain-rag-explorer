"""
scripts/verify_persistent_checkpointer.py

src/graph_router.pyのTODO17(SqliteSaverへの差し替え)が、
プロセスを再起動しても会話履歴を復元できるかを確認する。

使い方:
  1. ./.venv/bin/python -m src.graph_router  (1回目、これで checkpoints.sqlite に保存される)
  2. ./.venv/bin/python scripts/verify_persistent_checkpointer.py  (別プロセスで復元確認)
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from src.graph_router import build_router_graph
from src.rag_pipeline import build_index
from src.load_receipts import load_receipts_as_dataframe
from src.load_linkedin import load_connections_as_dataframe

load_dotenv()

RECEIPT_PATHS = sorted(str(p) for p in Path("data/tuebingen").glob("receipts_*.json"))
LINKEDIN_PATHS = sorted(str(p) for p in Path("data/linkedin").glob("*.csv"))
CONNECTIONS_PATHS = [p for p in LINKEDIN_PATHS if "Connections" in p]

llm = ChatGoogleGenerativeAI(
    model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
    temperature=0.4,
    google_api_key=os.getenv("GEMINI_API_KEY"),
)
collection = build_index(RECEIPT_PATHS + LINKEDIN_PATHS)
df = load_receipts_as_dataframe(RECEIPT_PATHS)
linkedin_df = load_connections_as_dataframe(CONNECTIONS_PATHS)

graph = build_router_graph(collection, df, linkedin_df, llm)
config = {"configurable": {"thread_id": "test-conversation-1"}}

state = graph.get_state(config).values
print("=== 復元されたstate ===")
print(state)

if state.get("history"):
    print("\n✅ historyが復元されました。永続化は成功しています。")
else:
    print("\n⚠️ historyが空です。1回目(python -m src.graph_router)を先に実行しましたか?")
