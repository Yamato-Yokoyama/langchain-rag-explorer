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

**目的**：今の RAG を「数字で測れる」状態で閉じる。長く引っ張らない。中身（LangGraph・ルーター・MCP）は v2 でそのまま使う。

### 終了条件（2026-10-11 改定：この2つで v1 終わり）

| # | やること | 終わりの基準 |
|---|---|---|
| [#42](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/42) | 評価を数字にする | 質問セットで検索の nDCG@10 が1コマンドで出る |
| — | README を今の姿に直す | 構成・#42 の数字・再現コマンドが今のコードと合っている |

**#42 は新しい進め方の試運転にする**：Claude が PR を出し、説明に選択式のレビューの問いを付ける。自分はインターンとしてレビューし（問いに答える、わざと入れたバグを1つ直す、1つ変える）、マージして数字を出す。ML（ESCI）で手計算した nDCG・BM25 の練習も兼ねる。

**#17 否定・除外と #38 CI は v2 に移す**（2026-10-11）。否定は ESCI の正解ラベルで測れるので、v2 で数字付きで直す。CI は v2 のリポジトリの形が決まってから入れる。

### v1 に入れないもの

| Issue | 行き先 |
|---|---|
| [#17](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/17) 否定・除外、[#38](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/38) CI | v2。否定は ESCI の正解ラベルで前後の数字を出す |
| [#51](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/51) リランカー、[#52](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/52) 埋め込みの fine-tune | v2。ML のフェーズ C（CrossEncoder の fine-tune）で作ったものを部品として入れる |
| [#35](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/35) 日本語→英語の多言語検索 | v2 で ESCI の jp / us を使って測れるなら拾う |
| [#16](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/16) [#18](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/18) [#19](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/19) [#22](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/22) [#24](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/24) [#36](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/36) [#37](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/37) [#41](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/41) | やらずに残す（v1 の後に必要になったら見直す） |
| [#48](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/48) [#49](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/49) [#50](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/50) | 保留（Speech Act・レシート画像・音声。2本が終わるまで触らない） |

---

## v2：ESCI の商品データ上の会話型アシスタント

**目的**：ML で作った日本語の商品検索を部品にして、LLM と会話しながら商品を探すアシスタントを小さく作る（Amazon Rufus のようなもの）。

人に一言で言うなら：今は「Amazon の公開データで日本語の商品検索を作って、どれだけ正しく並ぶかを測っている」。v2 ができたら「その検索の上に、Rufus のような会話型の買い物アシスタントを小さく作った」。「Rufus を作っている」とは言わない（規模も中身も違う）。⚠️ Rufus が日本語でどこまで提供されているかは未確認

**始める条件**：v1 が終わっていること。ML の検索（BM25・埋め込み・組み合わせ）が nDCG 付きで動いていること。

### 構成（案）

- データ：ESCI の日本語の商品（タイトル・説明・ブランドなど）
- 検索：jp-product-search-eval の検索をそのまま呼ぶ（RAG 側で作り直さない）
- 会話：今の LangGraph（文脈の補完 → ルーター → 検索 → critic → 履歴）を流用する

### 測り方（案）

1. キーワード型のクエリ（ESCI のまま）と、会話っぽい言い方のクエリで、検索の nDCG@10 を比べる
2. LLM でクエリを書き換えると、どこまで戻るかを見る
3. 会話っぽいクエリは LLM で作るので、一部を手で見て質を確かめる
4. 否定・除外（#17）を含むクエリで、直す前と後の nDCG を比べる
5. （候補）商品の説明文に命令を仕込まれたとき（間接プロンプトインジェクション）、答えがどれだけ崩れるかを測る。商品の文章は出品者が書く「信用できない文章」なので、評価と頑健性の横断テーマに当たる
6. （候補）LLM-as-judge：LLM に E/S/C/I を付けさせ、人のラベルとの一致（kappa）を見る

### 研究テーマの候補（未決定）

- 会話っぽいクエリ（言外の条件を含む言い方）で商品検索はどこまで崩れ、書き換えでどこまで戻るか（語用論）
- 日本語の単語の区切り方（形態素）で精度がどう変わるか（締切に間に合わせやすい案）
