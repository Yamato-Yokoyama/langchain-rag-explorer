"""
src/load_receipts.py

月次レシート JSON を Document のリストに変換する Loader。
Markdown loader と同じインターフェース(list[Document])で、
rag_pipeline に統合しやすくする。
"""
import json
import re

from pathlib import Path
from langchain_core.documents import Document
import pandas as pd

_CITATION_PATTERN = re.compile(r"\[cite:\s*\d+\]")


def _strip_citation(text: str | None) -> str | None:
    """元データに混入している '[cite: N]' のような citation artifact を除去する。"""
    if text is None:
        return None
    return _CITATION_PATTERN.sub("", text).strip()


def load_receipts_from_json(filepath: str) -> list[Document]:
    """月次レシート JSON を Document のリストに変換する。"""
    data = json.loads(Path(filepath).read_text(encoding="utf-8"))
    
    docs = []
    for receipt in data:
        page_content = _format_receipt_as_text(receipt)
        
        # ネストした dict から値を取り出す
        transaction = receipt.get("transaction", {})
        store = receipt.get("store", {})
        date_str = transaction.get("date", "")
        
        metadata = {
            "source": filepath,
            "receipt_id": receipt.get("receipt_id"),
            "date": date_str,
            "store": store.get("name"),
            "store_address": store.get("address"),
            "total_eur": transaction.get("total_eur"),
            "total_jpy": transaction.get("total_jpy"),
            "month": date_str[:7] if date_str else None,
        }
        
        docs.append(Document(page_content=page_content, metadata=metadata))
    
    return docs


def _format_receipt_as_text(receipt: dict) -> str:
    """レシート dict を自然文に整形。ネスト構造対応版。"""
    transaction = receipt.get("transaction", {})
    store = receipt.get("store", {})
    
    date = transaction.get("date", "日付不明")
    store_name = store.get("name", "店舗不明")
    total_eur = transaction.get("total_eur")
    
    # ヘッダ
    # 追加: 文脈を注入
    header = "【Tübingen で生活する日本人留学生 Yamato の生活費記録】\n"

    header += f"{date}、{store_name}で"
    if total_eur is not None:
        header += f" {total_eur} EUR の買い物をした。"
    else:
        header += " 買い物をした。"
    
    # 品目
    items = receipt.get("items", [])
    if items:
        item_texts = []
        for item in items:
            # 日本語名を優先(検索マッチしやすい)、なければ元言語名
            name = item.get("name_jp") or item.get("name_original", "")
            
            # price は dict、final_eur を取る
            price_dict = item.get("price", {})
            final_price = price_dict.get("final_eur")
            category = item.get("category", "")
            
            if final_price is not None:
                if category:
                    item_texts.append(f"{name}({category}, {final_price} EUR)")
                else:
                    item_texts.append(f"{name}({final_price} EUR)")
            else:
                item_texts.append(name)
        
        header += f" 購入品: {', '.join(item_texts)}。"

    return header


def load_receipts_as_dataframe(paths: list[str]) -> pd.DataFrame:
    """Receipt JSON ファイル群を flat な DataFrame に変換する。

    Input:
        paths: JSON ファイルパスのリスト
               (例: ["data/tuebingen/receipts_2025-10.json", ...])

    Output:
        pd.DataFrame with columns:
            - date (datetime)        : transaction.date
            - month (str)            : "2025-10" 形式、date から derive、groupby の主軸
            - store_name (str)       : store.name
            - store_address (str)    : store.address
            - total_eur (float)      : transaction.total_eur、金額集計の主軸
            - total_jpy (float)      : transaction.total_jpy
            - item_count (int)       : len(items)
            - source_file (str)      : traceability 用、paths の要素

    なぜ:
        - LLM に全件読ませる代わりに、pandas の groupby で決定的に集計できる形にする
        - top_k=171 で LLM が systematic に +162 EUR 過大報告した問題への構造的解決
        - Router の aggregation branch と table_display branch の共通データ源
        - build_index とは別関数として独立させることで、semantic branch(vector 索引)と
          aggregation/table_display branch(DataFrame)の責務を分離する
    """

    
    rows: list[dict] = []
    
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        
        for receipt in data:
            transaction = receipt.get("transaction", {})
            store = receipt.get("store", {})
            date_str = transaction.get("date", "")
            # 元データに "2026-05-19[cite: 1]" のような citation artifact が
            # 混入しているケースがあるため、日付部分(先頭10文字)だけを取り出す。
            # month と同じ「固定長 slice で防御」の考え方。
            date_clean = date_str[:10] if date_str else None
            rows.append({
                "date": date_clean,                      # 3 で pd.to_datetime に変換
                "month": date_str[:7] if date_str else None,
                "store": _strip_citation(store.get("name")),
                "store_address": _strip_citation(store.get("address")),
                "total_eur": transaction.get("total_eur"),
                "total_jpy": transaction.get("total_jpy"),
                "item_count": len(receipt.get("items", [])),
                "source_file": path,
            })
        
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])  # dtype を揃える
    
    return df
        