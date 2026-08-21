"""
src/load_receipts.py

月次レシート JSON を Document のリストに変換する Loader。
Markdown loader と同じインターフェース(list[Document])で、
rag_pipeline に統合しやすくする。
"""
import json

from pathlib import Path
from langchain_core.documents import Document
import pandas as pd
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
    # --- 実装ガイド(Yamato が写経する際の設計メモ) ---
    # data/tuebingen/receipts_2026-04.json の 1 件目を目視確認済み。スキーマ:
    #   receipt = {
    #       "receipt_id": str,
    #       "store": {"name": str, "address": str},
    #       "transaction": {
    #           "date": "YYYY-MM-DD", "time": str,
    #           "total_eur": float, "exchange_rate_jpy": float, "total_jpy": float,
    #       },
    #       "items": [ {...}, ... ],   # 空リストのレシートもあり得る、その場合 item_count=0
    #   }
    # → load_receipts_from_json (L12-38) が読んでいる JSON と同一スキーマ。
    #
    # 想定ロジック(load_receipts_from_json の読み込みパターンを踏襲):
    #   1. rows: list[dict] = [] を用意
    #   2. for path in paths:
    #        data = json.loads(Path(path).read_text(encoding="utf-8"))
    #        for receipt in data:
    #            transaction = receipt.get("transaction", {})
    #            store = receipt.get("store", {})
    #            date_str = transaction.get("date", "")
    #            rows.append({
    #                "date": date_str,                        # 3 で pd.to_datetime に変換
    #                "month": date_str[:7] if date_str else None,
    #                "store_name": store.get("name"),
    #                "store_address": store.get("address"),
    #                "total_eur": transaction.get("total_eur"),
    #                "total_jpy": transaction.get("total_jpy"),
    #                "item_count": len(receipt.get("items", [])),
    #                "source_file": path,
    #            })
    #   3. df = pd.DataFrame(rows)
    #      df["date"] = pd.to_datetime(df["date"]) で dtype を揃える
    #      (date を文字列のまま残すと month との二重管理になるので注意)
    #   4. return df
    #
    # 注意点:
    #   - load_receipts_from_json の metadata 構築ロジック(L25-34)と発想は同じだが、
    #     出力先が Document ではなく DataFrame row なのでここでは独立した関数にする
    #   - items が空のレシートは item_count=0 として扱う(欠損/エラーにしない)
    #   - paths が複数ファイルにまたがる場合、月をまたいで concat される想定
    #     (aggregation branch 側で df.groupby("month") する前提)
    ...