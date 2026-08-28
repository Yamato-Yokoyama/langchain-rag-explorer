# Interview Prep: Insights & Talking Points

> Yamato Yokoyama / LangChain RAG Explorer プロジェクト経由の学び
> 面接直前 30 分の読み返し用、実際に口に出せる形で残す
> 元の学びの文脈は各カードの参照リンクから daily note へ

---

## Insight 01: RAG の semantic gap を Speech Act theory で説明できる

**1 行要約**: 素朴な cosine retrieval が失敗する理由の一部は、Speech Act の Illocutionary Force(発話の型)のミスマッチで説明できる。

**面接での 1 段の言い回し**:
「私のプロジェクトで Q-principle についてのクエリを投げた時、Q-principle chunk 自体ではなく背景の chunk が上位に来ました。原因を分析したところ、BGE-M3 は Illocutionary Force、つまり発話の型の一致を Propositional Content、命題内容の一致より優先する傾向がありました。質問(Directive)には定義的な平叙文(Assertive)がマッチしやすく、これは Searle の Speech Act 理論からも予測できます。Query rewriting や HyDE がなぜ効くのか、この観点から理論的に説明できます。」

**深掘りされた時のフォールバック**:
- BGE-M3 は 100+ 言語を同じ空間に押し込む対照学習で訓練されている、その副作用として表層的な文型パターンが強く残る
- Levinson の Universalist 立場(発話行為の分類は言語横断で共通)を援用すれば、多言語 RAG での同現象の予測が可能
- 具体スコア: Q-principle クエリで背景 chunk 0.4398、Q-principle chunk 0.3833、僅差で order が逆転
- HyDE は Directive → Assertive の翻訳を構造的にやる手法

**元の文脈**: [daily/2026-08-11.md](../2026-08-11.md), [daily/2026-08-12.md](../2026-08-12.md)

**この気づきが独自な理由**: 通常の RAG チュートリアルは Speech Act 用語を使わない。Computational Linguistics 出身の Yamato が理論と実装の橋渡しをできる証拠。

---

## Insight 02: Enterprise RAG は Router 型で複数 retrieval を振り分ける

**1 行要約**: 現場の RAG は 1 個のパイプラインではなく、クエリを分類して SQL / BM25 / Semantic / Hybrid に振り分ける Router 型の設計が一般的。

**面接での 1 段の言い回し**:
「私の学習プロジェクトは単一の semantic retrieval から始めましたが、実際の Enterprise では複数のデータ型が混在します。顧客 ID や SKU のような構造化データは SQL 完全一致、数字を含む質問は BM25 と semantic のハイブリッド、多言語ドキュメントは Query Translation を併用、というように retrieval 戦略を Router で振り分ける設計が必要だと理解しています。私のプロジェクトの Week 3 以降で、Neo-Gricean ノート、LinkedIn 投稿、生活費 JSON という異なるデータ型を扱う中で、この分岐設計を実装したいと考えています。」

**深掘りされた時のフォールバック**:
- Router = LLM がクエリを見て「どの retrieval に投げるべきか」を判断する仕組み
- LangGraph の state machine で実装可能、Week 3 で触る予定
- Ece さん(SAP Working Student)の「AI Observability Agent」がまさにこの Router 型
- Adaptive Retrieval(初回スコアが低ければ rewriting にエスカレート)も同じ発想の適用
- SAP、Salesforce、金融機関の RAG チームが日常的に格闘している問題

**元の文脈**: [daily/2026-08-14.md](../2026-08-14.md)

**この気づきが独自な理由**: 「素朴 RAG が動く」で満足せず、Enterprise の実装イメージまで持っている応募者は少ない。SAP 応募との親和性が高い。

---

---

## Insight 03: 素朴 RAG の 5 種類の Semantic Gap を実データで分離

**1 行要約**: RAG が失敗する原因は 1 種類ではなく、少なくとも 5 種類の異なる gap に分解でき、それぞれ対処法が違う。

**面接での 1 段の言い回し**:
「私のプロジェクトで自分の生活費レシート JSON を RAG に組み込んだ時、失敗パターンを 5 種類分離して観察できました。Speech Act ミスマッチ、Chunk Size 希釈、指示性 Gap、集計不能、スコア接近です。それぞれ対処技術が違い、Speech Act は Query Rewriting、Chunk Size は Small-to-Big Retrieval、指示性は Data Enrichment、集計不能は SQL 層併用、スコア接近は chunk 統合、と対応します。単一の RAG パイプラインで全部解けないので、実務では Router で振り分ける Enterprise 設計が必要だと理解しています。」

**深掘りされた時のフォールバック**:
- 各 gap の具体例をノートから引用可能(Q-principle クエリ、留学生食費クエリ、集計クエリ)
- Anthropic の Contextual Retrieval 論文が指示性 Gap への一つの解決策
- Speech Act 分類は Yamato の Semantics & Pragmatics 授業由来、Searle の 5 分類が背景

**元の文脈**: [daily/2026-08-11.md](../2026-08-11.md), [daily/2026-08-12.md](../2026-08-12.md), [daily/2026-08-15.md](../2026-08-15.md)

**この気づきが独自な理由**: 通常の RAG チュートリアルは「retrieval が動きました」で終わる。「なぜ失敗するか」を 5 種類に分離できる学生は稀。しかも実データ(自分の生活費)で観察している。

