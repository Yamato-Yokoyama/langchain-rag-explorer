"""
scripts/verify_dataframe.py

load_receipts_as_dataframe() の正しさを検証する。

Ground truth は生 JSON を直接読んで load_receipts_as_dataframe とは独立に計算し、
DataFrame の値と突き合わせる(Day 10 の jq 検証と同じ発想: 実装のロジックを
再利用せず別経路で正解を出すことで、実装のバグと検証のバグが相殺しないようにする)。
"""
from pathlib import Path
import json

from src.load_receipts import load_receipts_as_dataframe

CORPUS_PATHS = sorted(str(p) for p in Path("data/tuebingen").glob("receipts_*.json"))


def ground_truth():
    total_eur = 0.0
    count = 0
    per_month_count: dict[str, int] = {}
    per_month_total: dict[str, float] = {}

    for path in CORPUS_PATHS:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for receipt in data:
            transaction = receipt.get("transaction", {})
            date = transaction.get("date", "")
            month = date[:7] if date else None
            eur = transaction.get("total_eur") or 0.0

            total_eur += eur
            count += 1
            per_month_count[month] = per_month_count.get(month, 0) + 1
            per_month_total[month] = per_month_total.get(month, 0.0) + eur

    return total_eur, count, per_month_count, per_month_total


def main():
    df = load_receipts_as_dataframe(CORPUS_PATHS)

    print(f"shape: {df.shape}")
    print(df.dtypes)
    print(df.head())

    gt_total, gt_count, gt_month_count, gt_month_total = ground_truth()

    df_total = df["total_eur"].sum()
    df_count = len(df)

    print("\n--- 全体突き合わせ ---")
    count_ok = df_count == gt_count
    total_ok = abs(df_total - gt_total) < 0.01
    print(f"件数      : df={df_count}  ground_truth={gt_count}  {'OK' if count_ok else 'NG'}")
    print(f"total_eur : df={df_total:.2f}  ground_truth={gt_total:.2f}  {'OK' if total_ok else 'NG'}")

    print("\n--- 月別突き合わせ ---")
    month_total = df.groupby("month")["total_eur"].sum()
    month_count = df.groupby("month").size()

    all_month_ok = True
    for month in sorted(gt_month_count):
        c_ok = month_count.get(month, 0) == gt_month_count[month]
        t_ok = abs(month_total.get(month, 0.0) - gt_month_total[month]) < 0.01
        all_month_ok = all_month_ok and c_ok and t_ok
        print(
            f"{month}: count df={month_count.get(month, 0)} gt={gt_month_count[month]} {'OK' if c_ok else 'NG'} | "
            f"total_eur df={month_total.get(month, 0.0):.2f} gt={gt_month_total[month]:.2f} {'OK' if t_ok else 'NG'}"
        )

    print("\n=== ALL OK ===" if (count_ok and total_ok and all_month_ok) else "\n=== MISMATCH FOUND ===")


if __name__ == "__main__":
    main()
