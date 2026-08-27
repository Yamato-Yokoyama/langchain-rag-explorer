import re
from typing import Literal
import pandas as pd
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, HumanMessage
from src.rag_pipeline import search, generate_answer
from src.aggregations import sum_by_month, count_by_month, top_n_by_price, total_all

"""Literal: sketch の route() の返り値型
pd: aggregation / table_display branch の DataFrame 引数型
BaseChatModel: sketch の llm 引数の型ヒント
Document: sketch の split_docs 引数型
search, generate_answer: sketch に「既存の rag_pipeline を呼ぶ」と明記
"""

def route(query: str, llm: BaseChatModel) -> Literal["semantic", "aggregation", "table_display"]:
    """Query を intent 3分類にディスパッチ

    Input:
        query: ユーザーからの自然言語クエリ(例: "4月の合計支出は?")

    Output:
        "semantic" / "aggregation" / "table_display" のいずれかの文字列リテラル

    なぜ:
        Router 型 RAG の入口。この判定結果で処理経路が決まるため、
        後段の全 branch がこの返り値に依存する。Phase 1 は LLM ベース(Option A)。
    """
    #llmで query intent を判定する処理を実装する

    system_msg=SystemMessage("""\
    # タスク
    あなたはユーザークエリを 3 つの intent に分類する分類器です。

    # Intent の定義
    - **semantic**: 概念・用語・意味の説明を求める質問。自然言語での回答が必要。
    - **aggregation**: 数値の集計・計算・要約を求める質問。合計・平均・件数・最大最小など。
    - **table_display**: データを一覧・表形式で見たい質問。個別レコードを構造化して眺めたい意図。

    # 境界例(紛らわしいペア)
    - "Q-principle って何?" → semantic(概念説明)
    - "4月の合計支出は?" → aggregation(数値集計)
    - "全レシート一覧を表で" → table_display(構造化表示)
    - "先月一番高かった買い物は?" → aggregation(top-N は計算)
    - "先月のレシート全部見せて" → table_display(絞り込んだ一覧)
    - "Neo-Gricean と Gricean の違いは?" → semantic(概念比較)

    # 曖昧な場合の判定基準
    - 数値が答えになるなら aggregation
    - 複数レコードを並べて見せるのが答えなら table_display
    - 文章での説明が答えなら semantic

    # 出力制約
    `semantic` / `aggregation` / `table_display` のいずれか 1 単語のみ。
    引用符・説明・改行・句読点を含めない。
    """)

    human_msg=HumanMessage(content=query)
    
    response = llm.invoke([system_msg, human_msg])
    
    intent = response.text.strip().lower()
    
    valid_intents = ["semantic", "aggregation", "table_display"]
    if intent not in valid_intents:
        intent = "semantic"  # デフォルトは semantic にフォールバック

    return intent


def _match_known_companies(query: str, split_docs: list[Document]) -> set[str]:
    """クエリ中に、コーパスに実在する company 名がそのまま含まれていないか調べる。

    LinkedIn Connections の page_content には既に company 名がテキストとして
    埋め込まれている(load_linkedin.py の "{initials}, {position} at {company}...")が、
    それでも "SAP" のような固有名詞1語は、他の chunk に埋もれて cosine similarity の
    上位に来ないことがある(2026-08-27 実験で確認: "DeepLとのつながりは?"などが失敗)。
    埋め込み類似度だけに頼らず、既知の company 名との文字列一致でメタデータを
    先に絞り込む(hybrid search の簡易版)。
    """
    known_companies = {
        doc.metadata["company"]
        for doc in split_docs
        if doc.metadata.get("company")
    }
    query_lower = query.lower()
    return {
        company for company in known_companies
        if company.lower() in query_lower
    }


def handle_semantic(query: str, split_docs: list[Document], vectors: list[list[float]], llm: BaseChatModel) -> str:
    """既存 rag_pipeline を呼ぶ。retrieval + generation の従来経路

    Input:
        query: ユーザーからのクエリ
        split_docs: build_index で構築済みの chunk リスト
        vectors: split_docs に対応する embedding ベクトル群
        llm: 回答生成用の Gemini モデルインスタンス

    Output:
        LLM が生成した自然文の回答

    なぜ:
        semantic branch は既存 pipeline の再利用。router 層で薄くラップすることで、
        Neo-Gricean のような概念クエリに対する従来経路を破壊しない。
        クエリが既知の company 名に一致する場合だけ、そのcompanyのDocumentに
        絞り込んでから検索する(該当なしなら従来通り全件が対象)。
    """
    matched_companies = _match_known_companies(query, split_docs)
    if matched_companies:
        filtered = [
            (doc, vec)
            for doc, vec in zip(split_docs, vectors)
            if doc.metadata.get("company") in matched_companies
        ]
        if filtered:
            split_docs, vectors = (list(items) for items in zip(*filtered))

    search_results = search(query, split_docs, vectors, top_k=5, use_rewriting=True, llm=llm)
    generated_answer = generate_answer(query, search_results, llm=llm)
    return generated_answer


