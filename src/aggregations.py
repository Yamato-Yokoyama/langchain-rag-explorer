import pandas as pd

def sum_by_month(df: pd.DataFrame) -> dict[str, float]:
    """月別合計金額を計算する。

    Input:
        df: load_receipts_as_dataframe で構築された receipt DataFrame

    Output:
        {"2025-10": 145.32, "2025-11": 89.50, ...} のような月 → 合計 EUR の dict

    なぜ:
        LLM は top_k=171 で全件見えても月別 grouping を 10ヶ月中 9ヶ月で誤答した。
        pandas の groupby で決定的に計算することで、Retrieval/Arithmetic bottleneck を
        構造的に回避する(sketch の Problem セクション参照)。
    """
    results = df.groupby("month")["total_eur"].sum()
    return results.to_dict()



def count_by_month(df: pd.DataFrame) -> dict[str, int]:
    """月別レシート件数を計算する。

    Input:
        df: load_receipts_as_dataframe で構築された receipt DataFrame

    Output:
        {"2025-10": 18, "2025-11": 15, ...} のような月 → 件数 の dict

    なぜ:
        top_k=50 で LLM の月別件数報告合計がぴったり 50 に一致した現象(retrieval bottleneck)、
        top_k=171 でも件数を誤答した現象(arithmetic bottleneck)、両方への構造的解決。
        pandas の groupby.size() で決定的に計算する。
    """
    results = df.groupby("month").size()
    return results.to_dict()


def top_n_by_price(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """高額 top-N レシートを返す。

    Input:
        df: load_receipts_as_dataframe で構築された receipt DataFrame
        n: 返す件数(default 5)

    Output:
        date, store_name, total_eur の 3 列を持つ pd.DataFrame(n 行、金額降順)

    なぜ:
        「一番高かった買い物は?」系クエリへの回答。LLM が top-K chunk 内でしか
        比較できない問題(Day 8 の 4月最高額誤答: 実 12.90 EUR を 11.55 EUR と回答)を、
        pandas の nlargest で決定的に解決する。
    """
    result = df.nlargest(n, "total_eur")[["date", "store", "total_eur"]]
    return result


def top_n_recent_connections(df: pd.DataFrame, n: int = 5, company: str | None = None) -> pd.DataFrame:
    """直近でつながった順に上位N件のLinkedIn Connectionsを返す。

    Input:
        df: load_connections_as_dataframe で構築された connections DataFrame
        n: 返す件数(default 5)
        company: 指定があれば、その勤務先の人だけに絞り込む(大文字小文字を区別しない部分一致)

    Output:
        initials, company, position, connected_on の4列を持つ pd.DataFrame(n行、日付降順)

    なぜ:
        「最近つながったDeepLの人を日付順で5人」のような質問は、embedding類似度検索
        (semantic branch)では原理的に解けない(Issue #12)。レシートのtop_n_by_priceと
        同じく、pandasのsort_valuesで決定的にソート・件数指定する。
    """
    result = df
    if company:
        result = result[result["company"].str.contains(company, case=False, na=False)]

    result = result.sort_values("connected_on", ascending=False).head(n)
    return result[["initials", "company", "position", "connected_on"]]


def total_all(df: pd.DataFrame) -> float:
    """全期間の合計金額を返す。

    Input:
        df: load_receipts_as_dataframe で構築された receipt DataFrame

    Output:
        全 receipt の total_eur の合計(float)

    なぜ:
        「全部でいくら使った?」系クエリへの回答。verify script で 1474.55 EUR が
        真値として確認済み、この関数はその ground truth を確実に返す責務を持つ。
    """
    sum = df["total_eur"].sum()
    return sum