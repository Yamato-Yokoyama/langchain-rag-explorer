# ロードマップ：v1 と v2

> 2026-10-10 決定。v1 を区切って終わらせ、v2 は ESCI の商品データの上に作る
> アイデアや調査メモはここに書かず Obsidian に置く。ここには「何をやれば終わりか」と「どう測るか」だけ書く

## 全体の流れ

RAG は「作れる」ことを見せる柱。ML の [jp-product-search-eval](https://github.com/Yamato-Yokoyama/cl-agent/tree/main/projects/ml/jp-product-search-eval)（ESCI の日本語商品検索を nDCG で測る）は「測れる」ことを見せる柱。この2本を、1つの話につなげる。

> 日本語の商品検索を作って測り（ML）、その上に会話型の買い物アシスタントを載せた（RAG v2）

```
ML（ESCI）           RAG v1                 RAG v2
日本語商品検索  ->   自分データの RAG を  ->  ESCI 商品データ上の
nDCG で測る          区切って完成させる       会話型アシスタント
（数字の柱）         （作れる証拠）           ML の検索を部品として使う
```

LangGraph の構成（ルーター、critic、会話履歴）、MCP、CI は v2 でもそのまま使う。替えるのはデータと検索の部品だけ。

---

## v1：自分データの RAG を区切って完成させる

**目的**：今の RAG を「直した、と数字で言える」状態で閉じる。長く引っ張らない。

### 終了条件（この4つが閉じたら v1 終わり）

| # | やること | 終わりの基準 |
|---|---|---|
| [#42](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/42) | 評価を数字にする | まとまった質問セットで検索の nDCG@10 が1コマンドで出る |
| [#17](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/17) | 否定・除外クエリ（「〜以外」「〜を除く」）を直す | 否定の質問を評価セットに入れ、直す前と後の数字を並べられる |
| [#38](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/38) | CI | push で pytest が回る |
| — | README を最新にする | 構成・結果の数字・再現コマンドが今のコードと合っている |

**なぜ #17 を v1 に入れるか**：否定は ML（ESCI）のエラー分析で「否定あり／なし」に分けて測る現象と同じ。自分のデータで一度直しておくと、ML で大きなデータで測るときの入り口になる。v1 を「課題を見つけて、直して、数字で確かめた」で閉じられる。

### v1 に入れないもの

| Issue | 行き先 |
|---|---|
| [#51](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/51) リランカー、[#52](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/52) 埋め込みの fine-tune | v2。ML のフェーズ C（CrossEncoder の fine-tune）で作ったものを部品として入れる |
| [#35](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/35) 日本語→英語の多言語検索 | v2 で ESCI の jp / us を使って測れるなら拾う |
| [#16](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/16) [#18](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/18) [#19](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/19) [#22](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/22) [#24](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/24) [#36](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/36) [#37](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/37) [#41](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/41) | やらずに残す（v1 の後に必要になったら見直す） |
| [#48](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/48) [#49](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/49) [#50](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/50) | 保留（Speech Act・レシート画像・音声。2本が終わるまで触らない） |

---

## v2：ESCI の商品データ上の会話型アシスタント

**目的**：ML で作った日本語の商品検索を部品にして、LLM と会話しながら商品を探すアシスタントを作る（Amazon Rufus のようなもの）。

**始める条件**：v1 が終わっていること。ML の検索（BM25・埋め込み・組み合わせ）が nDCG 付きで動いていること。

### 構成（案）

- データ：ESCI の日本語の商品（タイトル・説明・ブランドなど）
- 検索：jp-product-search-eval の検索をそのまま呼ぶ（RAG 側で作り直さない）
- 会話：今の LangGraph（文脈の補完 → ルーター → 検索 → critic → 履歴）を流用する

### 測り方（案）

1. キーワード型のクエリ（ESCI のまま）と、会話っぽい言い方のクエリで、検索の nDCG@10 を比べる
2. LLM でクエリを書き換えると、どこまで戻るかを見る
3. 会話っぽいクエリは LLM で作るので、一部を手で見て質を確かめる

### 研究テーマの候補（未決定）

- 会話っぽいクエリ（言外の条件を含む言い方）で商品検索はどこまで崩れ、書き換えでどこまで戻るか（語用論）
- 日本語の単語の区切り方（形態素）で精度がどう変わるか（締切に間に合わせやすい案）
