# Speech Act分類 Baseline(Issue #39): 何を・なぜ・どう活きるか

> Claude Code支援で実装した内容のレポート。後で見返して「これは自分でやった」と
> 説明できるように、問題設定・プロセス・結果・言語学的な意味づけをまとめておく。

---

## 問題(なぜこれをやったか)

キャリアポジショニングの「引き出し2: Speech Actを使ったエージェント意図分類」の
最初の実装ステップ。CS/CLの両方を持つ人材としての差別化ポイントの1つに、
「発話の意図(Speech Act)を分類できる」という具体的な技術的実績を持たせたかった。
既存のRAGプロジェクトとは独立に、外部対話コーパス(DailyDialog)で汎用のSpeech Act
分類器のbaselineを作り、後で(Non-goalsとして今回は含めない)agentやrouterに
統合する土台にする、という位置付け。

**RAGとの親和性(なぜ「MLがやりたいから」だけではないか)**: これは新しく思いついた
話ではなく、`daily/interview-prep/insights.md` Insight 01・03に既に実データで
記録されている理論的診断を、実装可能なコンポーネントに格上げする作業。Insight 01:
自分のRAGでQ-principleについて聞いた時、Q-principle chunk自体が上位に来ず、
背景chunkが先に来た。原因はBGE-M3が「発話の型(Illocutionary Force)」の一致を
「内容の一致」より優先するため(質問=Directiveは、定義文=Assertiveより、同じ
Directive型の文とマッチしやすい)。Insight 03ではこれを「Speech Actミスマッチ」
という5種類あるRAG失敗パターンの1つとして特定し、対処法を「Query Rewriting」と
既に決めている。Issue #39は、この「Speech Actのミスマッチが原因だ」という診断を
人力ではなく分類器で自動化するための、最初の一歩。

## Input → Process → Output

**Input**
- `li2017dailydialog/daily_dialog`(Hugging Face Hub)。発話単位にflatten後
  train=87,170 / validation=8,069 / test=7,740件
- ラベルは4クラス: inform(45.7%) / question(28.7%) / directive(16.3%) /
  commissive(9.3%)。約5倍のクラス不均衡がある

**Process**
- `src/ml/train_speech_act.py`: TF-IDF(ngram_range=(1,2), min_df=2) +
  sklearn Pipelineで、Naive BayesとLogistic Regressionの2つのbaselineを学習
- `src/ml/inference.py`: 学習済みモデルを読み込み、任意の英文を`predict`/
  `predict_proba`で分類する`SpeechActClassifier`ラッパー
- `notebooks/01_speech_act_baseline.ipynb`: データ探索〜学習〜評価を通しで実行
- 既存のRAGコード(`rag_pipeline.py`, `router.py`, `chainlit_app.py`等)には
  一切手を入れていない(`git diff main...`で確認済み)

**Output**
- `src/ml/models/{nb,lr}_speech_act.joblib`(学習済み重み、.gitignore済み)
- `docs/experiments.md`に定量結果を記録:
  - Naive Bayes: Macro F1 = **0.539**
  - Logistic Regression(`class_weight="balanced"`): Macro F1 = **0.700**

## NB vs LR、なぜこの2つか・よくある誤解

**なぜこの2つを比較したか**: 特別な理由があったわけではなく、テキスト分類で
一番標準的な「教科書ペア」。NBは**生成モデル**(各クラスの発話がどういう単語分布
から生成されるかを学習し、ベイズの定理で逆算する)、LRは**識別モデル**(生成過程は
考えず、単語の出現パターンから直接クラスを分ける重みを学習する)。同じ特徴量
(TF-IDF)を使い、モデルの考え方(生成 vs 識別)だけを変えて比較する設計。
Transformerのfine-tuneは今回のNon-goalsとして明示的に除外しているので、この2つで
十分という判断。

