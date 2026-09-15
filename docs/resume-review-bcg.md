# レジュメ添削メモ(BCG版)

> 2026-09-09作成、2026-09-10更新。現行レジュメ(`Yamato_Yokoyama_Resume.pdf` 相当のテキスト)をベースに、直すべき箇所だけを最小差分で記録する。全面リライトはしない。コード側(`src/`)、および `~/home/nlp/Personal/Compound`(German Compound Word Classifier の実体)の実装内容と突き合わせて事実確認済み。

## 2026-09-10 訂正: German Compound Word Classifier は削除ではなく残す

前回のメモでは「未完了」と判断してPROJECTSから削除する方針にしていたが、本人確認の結果これは誤り。実体は `~/home/nlp/Personal/Compound`(README上は "Multilingual Retrieval Diagnostic" という4週間の自己企画プロジェクトのWeek 1)で、Statistical NLPのコースデータを使いつつ自発的にスコープを広げたもの。`Week1/main.ipynb` を実際に読んで裏取り:

- 特徴量: 単語長・母音の割合・ハイフンの有無という手作りの言語的特徴量(n-gram や TF-IDF ではない)。
- モデル: `sklearn.pipeline.Pipeline([StandardScaler, LogisticRegression])`。
- 検証: `StratifiedKFold(n_splits=5)` で `f1_macro` を計測。

ここまでは現行レジュメの記述と一致。**ただし** `LogisticRegression()` は確認できた範囲ではデフォルト引数のままで、`GridSearchCV` 等の明示的なハイパーパラメータ探索コードは見当たらなかった。つまり現行レジュメの "tune hyperparameters" という文言と、SKILLS欄の "regularization (L1/L2)" は、見つかった証拠では裏付けが弱い。

**対応方針(下記に反映済み)**: "tune hyperparameters" は削除し、実際に確認できた "stratified k-fold cross-validation でdata leakageを防いだ" という記述に差し替え。SKILLS欄の "regularization (L1/L2)" も一旦削除し、"Logistic Regression" のみ残す(これは実際に使っている)。もし後で `GridSearchCV(penalty=['l1','l2'], ...)` を実装して主張を事実にするなら、そのタイミングで両方とも復活させればよい。

## 変更箇所

### 1. PROJECTS: LangChain RAG Explorer のブロックを差し替え

**現行**:
```
LangChain RAG Explorer | Personal Project (In Progress)
- Building a multilingual (Japanese/English) RAG system over personal documents
  (course notes, LinkedIn posts, CV) using LangChain, BGE-M3 embeddings, and ChromaDB.
- Designed with a theory-to-implementation mapping: applying pragmatics concepts
  (Common Ground, Question Under Discussion) from Semantics & Pragmatics coursework
  to diagnose retrieval and response quality.
- Tech: Python, LangChain, Gemini API, BGE-M3, ChromaDB.
```

**差し替え後**:
```
LangChain RAG Explorer | Personal Project (In Progress)
- Building a multilingual (Japanese/English) RAG system over my own knowledge base —
  course notes, LinkedIn connections, and monthly receipt JSON — using LangChain,
  Chainlit, and BGE-M3 on ChromaDB, with LangGraph as the emerging state layer.
- Iterated daily with Claude Code: added a receipt-JSON loader (data structured via
  a Gemini schema), wired up a Chainlit chat UI, and migrated a hand-written query
  router into a LangGraph state graph for conversation state.
- Applied Semantics & Pragmatics coursework (Speech Acts, Common Ground, Question
  Under Discussion) as a diagnostic lens to classify retrieval failures on real data
  and pick fixes per type — query rewriting, data enrichment, or a deterministic
  pandas aggregation fallback.
```

