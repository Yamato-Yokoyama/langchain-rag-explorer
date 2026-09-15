"""
src/graph_router.py

Issue #21 stage 1: src/router.py の route() が行っている if/elif の
判定ロジックを、LangGraph の conditional edge として組み直した(完了)。
Issue #21 stage 2: Checkpointer + 指示語解決ノードを追加し、マルチターンの
会話(「それぞれの役職は?」等)に対応した(完了)。
Issue #22: 指示語の有無をクエリ単体で先に判定する detect_deixis ノードを
追加し、指示語が無いターン(話題が変わった時等)では contextualize_query の
全履歴書き換えをスキップする(今回のTODO)。3ターン以上での履歴参照範囲や
複数トピックの絞り込みは、まずこのフラグで様子を見てから設計判断する。

参考: docs/notes/langgraph-101-tutorial/
  01_hello_world.md, 02_conditional_edges_and_checkpointer.md,
  03_wiring_into_chainlit.md, 04_accumulating_state_for_conversation_history.md
詰まったら聞く。中身は自分で書く。

Called by: src.chainlit_app
Depends on: src.router(既存の route/handle_* をそのまま再利用),
  src.query_rewriting(contextualize_query, needs_context)
"""
import operator
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.router import (
    route,
    handle_semantic,
    handle_aggregation,
    handle_table_display,
    handle_linkedin_table,
)
from src.query_rewriting import contextualize_query, needs_context


# TODO 1: State を定義する(完了)
class RouterState(TypedDict):
    query: str
    answer: str
    # TODO 10: history フィールドを追加する。
    #   ヒント: 04のノートの通り、Annotated[list, operator.add] にすると
    #   ノードが {"history": [新しい1件]} を返すだけで蓄積される(上書きされない)
    history: Annotated[list, operator.add]


