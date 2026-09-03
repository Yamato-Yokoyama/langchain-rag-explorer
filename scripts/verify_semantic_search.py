"""
scripts/verify_semantic_search.py

semantic branch(handle_semantic → generate_answer)の回答品質を確認する。

verify_dataframe.py とは違い、ここでの出力は LLM が書く自然文なので、
「厳密な正解と一致するか」ではなく「人間が読んで正しいと判断できるか」で
確認する(Issue #26: company フィルタ・query rewriting・generate_answerの
役職名/地名の同義語対応、を確認する固定の質問セット)。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from src.rag_pipeline import build_index
from src.router import handle_semantic

RECEIPT_PATHS = sorted(str(p) for p in Path("data/tuebingen").glob("receipts_*.json"))
LINKEDIN_PATHS = sorted(str(p) for p in Path("data/linkedin").glob("*.csv"))
SEMANTIC_PATHS = RECEIPT_PATHS + LINKEDIN_PATHS

# Issue #26 で見つかった、役職名・地名の同義語が絡む質問セット。
# 「正解の文字列」ではなく「この人物名が言及されているべき」という観点で確認する。
TEST_CASES = [
    {
        "query": "DeepLのVPとのつながりは?",
        "expect_mentions": ["B.R."],
    },
    {
        # "APAC" と明示的に絞っているので、APAC特化でないB.R.は含まれなくてよい。
        # K.T.(アジア太平洋統括 社長)が出てくれば、Issue #26の同義語対応は成功。
        "query": "DeepL APACのVPは?",
        "expect_mentions": ["K.T."],
    },
    {
        "query": "SAPで働きたい",
        "expect_mentions": [],  # 固有名詞というより、SAP関連情報が返ればOK(目視確認)
    },
]


def main():
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        temperature=0.4,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )
    collection = build_index(SEMANTIC_PATHS)

    for case in TEST_CASES:
        query = case["query"]
        expect_mentions = case["expect_mentions"]

        answer = handle_semantic(query, collection, llm)

        print("=" * 60)
        print(f"Query: {query}")
        print(f"Answer: {answer}")

        if expect_mentions:
            missing = [name for name in expect_mentions if name not in answer]
            if missing:
                print(f"[要確認] 言及が期待される名前が無い: {missing}")
            else:
                print("[OK] 期待した名前が全て言及されている")
        else:
            print("[目視確認] 期待する固有名詞は指定していません、内容を読んで判断してください")
        print()


if __name__ == "__main__":
    main()