---

## Insight 04: RAG の Context 問題は Common Ground の欠如、対処は Enrichment か Contextualization

**1 行要約**: LLM は暗黙のユーザー背景を補ってくれないので、Document 側か Query 側で明示的に注入する必要がある。

**面接での 1 段の言い回し**:
「私のレシート RAG で『留学生はどんな食べ物?』と聞いた時、retrieval は成功したのに LLM が『情報がありません』と答えました。document 側に『留学生』という主体情報が無いため、Speech Act の共有前提 (Common Ground) が成立していなかったからです。実務では 2 種類の対処法があります。Query Contextualization はユーザー情報を query に注入する方法で、SAP 顧客サポートで契約 ID を自動注入するようなケースに使われます。Data Enrichment は document 側に文脈を注入する方法で、契約書 chunk の冒頭に顧客・年度を自動追加するようなケースです。私は Yamato ユーザーが 1 人なので Data Enrichment を選択、chunks の冒頭に『Tübingen で生活する日本人留学生 Yamato の生活費記録』を注入して、スコアが 0.50 から 0.60 に改善しました。」

**深掘りされた時のフォールバック**:
- 副作用: 全 chunk に同じテキスト = 差別化が弱まる、Grice の Quantity Maxim 違反と読める
- 2 種の使い分け: ユーザー多い場面 → Contextualization、Document 多い場面 → Enrichment
- Theory mapping: Common Ground を陽に構築する技術として位置づけ可能

**元の文脈**: [daily/2026-08-15.md](../2026-08-15.md)

**この気づきが独自な理由**: Common Ground 理論と実装対処法(Enrichment/Contextualization)を直接接続できる。Speech Act 教育を受けた CL 学生の武器。

---

## Insight 05: asyncioイベントループのブロッキングでサーバーが「死んで見える」

**1行要約**: `async def`の中で`await`を挟まない重い同期処理(埋め込み計算)を呼ぶと、プロセスは生きているのにイベントループ全体が固まり、外からは「接続できないサーバー」に見える。

**面接での1段の言い回し**:
「Chainlitアプリで、新しいチャットセッションが始まるたびに埋め込みベクトルの構築という重い同期処理を呼んでいました。ChainlitはFastAPI/Starlette系の非同期フレームワークで、全セッションを1本のイベントループで処理しています。`await`を挟まない同期処理を挟むと、その間イベントループの制御が一切戻らず、他の全ユーザーの通信が止まります。フロントエンドからは『サーバーに接続できませんでした』というエラーに見えますが、実際はプロセスは生きていて応答できないだけでした。修正は、重い初期化処理をセッションごとの処理からアプリ起動時に1回だけ実行するモジュールレベルの処理に移したことです。」

**深掘りされた時のフォールバック**:
- FastAPI公式ドキュメントでも「asyncハンドラ内でのブロッキング同期処理」は明記された既知の罠
- 対処は2パターン: (1) 重い初期化は起動時に1回(今回はこれ)、(2) 避けられない同期処理はスレッドプールに逃がす
- ディスクキャッシュ(pickle)は別レイヤー: 「いつ実行するか」ではなく「同じ計算を繰り返さない」ための仕組み

**元の文脈**: [daily/interview-prep/chainlit-asyncio-event-loop-blocking.md](chainlit-asyncio-event-loop-blocking.md)(図解・timeline付きの深掘り版), [daily/2026-08-27.md](../2026-08-27.md)

**この気づきが独自な理由**: 個人プロジェクトのバグ修正を「非同期フレームワークにおけるイベントループのブロッキング」という一般化された概念として説明できる。SAP等のFastAPI/Starlette系Enterprise backendで頻出するクラスの問題であり、単なる「バグ直しました」で終わらせず設計原則として言語化できている。

---

## Future Enhancement: Visual Documentation

**1 行要約**: 設計ドキュメントに Graphviz(DOT 言語)で生成した diagram を添える運用を Day 11 で開始、文章だけでなく視覚的にも設計を残せるようにした。

**面接での 1 段の言い回し**:
「Day 11 で Router 型 RAG の設計をドキュメント化する際、文章だけでなく Graphviz の DOT 言語で data flow diagram も作成しました。画像を直接コミットするのではなく DOT ソースをバージョン管理下に置くことで、diff で差分レビューができ、必要なら CI で再レンダリングもできる形にしています。設計判断の理由を文章で説明しつつ、全体構造を一目で把握できる図を添えることで、レビュアーやチームメンバーへの説明コストを下げられると考えています。」

**深掘りされた時のフォールバック**:
- なぜ画像だけでなく DOT ソースもコミットするか: テキストベースなので `git diff` でレビューでき、バイナリの画像ファイルより軽量で差分も追える
- 現状は router-overview.dot 1 枚だが、Router の 3 分岐が実装フェーズごとに更新していく想定
- Enterprise では Confluence や ADR(Architecture Decision Record)に diagram を添えるのが一般的、同じプラクティスを個人プロジェクトに導入した形

**元の文脈**: [docs/router-design-sketch.md](../../docs/router-design-sketch.md), [daily/2026-08-19.md](../2026-08-19.md)

**この気づきが独自な理由**: 個人の学習プロジェクトでも、書きっぱなしのメモではなくバージョン管理された図付きの設計ドキュメントとして残す習慣は、実務のドキュメンテーション文化に近い。