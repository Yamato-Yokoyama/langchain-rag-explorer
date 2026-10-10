"""
src/eval_retrieval.py

検索の精度を nDCG@k と Recall@k で測る(Issue #42)。

正解セットは eval/golden_retrieval.jsonl(scripts/build_golden_retrieval.py が作る)。
1行 = 質問1つと、正解のレシートの receipt_id のリスト。
本番と同じ collection(LinkedIn・レシート全部)に対して search() を呼び、上位 k 件に正解がどれだけ上に来たかを測る。

    python -m src.eval_retrieval              # nDCG@10・Recall@10、結果を results/retrieval_eval.csv に保存
    python -m src.eval_retrieval --k 5

Depends on:
    - src/rag_pipeline.py(build_index, search)
    - src/metrics.py
"""

import argparse
import csv
import json
from pathlib import Path

from src import metrics

GOLDEN = Path("eval/golden_retrieval.jsonl")
RESULTS = Path("results/retrieval_eval.csv")


def load_golden(path: Path = GOLDEN) -> list[dict]:
    """Read the golden set: one {"query", "relevant"} per line."""
    cases = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue  # 空行は飛ばす
            cases.append(json.loads(line))
    return cases


def item_id(metadata: dict) -> str | None:
    """The id a golden label refers to. Receipts use receipt_id; other documents have no label (None)."""
    return metadata.get("receipt_id")


def gains_for(retrieved_ids: list[str | None], relevant: set[str]) -> list[float]:
    """Gain per retrieved rank: 1.0 if that document is a correct answer, else 0.0."""
    gains = []
    for rid in retrieved_ids:
        if rid in relevant:
            gains.append(1.0)
        else:
            gains.append(0.0)
    return gains


def evaluate_query(retrieved_ids: list[str | None], relevant_ids: list[str], k: int) -> dict:
    """nDCG@k and Recall@k for one query."""
    relevant = set(relevant_ids)
    gains = gains_for(retrieved_ids, relevant)
    return {
        "ndcg": metrics.ndcg(gains, k),
        "recall": metrics.recall(retrieved_ids, relevant, k),
        "hits": int(sum(gains[:k])),
        "n_relevant": len(relevant),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10)
    args = ap.parse_args()

    # 重い import(埋め込みモデルの読み込み)は実行時だけにして、テストを軽くする
    from src.chainlit_app import SEMANTIC_PATHS
    from src.rag_pipeline import build_index, search

    collection = build_index(SEMANTIC_PATHS)
    rows = []
    for case in load_golden():
        hits = search(case["query"], collection, top_k=args.k)
        retrieved_ids = []
        for _score, doc in hits:
            retrieved_ids.append(item_id(doc.metadata))
        rows.append({"query": case["query"], **evaluate_query(retrieved_ids, case["relevant"], args.k)})

    print(f"{'nDCG':>6} {'Recall':>6} {'hits':>9}  query")
    for r in rows:
        print(f"{r['ndcg']:6.3f} {r['recall']:6.3f} {r['hits']:>4}/{r['n_relevant']:<4}  {r['query']}")
    total_ndcg = 0.0
    total_recall = 0.0
    for r in rows:
        total_ndcg = total_ndcg + r["ndcg"]
        total_recall = total_recall + r["recall"]
    mean_ndcg = total_ndcg / len(rows)
    mean_recall = total_recall / len(rows)
    print(f"\nmean nDCG@{args.k} = {mean_ndcg:.3f}   mean Recall@{args.k} = {mean_recall:.3f}   ({len(rows)} queries)")

    RESULTS.parent.mkdir(exist_ok=True)
    with RESULTS.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["query", "ndcg", "recall", "hits", "n_relevant"])
        w.writeheader()
        w.writerows(rows)
    print(f"→ {RESULTS}")


if __name__ == "__main__":
    main()
