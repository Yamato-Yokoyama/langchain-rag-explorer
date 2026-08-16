"""
src/load_receipts.py

月次レシート JSON を Document のリストに変換する Loader。
Markdown loader と同じインターフェース(list[Document])で、
rag_pipeline に統合しやすくする。
"""
import json

from pathlib import Path
from langchain_core.documents import Document
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