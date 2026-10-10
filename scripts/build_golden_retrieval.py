"""
scripts/build_golden_retrieval.py

検索評価(Issue #42)の正解セット eval/golden_retrieval.jsonl を作る。

正解はルールで決める: 質問ごとに「品目名にこのキーワードを含むレシート」を正解(gain 1.0)にする。
人の判断を入れないので、誰が作り直しても同じ正解になる。品目名は日本語訳(name_jp)とドイツ語の原文(name_original)の両方を見る。

対象はリポジトリに入っているレシートだけ(LinkedIn の Connections は個人情報のため git に入れていないので使わない)。

    python scripts/build_golden_retrieval.py
"""

import json
import re
from pathlib import Path

RECEIPTS = sorted(Path("data/tuebingen").glob("receipts_*.json"))
OUT = Path("eval/golden_retrieval.jsonl")

# (質問, 品目名に含まれていれば正解とするキーワード)。日本語・英語・ドイツ語の質問を混ぜる
QUERIES = [
    ("バナナを買ったレシート", ["バナナ"]),
    ("オートミールを買った日", ["オートミール"]),
    ("ビールを買ったのはいつ?", ["ビール"]),
    ("辛ラーメンを買ったレシート", ["辛ラーメン"]),
    ("インスタントコーヒー", ["インスタントコーヒー"]),
    ("シャンプーを買った", ["シャンプー"]),
    ("ハリボーのグミ", ["ハリボー"]),
    ("冷凍ピザを買ったレシート", ["冷凍ピザ"]),
    ("マウルタッシェン", ["マウルタッシェン"]),
    ("歯磨き粉とマウスウォッシュ", ["歯磨き粉", "マウスウォッシュ"]),
    ("receipts where I bought rice", ["米"]),
    ("frozen pizza", ["冷凍ピザ"]),
    ("Haribo gummy bears", ["ハリボー"]),
    ("Maultaschen kaufen", ["マウルタッシェン"]),
    ("Bananen", ["バナナ"]),
]


def _clean(text: str | None) -> str:
    # OCR の出典タグ [cite: 1] などを取り除く
    return re.sub(r"\[cite[^\]]*\]", "", text or "").strip()


def relevant_ids(receipts: list[dict], keywords: list[str]) -> list[str]:
    """Return receipt_ids whose item names (Japanese or original) contain any keyword."""
    hits = []
    for r in receipts:
        names = [_clean(it.get("name_jp")) + " " + _clean(it.get("name_original")) for it in r.get("items", [])]
        if any(kw in name for kw in keywords for name in names):
            hits.append(r["receipt_id"])
    return hits


def main():
    receipts = [r for f in RECEIPTS for r in json.loads(f.read_text(encoding="utf-8"))]
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for query, keywords in QUERIES:
            ids = relevant_ids(receipts, keywords)
            f.write(json.dumps({"query": query, "keywords": keywords, "relevant": ids}, ensure_ascii=False) + "\n")
            print(f"{len(ids):>3}  {query}")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
