"""
src/rag_pipeline.py

RAG の Load → Split → Embed → Search を統合するメインパイプライン。

Called by:
    - src/chainlit_app.py(Week 2)
    - tests/test_rag.py

Depends on:
    - src/load_markdown.py
    - src/similarity.py
"""

import os
from dotenv import load_dotenv

# HuggingFaceEmbeddings の初期化(HF_HUB_OFFLINE 等を読む)より前に読み込む必要がある。
# ここで呼ばないと、chainlit_app.py 側の load_dotenv() 呼び出しは
# `from src.rag_pipeline import build_index` の import 実行後になってしまい、
# 下の embeddings 初期化には間に合わない(2026-08-29、再発対応)。
load_dotenv()

from src.load_markdown import load_as_plain_text          # ← 再利用性
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.query_rewriting import expand_query_to_definition  # ← 再利用性
from src.load_receipts import load_receipts_from_json      # ← 再利用性
from src.load_linkedin import load_shares_from_csv, load_connections_from_csv  # ← 再利用性
from pathlib import Path
import chromadb


# Embedding
embeddings = HuggingFaceEmbeddings(
    model_name = "BAAI/bge-m3",
    model_kwargs={"device": "cpu"}
)

_CHROMA_DIR = Path("chroma_db")
_COLLECTION_NAME = "rag_explorer"


def _clean_metadata(metadata: dict) -> dict:
    """ChromaDB は metadata の値に None や NaN を受け付けないため、有効な値だけ残す。"""
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, float) and value != value:  # NaN は自分自身と等しくない
            continue
        cleaned[key] = value
    return cleaned


def build_index(filepaths: str | list[str]):
    """Load + Split + Embed し、ChromaDB の collection に保存する。ファイル拡張子で loader を自動選択。

    対象ファイル群から作った chunk 数と、既に .chroma/ に保存済みの件数が
    一致していれば埋め込み計算はスキップし、保存済みの collection をそのまま返す。
    レシート+LinkedIn 全件のCPU埋め込みは数分かかる重い処理なので、
    サーバーを再起動するたびにやり直さないようにするための措置。
    """

    # 拡張子で分岐
    if isinstance(filepaths, str):
        filepaths = [filepaths]

    all_split_docs = []
    for path in filepaths:
        if path.endswith(".md"):
            docs = load_as_plain_text(path)
            # Split
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]
            splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
            split_docs = splitter.split_text(docs[0].page_content)

        elif path.endswith(".json"):
            # JSON は 1 レシート = 1 Document で既に分割済み、Split 不要
            split_docs = load_receipts_from_json(path)
        elif path.endswith(".csv"):
            # LinkedIn export はファイル名で Shares / Connections を判別
            filename = Path(path).name
            if "Shares" in filename:
                split_docs = load_shares_from_csv(path)
            elif "Connections" in filename:
                split_docs = load_connections_from_csv(path)
            else:
                raise ValueError(f"Unknown LinkedIn CSV type: {filename}")
        else:
            raise ValueError(f"Unsupported file type: {path}")

        all_split_docs.extend(split_docs)

    client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    # hnsw:space を明示的に cosine にする(デフォルトは L2 距離で、BGE-M3 のコサイン類似度前提と合わない)
    collection = client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if collection.count() == len(all_split_docs):
        return collection

    vectors = embeddings.embed_documents([doc.page_content for doc in all_split_docs])

    ids = []
    documents = []
    metadatas = []
    for i, doc in enumerate(all_split_docs):
        ids.append(f"chunk_{i}")
        documents.append(doc.page_content)
        metadatas.append(_clean_metadata(doc.metadata))

    collection.add(ids=ids, embeddings=vectors, documents=documents, metadatas=metadatas)

    return collection