def build_router_graph(collection, df, linkedin_df, llm):
    """route()の判定ロジックを LangGraph の conditional edge として組み立てる。

    Input:
        collection: semantic branch 用の ChromaDB collection
        df: aggregation / table_display branch 用の receipt DataFrame
        linkedin_df: linkedin_table branch 用の connections DataFrame
        llm: route と各 branch で共用する LLM インスタンス
        (これらは State には入れず、この関数の中でノード関数がクロージャとして捕まえる)

    Output:
        compile 済みの graph。graph.invoke({"query": "...", "answer": ""}) で呼べる

    なぜ:
        既存の router_answer() と同じ役割を、LangGraph の正式なグラフ構造として
        表現する。判定ロジック・各 handle_* 関数の中身は一切変えず、再利用する。
    """

    def router_node(state: RouterState) -> dict:
        # TODO 2: 何もしない空ノード。conditional edge の分岐元として置くだけ。
        #   ヒント: 更新するものが無いので、空の dict を返せばいい
        return {}

    def decide_route(state: RouterState) -> str:
        """route()を呼んで、次に進むノード名を決める。

        Input:
            state: RouterState

        Output:
            "semantic" / "aggregation" / "table_display" / "linkedin_table" のいずれか

        なぜ:
            route()の返り値が、LangGraphのconditional edgeが期待する
            「次のノード名」の形と完全に一致している(4つのintentの文字列名が
            そのままノード名になっている)。ロジックの移植はここだけで完結する。
        """
        # TODO 3: state["query"] と llm を使って route(query, llm) を呼び、
        #   その返り値をそのまま return する
        return route(state["query"], llm)

    def semantic_node(state: RouterState) -> dict:
        # TODO 4: handle_semantic(state["query"], collection, llm) を呼び、
        #   結果を {"answer": ...} の形で return する
        result = handle_semantic(state["query"], collection, llm)
        return {"answer": result}

    def aggregation_node(state: RouterState) -> dict:
        # TODO 5: handle_aggregation(state["query"], df, llm) を呼び、
        #   結果を {"answer": ...} の形で return する
        handle_result = handle_aggregation(state["query"], df, llm)
        return {"answer": handle_result}

    def table_display_node(state: RouterState) -> dict:
        # TODO 6: handle_table_display(state["query"], df) を呼び、
        #   結果を {"answer": ...} の形で return する
        handle_result = handle_table_display(state["query"], df)
        return {"answer": handle_result}

    def linkedin_table_node(state: RouterState) -> dict:
        # TODO 7: handle_linkedin_table(state["query"], linkedin_df) を呼び、
        #   結果を {"answer": ...} の形で return する
        handle_result = handle_linkedin_table(state["query"], linkedin_df)
        return {"answer": handle_result}

    def detect_deixis_node(state: RouterState) -> dict:
        # TODO 15: 何もしない空ノード(router_nodeと同じ役割)。
        #   conditional edge の分岐元として置くだけ。
        return {}

    def decide_needs_context(state: RouterState) -> str:
        """クエリに指示語が含まれるか判定して、次のノード名を返す(Issue #22)。

        Input:
            state: RouterState

        Output:
            "needed"(contextualizeへ、履歴を見に行く) /
            "not_needed"(routerへ直行、書き換えをスキップ)

        なぜ:
            decide_route と同じ「判定してノード名を返す」パターン。
            指示語が無いクエリ(話題が変わったターン等)まで毎回
            contextualize_query に全履歴を渡してしまうと、無関係な履歴に
            引っ張られて誤った書き換えが起きるリスクがある(Issue #22 論点2)。
            ここで先に1段階フィルタする。
        """
        # TODO 16: needs_context(state["query"], llm) を呼び、
        #   True なら "needed"、False なら "not_needed" を return する
        needs_context_result = needs_context(state["query"], llm)
        if needs_context_result:
            return "needed"
        else:
            return "not_needed"

    def contextualize_node(state: RouterState) -> dict:
        """会話履歴を見て、今回のクエリの指示語を解決する(Issue #21 stage 2)。

        Input:
            state: RouterState(historyには過去のターンが蓄積されている)

        Output:
            dict。{"query": 解決後のクエリ} を返す(historyはここでは触らない)

        なぜ:
            route()やhandle_*が指示語入りのクエリ(「それぞれの役職は?」)を
            そのまま受け取ると、何を指しているか分からず正しく処理できない。
            router_nodeより前にこのノードを置き、解決済みのクエリに
            差し替えてから後段(router以降)に渡す。
        """
        # TODO 11: contextualize_query(state["query"], state["history"], llm) を呼び、
        #   結果を {"query": ...} の形で return する
        result = contextualize_query(state["query"], state["history"], llm)
        return {"query": result}

    def record_history_node(state: RouterState) -> dict:
        """このターンのやり取り(質問+回答)を history に1件追加する。

        Input:
            state: RouterState(この時点で query は解決済み、answer は生成済み)

        Output:
            dict。{"history": [このターンの記録1件]} を返す
            (historyはAnnotated[list, operator.add]なので、これだけで蓄積される)

        なぜ:
            semantic/aggregation/table_display/linkedin_tableの4つのノードは
            それぞれ別の場所にあるので、「このターンが終わった後」を表す
            1箇所(この関数)にまとめてhistory記録の責務を持たせる。
        """
        # TODO 12: f"Q: {state['query']}\nA: {state['answer']}" のような1件の
        #   文字列を作り、{"history": [その文字列]} を return する
        history_entry = f"Q: {state['query']}\nA: {state['answer']}"
        return {"history": [history_entry]}

    # TODO 13: グラフを組み立て直す(stage 1からの変更点、済)
    #   ヒント:
    #   - ノード登録に "contextualize" と "record_history" を追加
    #   - set_entry_point を "router" から "contextualize" に変更
    #   - add_edge("contextualize", "router") を追加(固定のedge、conditionalではない)
    #   - 4つの branch ノードの行き先を、END ではなく "record_history" に変更
    #     (add_edge("semantic", "record_history") のように4つとも直す)
    #   - add_edge("record_history", END) を追加
    #   - .compile() の引数に checkpointer=MemorySaver() を渡す
    # TODO 17: Issue #22 用にグラフ入口を組み替える。
    #   ヒント:
    #   - ノード登録に "detect_deixis" を追加
    #   - set_entry_point を "contextualize" から "detect_deixis" に変更
    #   - add_edge("contextualize", "router") はそのまま残す
    #   - add_conditional_edges("detect_deixis", decide_needs_context, {
    #         "needed": "contextualize",
    #         "not_needed": "router",
    #     }) を追加
    graph_builder = StateGraph(RouterState)
    graph_builder.add_node("detect_deixis", detect_deixis_node)
    graph_builder.add_node("contextualize", contextualize_node)
    graph_builder.add_node("record_history", record_history_node)
    graph_builder.add_node("router", router_node)
    graph_builder.add_node("semantic", semantic_node)
    graph_builder.add_node("aggregation", aggregation_node)
    graph_builder.add_node("table_display", table_display_node)
    graph_builder.add_node("linkedin_table", linkedin_table_node)
    graph_builder.set_entry_point("detect_deixis")
    graph_builder.add_conditional_edges("detect_deixis", decide_needs_context, {
        "needed": "contextualize",
        "not_needed": "router",
    })
    graph_builder.add_edge("contextualize", "router")
    graph_builder.add_conditional_edges("router", decide_route,{
        "semantic": "semantic",
        "aggregation": "aggregation",
        "table_display": "table_display",
        "linkedin_table": "linkedin_table",
    })
    graph_builder.add_edge("semantic", "record_history")
    graph_builder.add_edge("aggregation", "record_history")
    graph_builder.add_edge("table_display", "record_history")
    graph_builder.add_edge("linkedin_table", "record_history")
    graph_builder.add_edge("record_history", END)
    return graph_builder.compile(checkpointer=MemorySaver())

