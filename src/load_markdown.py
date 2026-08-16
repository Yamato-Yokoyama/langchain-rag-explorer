import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# 1. UnstructuredMarkdownLoader → UnstructuredLoader(統合版)
from langchain_unstructured import UnstructuredLoader
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter

FILEPATH = "data/class-notes/neo-gricean-implicature.md"

# --- パターン 1: 自作の素朴テキストローダー ---
def load_as_plain_text(filepath: str) -> list[Document]:
    """
    Markdown ファイルを読み、Document 1 個の list として返す素朴なローダー。

    Input:
        filepath: str - Markdown ファイルの絶対 or 相対パス

    Output:
        list[Document] - 要素 1 個のリスト
                         doc.page_content = ファイル全文
                         doc.metadata = {"source": filepath}

    なぜ:
        - LangChain の Loader は必ず list を返す規則(将来複数ファイル対応時に扱いが同じ)
        - UnstructuredLoader が Markdown で崩れたため、自作でシンプルに保つ
    """
    text = Path(filepath).read_text(encoding="utf-8")
    return [Document(page_content=text, metadata={"source": filepath})]

docs1 = load_as_plain_text(FILEPATH)
# print(f"Document count: {len(docs1)}")
# print(f"--- page_content (最初の 300 文字) ---")
# print(docs1[0].page_content[:300])
# print(f"--- metadata ---")
# print(docs1[0].metadata)




docs2 = load_as_plain_text(FILEPATH)
# --- パターン 2: MarkdownHeaderTextSplitter ---
headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
split_docs = splitter.split_text(docs2[0].page_content)

# # 目視
# print(f"Split count: {len(split_docs)}")
# for i, doc in enumerate(split_docs[:3]):  # 最初の 3 個だけ
#     print(f"\n--- Chunk {i} ---")
#     print(f"metadata: {doc.metadata}")
#     print(f"content: {doc.page_content[:150]}")
    