def search(query: str, collection, top_k=5, use_rewriting=False, llm=None, where=None) -> list:
    """クエリに対して上位k件の chunk を、ChromaDB の collection から検索して返す。"""
    if use_rewriting:
        original_query = query
        query = expand_query_to_definition(query, llm)
        print(f"\n[Query Rewriting]")
        print(f"  元:   {original_query}")
        print(f"  拡張: {query}")

    query_vec = embeddings.embed_query(query)

    results = collection.query(
        query_embeddings=[query_vec],
        n_results=top_k,
        where=where,
    )

    # ChromaDB はバッチクエリ前提の形(リストの中にリスト)で返すので、1件分だけ取り出す
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    scores = []
    for document_text, metadata, distance in zip(documents, metadatas, distances):
        doc = Document(page_content=document_text, metadata=metadata)
        similarity = 1 - distance  # collection を cosine space で作っているので、distance = 1 - コサイン類似度
        scores.append((similarity, doc))

    return scores

def generate_answer(query: str, retrieved_chunks: list, llm) -> str:
    """
    取得した chunks を context に、LLM に回答を生成させる。
    
    Input:
        query: ユーザーの質問
        retrieved_chunks: search() の返り値、[(score, doc), ...]
        llm: ChatGoogleGenerativeAI インスタンス
    
    Output:
        str, LLM の回答本文
    """
    # chunks を 1 つの context 文字列にまとめる
    context ="\n\n".join([
        f"[Source: {doc.metadata}\n{doc.page_content}]"
        for score, doc in retrieved_chunks
    ])
    
    # プロンプト構築(SystemMessage で役割、HumanMessage で質問 + context)
    message = [
        SystemMessage(content="以下の文脈のみを根拠に、日本語で簡潔に答えてください。文脈から合理的に推論できる範囲で答えて構いません。関連する情報が全くない場合のみ「情報がありません」と答えてください。"),
        HumanMessage(content=f"文脈:\n{context}\n\n質問: {query}"),
    ]
    
    response = llm.invoke(message)
    return response.text


if __name__ == "__main__":
    # load_dotenv() はファイル冒頭で既に呼んでいる
    #LLMで回答生成
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        temperature=0.4,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )
    
    
    # #Index 構築
    # split_docs, vectors = build_index("data/class-notes/neo-gricean-implicature.md")
    
    # query = "Q-principleって何?"
    
    # # === 実験 1: Rewriting なし ===
    # print("=" * 60)
    # print("実験 1: Rewriting なし")
    # print("=" * 60)
    # results = search(query, split_docs, vectors, top_k=5)
    # answer = generate_answer(query, results, llm)
    
    # print(f"\n=== Query ===\n{query}")
    # print(f"\n=== Answer ===")
    # for score, doc in results:
    #     print(f"\nScore: {score:.4f}, Header: {doc.metadata}")
    # print(f"\n=== Final Answer ===\n{answer}")
    
    # # === 実験 2: Rewriting あり ===
    # print("\n" + "=" * 60)
    # print("実験 2: Rewriting あり")
    # print("=" * 60)
    # results = search(query, split_docs, vectors, top_k=5, use_rewriting=True, llm=llm)
    # answer = generate_answer(query, results, llm)
    
    # print(f"\n=== Query ===\n{query}")
    # print(f"\n=== Answer ===")
    # for score, doc in results:
    #     print(f"\nScore: {score:.4f}, Header: {doc.metadata}")
    # print(f"\n=== Final Answer ===\n{answer}")


    # === 実験 3: レシート検索 ===
    # レシート JSON を index に(まず 4 月分だけ)
    collection = build_index("data/tuebingen/receipts_2026-04.json")

    # 自然言語クエリ
    queries = [
        "留学生はどんな食べ物を買ってる?",
        "スーパーで何を買ってる?",
        "4 月の一番高い買い物は?",  # ← SQL 系、うまく答えられない予想
    ]

    for query in queries:
        print("=" * 60)
        print(f"Query: {query}")
        print("=" * 60)
        results = search(query, collection, top_k=5)
        for score, doc in results:
            print(f"\nScore: {score:.4f}, Metadata: {doc.metadata}")
        answer = generate_answer(query, results, llm)
        print(f"\n=== Final Answer ===\n{answer}\n")
