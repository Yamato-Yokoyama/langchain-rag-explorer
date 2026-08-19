# Router-Type RAG Design Sketch

## Overview

### Problem

既存アプローチ(素朴な RAG、Query Rewriting + top_k 調整)では、集計クエリがうまくいかなかった。ドキュメント数が増えていくと top_k の調整だけでは対応しきれなくなるため、Router が必要だと判断した。

LLM はそもそも集計計算が苦手。SQL やテーブルのようにあらかじめ構造化データとして定義できるものは、先に構造化データ層(DataFrame / DB)として用意しておいた方が精度も上がり、LLM に全件読ませるより消費トークンも抑えられる。

実際に Query Rewriting + top_k 調整を行い、全 Docs を retrieval に含めても、各レシートの件数が実際の値と食い違い、せっかくメタデータを持たせていたのに合計金額も大きくズレた。Day 10 の全10ヶ月コーパス(171 receipts, 1474.55 EUR)で aggregation query を検証した結果、retrieval 改善だけでは集計問題は解けないことが実データで確定した:

- **Retrieval bottleneck** (top_k=50): LLM 回答の合計がぴったり top_k と一致、chunk 数上限が集計精度を頭打ちにする
- **Arithmetic bottleneck** (top_k=all=171): 全件見えても月別グルーピングを 10ヶ月中 9ヶ月で誤答、合計金額は systematic に +162 EUR 過大

結論: 意味検索(semantic retrieval)と集計計算(deterministic aggregation)は別レイヤーで扱う必要がある。単一パイプラインで両方を LLM に任せる設計には原理的な限界がある。

### Solution: Intent-based Routing

Query を intent で3分類し、それぞれ適した処理層にディスパッチする Router 型 RAG を導入する。aggregation / table_display 系は構造化データ層(pandas / SQL)をあらかじめ用意しておくことで、集計のたびに全件を LLM に読ませる必要がなくなり、消費トークンも抑えられる。

### Data Flow

`docs/diagrams/router-overview.dot` に DOT source を配置。レンダリング済み画像は `docs/diagrams/router-overview.png`。

(画像はここに埋め込み: `![Router Overview](./diagrams/router-overview.png)`)

### Three Branches (概要のみ、詳細は後述)

| Intent | 例 | 処理層 |
|---|---|---|
| `semantic` | "神経文法性の implicature とは?" | 既存 RAG(embedding retrieval + LLM generation) |
| `aggregation` | "4月の合計支出は?" | 構造化データ層(pandas / SQL)+ LLM で自然文整形 |
| `table_display` | "全レシート一覧を表で" | 構造化データ層 → 表形式で直接出力 |

### 既存コードの位置づけ

`rag_pipeline.py` の3関数は semantic branch の内部実装として温存:

- `build_index()`: index 構築(全 branch で index 自体は共有)
- `search()`: semantic branch でのみ呼ばれる
- `generate_answer()`: semantic branch と aggregation branch(整形時)で呼ばれる

Router 層は新規追加、既存 API は破壊しない。

### スコープ外(Phase 2 課題)

- **マルチターン照応**: 「その中で一番高いのは?」のような follow-up query の解決。Day 10 で欠如を確認済み、Router の各 branch が独立してるうちは扱わない。会話 state 管理層を別途導入する Phase で対応。