**変更点の根拠**:
- tech line は削除(パターンY通り)。
- 1つ目のbulletに Chainlit / LangGraph / 実データ種別(LinkedIn connections, receipt JSON)を追加。`src/chainlit_app.py`, `src/graph_router.py`, `src/load_receipts.py`, `src/load_linkedin.py` で実装確認済み。
- 3つ目のbulletの **"a SQL fallback" → "a deterministic pandas aggregation fallback"** に訂正。実装は SQL ではなく `src/aggregations.py` の pandas `groupby`。ここは前回の相談で指摘済みの誤記で、面接で深掘りされると事実と食い違うため必ず直す。

### 2. PROJECTS: German Compound Word Classifier のブロックを書き換え(削除ではない)

**現行**:
```
German Compound Word Classifier | Statistical NLP, Universität Tübingen
- Engineered an end-to-end ML pipeline classifying German compound words;
  achieved F1 = 0.88, ranked 14 on class leaderboard.
- Used scikit-learn Pipeline (StandardScaler + Logistic Regression) with
  cross-validation to prevent data leakage and tune hyperparameters.
  Tech: Python, scikit-learn, pandas.
```

**差し替え後(2026-09-10 22:xx 版、BIO-tagging言及を削除済み)**:
```
German Compound Word Classifier | Self-Directed Project (Statistical NLP coursework data, Universität Tübingen)
- Engineered hand-crafted linguistic features (word length, vowel ratio, hyphen
  presence) into a scikit-learn Pipeline (StandardScaler + Logistic Regression) to
  classify German words as compound vs. non-compound, validated with stratified
  k-fold cross-validation to guard against data leakage — F1 = 0.88, ranked 14 on
  the class leaderboard.
- Framed as a linguistics problem before an ML one: German compounding and
  Japanese's lack of word boundaries are the same structural challenge that breaks
  naive tokenization in multilingual search/RAG systems.
```

**変更点の根拠**:
- タイトル行を "Statistical NLP, Universität Tübingen" → "Self-Directed Project (Statistical NLP coursework data, ...)" に変更。実体(`~/home/nlp/Personal/Compound`)のREADMEを読むと、コースが用意したデータセットは使いつつも4週間ロードマップ(Week1: 分類 → Week2: 分割 → Week3: 文書分類 → Week4: 検索MVP)は自己企画で、単なる授業課題以上の内容。過小評価しない書き方にした。
- bullet 1: "an end-to-end ML pipeline" という曖昧な書き方を、実際に確認した特徴量(単語長・母音率・ハイフン有無)とモデル構成に差し替え。"tune hyperparameters" は上記の理由で削除し、実際に確認できた "stratified k-fold cross-validation" に差し替え。
- bullet 2: 言語学フレーミング(ドイツ語の複合語とスペースなしの日本語は同じ構造的課題で、素朴なtokenizationを壊す)はREADMEに既にあった記述をそのまま起こしたもので、そのまま残す。**ただし文末の "the motivation for extending this into a segmentation (BIO-tagging) task next" は削除した** — `week2/`は着手途中で完了していないため、未完了の作業を成果であるかのように書くべきではないという本人判断。

**L1/L2の記憶違いについて(訂正)**: 前回この文書で「Compound Word Classifierでは明示的なL1/L2比較コードが見当たらない」と書いたが、これに対して本人から「実際にL1/L2の正則化をやった記憶があるのは、たぶんNLP1の回帰課題(`p1-yama1`、ランダムベースラインのある課題)の方だった」との回答があった。つまりL1/L2の経験自体は実在するが、それはCompound Word Classifierのプロジェクトではなく別の課題での経験であり、レジュメのCompound Word Classifierの行に書くのは誤り。今回SKILLS欄から"regularization (L1/L2)"を削除した判断は妥当だったことになる(このプロジェクトのSKILLSとしては書かない、で確定)。`p1-yama1`をレジュメに載せるかどうかは別の検討事項で、今回はスコープ外。

### 3. SKILLS & LANGUAGES: ML/NLP 行を更新(追加2語・L1/L2は一旦削除)