def handle_aggregation(query: str, df: pd.DataFrame, llm: BaseChatModel) -> str:
    """pandas で集計 → LLM で自然文整形

    Input:
        query: 集計系クエリ(例: "4月の合計支出は?")
        df: build_index で構築済みの receipt DataFrame
        llm: 集計関数選択(function calling)+ 結果の自然文整形用

    Output:
        pandas の集計結果を LLM が自然文に整形した回答

    なぜ:
        LLM の arithmetic bottleneck(top_k=171 で +162 EUR 過大の実データ根拠)を
        pandas の決定的計算に置き換える。LLM は関数選択と整形のみ担当し、
        数値計算そのものには関与させない。
    """
    sub_intent_system = SystemMessage(content="""\
    # タスク
    あなたはユーザーの集計クエリを 4 つのサブカテゴリに分類する分類器です。
    Router で既に aggregation branch と判定された query のみが入力されます。

    # サブ intent の定義
    - **sum_by_month**: 月ごとの合計金額を求める質問。「月別に」「4月の合計は」など。
    - **count_by_month**: 月ごとの購入回数・件数を求める質問。「月に何回」「件数」など。
    - **top_n_by_price**: 高額な買い物を上位から求める質問。「一番高い」「top 5」「最高額」など。
    - **total_all**: 全期間の総合計金額を求める質問。「全部でいくら」「トータル」「全体の合計」など。

    # 境界例
    - "4月の合計は?" → sum_by_month(月別)
    - "全部でいくら使った?" → total_all(全期間)
    - "月ごとに何回買った?" → count_by_month
    - "一番高かった買い物は?" → top_n_by_price
    - "毎月の支出は?" → sum_by_month
    - "最高額のレシートは?" → top_n_by_price

    # 曖昧な場合の判定基準
    - 「月」が含まれ、金額を聞くなら sum_by_month、件数を聞くなら count_by_month
    - 「月」が含まれず、全期間の金額を聞くなら total_all
    - 「高い」「top」など順位付けを求めるなら top_n_by_price

    # 出力制約
    `sum_by_month` / `count_by_month` / `top_n_by_price` / `total_all` のいずれか 1 単語のみ。
    引用符・説明・改行・句読点を含めない。
    """)
    
    sub_intent_system = SystemMessage(content=sub_intent_system.content)
    human_msg = HumanMessage(content=query)

    response = llm.invoke([sub_intent_system, human_msg])
    sub_intent = response.text.strip().lower()
    
    valid_intents = ["sum_by_month", "count_by_month", "top_n_by_price", "total_all"]   
    FUNC_MAP = {
    "sum_by_month": sum_by_month,
    "count_by_month": count_by_month,
    "top_n_by_price": top_n_by_price,
    "total_all": total_all,
    }
    
    if sub_intent not in valid_intents:
        agg_func = None
    else:
        agg_func = FUNC_MAP.get(sub_intent, total_all)

    if agg_func is None:
        return "不明な集計クエリです。"

    # 集計処理を実行(aggregations.py の各関数は df のみを受け取る決定的な計算)
    result = agg_func(df)

    # 集計結果(dict / float / DataFrame)を LLM で自然文に整形する。
    # generate_answer() は chunk(score, Document)のリストを前提にした semantic branch 専用の
    # 整形関数なので、ここでは流用せず aggregation 向けの整形呼び出しを別に用意する。
    result_text = result.to_markdown(index=False) if isinstance(result, pd.DataFrame) else str(result)

    format_system = SystemMessage(content="""\
あなたは集計結果を日本語の自然文で簡潔に説明するアシスタントです。
与えられた質問と計算結果(dict / 数値 / 表)をもとに、質問に一言で答えてください。
数値は与えられたものをそのまま使い、勝手に計算し直したり変更したりしないでください。
""")
    format_human = HumanMessage(content=f"質問: {query}\n\n集計結果: {result_text}")

    formatted = llm.invoke([format_system, format_human])
    return formatted.text


def handle_table_display(query: str, df: pd.DataFrame) -> str:
    """構造化データを Markdown table として直接返す(LLM を通さない)

    Input:
        query: 表示系クエリ(例: "全レシート一覧を表で")
        df: build_index で構築済みの receipt DataFrame

    Output:
        Markdown 形式の table 文字列(df.to_markdown() 相当)

    なぜ:
        LLM を経由しないため件数・金額のズレが原理的に発生しない。
        Yamato の生活記録を「一覧として眺める」用途を first-class にする設計判断
        (sketch の Table Display Branch の位置づけ参照)。

        「トップ5」「上位3件」「一番高い」のような順位指定は query に明示的な
        シグナルがあるため、LLM を介さず正規表現 + 既存の top_n_by_price で
        決定的に絞り込む(集計と同じく、表示範囲の判定にも LLM の解釈揺れを持ち込まない)。
    """
    match = re.search(r"(?:トップ|上位|top)\s*(\d+)", query, re.IGNORECASE)
    if match:
        result_df = top_n_by_price(df, n=int(match.group(1)))
    elif "一番高" in query or "最高額" in query:
        result_df = top_n_by_price(df, n=1)
    else:
        result_df = df

    # date 列は集計側では datetime のまま扱いたいので、表示直前にコピー側だけ
    # 日付部分(時刻なし)の文字列に変換する。df 自体(集計で再利用される側)は変更しない。
    display_df = result_df.copy()
    if "date" in display_df.columns:
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")

    return display_df.to_markdown(index=False)


def router_answer(query: str, split_docs: list[Document], vectors: list[list[float]], df: pd.DataFrame, llm: BaseChatModel) -> str:
    """Router 層の wrapper。intent 判定 → 対応 branch にディスパッチ

    Input:
        query: ユーザーからのクエリ
        split_docs, vectors: semantic branch 用の pre-built 資産
        df: aggregation / table_display branch 用の pre-built 資産
        llm: route と各 branch で共用する LLM インスタンス

    Output:
        選択された branch が返した回答文字列

    なぜ:
        chainlit_app.py 側から見た単一エントリーポイント。既存の
        generate_answer() 呼び出しを router_answer() に差し替えるだけで
        Router 導入が完了する設計(既存 API を破壊しない)。
    """
    intent = route(query, llm)

    if intent == "semantic":
        return handle_semantic(query, split_docs, vectors, llm)
    elif intent == "aggregation":
        return handle_aggregation(query, df, llm)
    elif intent == "table_display":
        return handle_table_display(query, df)

    return "不明なクエリです。"