**誤解1: LRは0.6のような閾値で2値(commissive vs それ以外)にしかならない、は誤り**。
今回使っている`LogisticRegression(class_weight="balanced")`は**multinomial
(softmax)方式**で、4クラス全部の確率を同時に計算し、合計1になるよう正規化してから
最大値を選ぶ。NBが「クラスごとに確率を出して比較する」のと同じ形の出力になる
(仕組みは別、出力の形は同じ)。「クラスごとに独立した2値分類器を作り、閾値で
判定する」のはOne-vs-Rest(OvR)という別方式で、今回は使っていない。

**誤解2: `class_weight="balanced"`は既存モデルの微調整(fine-tuning)ではない**。
NB・LRどちらも`train_speech_act.py`で**毎回ゼロから学習している**。
`class_weight="balanced"`は学習させるその瞬間に渡す設定(ハイパーパラメータ)で、
「少数派クラスの間違いをより重く罰する」という学習時のルール。事前学習済みモデルを
後から調整する話ではない。

## 具体的なデータ例(notebookの実出力より)

| クラス | 実際の発話例(DailyDialog) |
|---|---|
| directive(依頼・指示) | "Say, Jim, how about going for a few beers after dinner?" |
| commissive(申し出・約束) | "You know that is tempting but is really not good for our fitness." |
| question(質問) | "What do you mean? It will help us to relax." |
| inform(情報提供) | "Sounds great to me! If they are willing, we could ask them to go dancing with us." |

**誤分類の実例**:

| 発話 | 正解 | LRの予測 | 確率 |
|---|---|---|---|
| "I will send the report by tomorrow." | commissive | directive(誤り) | directive=0.458, commissive=0.187 |

## 結果の中身(数字だけでなく、何が起きたか)

- LRがNBを大きく上回った最大の要因は`class_weight="balanced"`によるクラス
  不均衡の補正。NBはcommissiveのrecallが0.033(ほぼ全て誤分類)だったのに対し、
  LRは0.607まで改善。ただし引き換えにprecisionは0.416まで低下した
  (見逃しを減らすと誤検出が増えるトレードオフが数字で確認できた)
- 両モデルに共通する弱点: **directiveとcommissiveの混同**。
  例: "I will send the report by tomorrow."(commissive)をLRに通すと、
  directiveが最尤(0.458)、commissiveは0.187に留まった

## CLの知識がどう活きたか

ここが単なる「scikit-learnでモデルを2つ回した」で終わらない部分。

1. **なぜdirective/commissiveが混同されるかを理論から説明できる**: TF-IDFの
   bag-of-words表現は語順・主語情報を落とす。"I will send..."(commissive、
   話者自身が引き受ける)と"Please send..."(directive、相手に頼む)は、
   話者の役割(誰が行為の担い手か)が違うだけで表層語彙が近い。これは統語論・
   語用論的な区別であって、単語の出現頻度だけを見るモデルには原理的に見えにくい
   という説明が、Searleの理論的枠組みを知っているからこそできる
2. **DailyDialogの4クラス設計自体への批判的な視点**: Searleの5分類
   (assertive/directive/commissive/expressive/declarative)に対し、DailyDialog
   はexpressive/declarativeが無く、questionをassertiveから独立させている。
   これは「データセットの設計判断が理論を簡略化した結果」であって、単に
   「4クラス問題を解いた」以上の理解を示せる(`docs/speech-act-baseline-primer.md`
   §2に詳細)
3. **次にやるべきことの仮説が立てられる**: 「文脈(語順・主語)を見るモデルなら
   directive/commissive混同がどこまで改善するか」という、TF-IDFの限界から
   導かれる具体的な次の実験仮説を、理論的根拠付きで説明できる

## 面接で聞かれた時の1段の言い回し

「DailyDialogでSpeech Act分類のbaselineを2つ作り、Logistic RegressionがNaive
Bayesをmacro F1で0.539→0.700まで改善することを確認しました。特に面白かったのは、
両モデルともdirectiveとcommissiveを混同する傾向で、これはTF-IDFが語順や主語を
無視するため、"何をするか"は同じでも"誰が行為の担い手か"という語用論的な違いを
捉えられないからだと考えています。次はこの文脈情報をモデルに持たせることで、
この混同がどこまで解消するかを検証したいと考えています。」