import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

from src.rag_pipeline import build_index
from src.load_receipts import load_receipts_as_dataframe
from src.load_linkedin import load_connections_as_dataframe
from langchain_google_genai import ChatGoogleGenerativeAI

if __name__ == "__main__":
    # TODO 9: 実際に動かして確認する
    #   ヒント:
    #   - src.rag_pipeline.build_index() で collection を用意
    #   - src.load_receipts.load_receipts_as_dataframe() で df を用意
    #   - src.load_linkedin.load_connections_as_dataframe() で linkedin_df を用意
    #   - ChatGoogleGenerativeAI で llm を用意(hello_gemini.py や rag_pipeline.py の
    #     __main__ を参考にしていい)
    #   - build_router_graph(collection, df, linkedin_df, llm) でグラフを作る
    #   - いくつかテストクエリで invoke して、route()と同じ答えが返るか確認する
    #     例: "4月の合計支出は?" → aggregation, "DeepLのVPは?" → semantic,
    #         "最近つながったSAPの人を3人教えて" → linkedin_table
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

    graph = build_router_graph(collection, df, linkedin_df, llm)
    print("=== stage 1 の確認(単発クエリ、historyは空のまま) ===")
    result = graph.invoke(
        {"query": "4月の合計支出は?", "answer": "", "history": []},
        config={"configurable": {"thread_id": "stage1-test"}},
    )
    print(f"結果: {result}")

    # TODO 14: stage 2(マルチターン)の確認。
    #   ヒント:
    #   - config = {"configurable": {"thread_id": "test-conversation-1"}} を作る
    #   - 1ターン目: graph.invoke({"query": "最近つながったSAPの人を3人教えて",
    #     "answer": "", "history": []}, config=config) を呼ぶ
    #   - 2ターン目: graph.invoke({"query": "それぞれの役職は?", "answer": "",
    #     "history": []}, config=config) を、同じ config で呼ぶ
    #     (historyは空のリストを渡してよい、Annotated[list, operator.add]が
    #      checkpointerに保存済みの中身と自動的に合成してくれる)
    #   - 2ターン目の結果のqueryとanswerを見て、「それぞれ」がSAPの3人を
    #     指して解決できているか確認する

    def run_turn(label, turn_input, config):
        """graph.stream()でノードごとの出力を逐次printし、どのbranchを通ったか可視化する。
        invoke()は最終結果しか返さないため、途中どのノードが呼ばれたかは分からない。
        """
        print(f"=== stage 2 の確認: {label} ===")
        for update in graph.stream(turn_input, config=config, stream_mode="updates"):
            for node_name, node_output in update.items():
                print(f"  [{node_name}] → {node_output}")
        final_state = graph.get_state(config).values
        print(f"{label}の最終state: {final_state}")
        return final_state

    config = {"configurable": {"thread_id": "test-conversation-1"}}
    result1 = run_turn(
        "1ターン目",
        {"query": "最近つながったSAPの人を3人教えて", "answer": "", "history": []},
        config,
    )
    result2 = run_turn(
        "2ターン目",
        {"query": "それぞれの役職は?", "answer": "", "history": []},
        config,
    )

    print("--- グラフの構造(draw_ascii、これは配線図そのもの。実行順は上のstream出力を見る) ---")
    print(graph.get_graph().draw_ascii())