**現行**:
```
ML / NLP: scikit-learn, pandas, NumPy, LangChain, RAG systems, embeddings (BGE-M3),
vector databases (ChromaDB), prompt engineering, Logistic Regression, regularization (L1/L2)
```

**差し替え後**:
```
ML / NLP: scikit-learn, pandas, NumPy, LangChain, LangGraph, Chainlit, RAG systems,
embeddings (BGE-M3), vector databases (ChromaDB), prompt engineering,
Logistic Regression
```

**根拠**:
- LangGraph・Chainlit は `src/graph_router.py` / `src/chainlit_app.py` で実装済みなので追加。
- **"regularization (L1/L2)" は削除**。`Week1/main.ipynb` で確認できたのはデフォルト引数の `LogisticRegression()` のみで、L1/L2どちらのペナルティを使うか・正則化強度をどう選んだか、という明示的な比較・探索コードは見当たらなかった。"Logistic Regression" は実際に使っているので残す。もし `GridSearchCV(param_grid={"classifier__penalty": ["l1","l2"], ...}, solver="liblinear")` のようなコードを実際に追加すれば、そのとき正当な主張として復活させられる(10分程度の作業)。

### PROJECTS全体の分量について

RAG Explorer(3 bullets)+ Compound Word Classifier(2 bullets)= 5 bullets。EXPERIENCEセクションの合計bullet数(3ポジション、計5 bullets)と同程度なので、レジュメ全体のバランスとしては破綻しない想定。1ページに収まるか気になる場合は、Compound Word Classifierのbullet 2(言語学フレーミング)を削って1bulletに縮められる(その場合、言語学アピールはRAG Explorer側の3つ目のbulletだけで担うことになる)。

## 変更しない箇所(確認済み、そのままでOK)

- **EDUCATION**: 変更なし。
- **EXPERIENCE**: 変更なし。特に MetaMoJi の AI Product Intern はそのまま残す — BCGのJD("assisting with prompt optimization")と直接一致するので削らない。
- **AI Tools 行**(Claude, ChatGPT, Gemini, NotebookLM, Claude Code): 変更なし。Cursor / n8n は**追加しない**— JDが "a plus" として挙げているが実際に使っていないため。使っていないツールを書くと深掘りされたときに詰まる。
- **Tools / Languages / Work Authorization**: 変更なし。
- ファイル名: `Yamato_Yokoyama_Resume_BCG.pdf` にリネーム(前回合意通り)。

## リポジトリ側の対応(このドキュメントと同時に完了)

- `README.md` を全面更新。以前は "Week 1 in progress" のまま止まっていたstale表記(Chainlit/LangGraphが未着手扱いになっていた)を、実際の実装状況(両方とも完了)に合わせて修正。GitHubリンクを踏んだ採用担当がスキャフォールドのまま止まって見える問題はこれで解消。
- 併せて壊れていたリンク(`docs/theory-mapping.md` — 存在しないファイルへの参照)を、実在する `docs/specialty-positioning.md` / `docs/rag-direction-and-learning-method.md` 等に差し替え。

## レジュメのRAGデータ化(実施済み・非公開)

`data/resume/resume_bcg.json` としてレジュメ本文(このメモの内容を反映したBCG版)を構造化データ化し、`src/load_resume.py` で receipts と同じ `list[Document]` インターフェースの loader を実装した。セクション(contact/education/experience/projects/skills)ごとに1 Documentに分割し、`resume_version` / `section` を metadata に付与済み。

**公開範囲**: このリポジトリはPublicだが、電話番号を含むため `data/resume/` は `.gitignore` に追加し、今のところローカルのみ(GitHubには上げない)。後日、電話番号をマスクした版を別途 `data/resume/` 内に置き、そちらだけ `.gitignore` の例外にする形で公開する予定(現時点では未実施)。

**未実施**: `rag_pipeline.py` / `chainlit_app.py` への実際のワイヤリング(`load_resume_from_json` を呼んでインデックスに含める)はまだ。今回はデータ層とloaderまで。
