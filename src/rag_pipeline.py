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

from src.load_markdown import load_as_plain_text          # ← 再利用性
from src.similarity import cosine_similarity              # ← 再利用性
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings


from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv

from src.query_rewriting import expand_query_to_definition  # ← 再利用性
from src.load_receipts import load_receipts_from_json      # ← 再利用性
from src.load_linkedin import load_shares_from_csv, load_connections_from_csv  # ← 再利用性
from pathlib import Path


# Embedding
embeddings = HuggingFaceEmbeddings(
    model_name = "BAAI/bge-m3",
    model_kwargs={"device": "cpu"}
)

def build_index(filepaths: str | list[str]) -> tuple[list, list]:
    """Load + Split + Embed。ファイル拡張子で loader を自動選択。"""
    
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

    vectors = embeddings.embed_documents([doc.page_content for doc in all_split_docs])

    return all_split_docs, vectors

def search(query: str, split_docs: list, vectors: list, top_k=5, use_rewriting = False, llm=None) -> list:
    """クエリに対して上位k位をChunksを返す"""
    if use_rewriting:
        original_query = query
        query = expand_query_to_definition(query, llm)
        print(f"\n[Query Rewriting]")
        print(f"  元:   {original_query}")
        print(f"  拡張: {query}")
        
          
    query_vec = embeddings.embed_query(query)
    scores = []
        
    for chunkvec, doc in zip(vectors, split_docs):
        similarity = cosine_similarity(query_vec, chunkvec)
        scores.append((similarity, doc))
        
    scores.sort(reverse=True, key=lambda x: x[0])
    
    return scores[:top_k]
    
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
    load_dotenv()
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
    split_docs, vectors = build_index("data/tuebingen/receipts_2026-04.json")
    
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
        results = search(query, split_docs, vectors, top_k=5)
        for score, doc in results:
            print(f"\nScore: {score:.4f}, Metadata: {doc.metadata}")
        answer = generate_answer(query, results, llm)
        print(f"\n=== Final Answer ===\n{answer}\n")
    