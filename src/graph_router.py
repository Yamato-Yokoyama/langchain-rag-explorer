"""
src/graph_router.py

Issue #21 の第一段階。src/router.py の route() が行っている if/elif の
判定ロジックを、LangGraph の conditional edge として組み直す。
Checkpointer(会話履歴の保存)はまだ含めない(そこは次の段階)。

参考: docs/notes/langgraph-101-tutorial/01_hello_world.md, 02_conditional_edges_and_checkpointer.md
詰まったら聞く。中身は自分で書く。

Called by: なし(単体で実行して確認する用)
Depends on: src.router(既存の route/handle_* をそのまま再利用)
"""
from typing import TypedDict
from langgraph.graph import StateGraph, END
from src.router import (
    route,
    handle_semantic,
    handle_aggregation,
    handle_table_display,
    handle_linkedin_table,
)


# TODO 1: State を定義する
#   ヒント: collection や df のような「大きい・シリアライズしにくいリソース」は
#   State に入れない(02のCheckpointerの節を参照、後で足す時に壊れる元になる)。
#   State には「クエリ」と「最終的な回答」の2つだけ持たせればいい。
class RouterState(TypedDict):
    ...


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
        ...

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
        ...

    def semantic_node(state: RouterState) -> dict:
        # TODO 4: handle_semantic(state["query"], collection, llm) を呼び、
        #   結果を {"answer": ...} の形で return する
        ...

    def aggregation_node(state: RouterState) -> dict:
        # TODO 5: handle_aggregation(state["query"], df, llm) を呼び、
        #   結果を {"answer": ...} の形で return する
        ...

    def table_display_node(state: RouterState) -> dict:
        # TODO 6: handle_table_display(state["query"], df) を呼び、
        #   結果を {"answer": ...} の形で return する
        ...

    def linkedin_table_node(state: RouterState) -> dict:
        # TODO 7: handle_linkedin_table(state["query"], linkedin_df) を呼び、
        #   結果を {"answer": ...} の形で return する
        ...

    # TODO 8: グラフを組み立てる
    #   ヒント:
    #   - StateGraph(RouterState) で器を作る
    #   - add_node で router_node と 4つの branch ノードを登録
    #     (登録名は "semantic" / "aggregation" / "table_display" / "linkedin_table" に
    #      揃えておくと、decide_route の返り値をそのままノード名として使える)
    #   - set_entry_point("router") で router_node から始める
    #   - add_conditional_edges("router", decide_route, {
    #         "semantic": "semantic", "aggregation": "aggregation",
    #         "table_display": "table_display", "linkedin_table": "linkedin_table",
    #     })
    #   - 4つの branch ノードは、それぞれ add_edge で END に繋ぐ
    #   - .compile() したものを return する
    graph_builder = StateGraph(RouterState)
    ...


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
    ...
