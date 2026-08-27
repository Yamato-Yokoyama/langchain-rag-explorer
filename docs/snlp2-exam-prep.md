# SNLP2試験対策とこのプロジェクトの接続

> [docs/why.md](why.md)から分割(2026-08-27)。2027年7月下旬のSNLP2(Statistical NLP 2)最終試験に向けた棚卸し。

参考シラバス: https://snlp2-2026.github.io/lectures.html (Tübingen大学 Statistical NLP 2、Çağrı Çöltekin担当)

**重要な前提の確認**: このページの2026年度日程は既に試験(7/24)まで終わっている。自分の試験は2027年7月下旬なので、参照しているのは**次の年度の同名科目のシラバス構成**のはず。年度ごとの日程はズレるが、扱うトピックの並び(math recap → regression/classification → gradient descent → linguistic representations → ANN → sequence learning/RNN → Transformer → pretrained LMs → LLMs → 評価)は毎年大きくは変わらない前提で、このトピック構成を対策の土台にする。

## このプロジェクトが既に実質的にカバーしている範囲

| シラバスのトピック | このプロジェクトでの実践 | どこで |
|---|---|---|
| Learning linguistic representations(embeddings) | BGE-M3で実際に埋め込み、PCAで可視化、コサイン類似度で検索 | [data-flow-markdown-neo-gricean.md](../daily/interview-prep/data-flow-markdown-neo-gricean.md), `daily/2026-08-10.md` |
| Transformer / Pretrained LMs / LLMs | Geminiを実際にAPI経由で呼び、SystemMessage/HumanMessageの構造、multilingal embeddingの挙動を体感 | [pragmatics-in-rag-query-processing.md](../daily/interview-prep/pragmatics-in-rag-query-processing.md) §3 |
| Evaluation in NLP | Ground truthとの突き合わせ(`jq`での正解値取得 vs LLM出力の系統誤差検証)を実データで実施済み | `daily/2026-08-19.md`(171件のground truth検証) |
| Unsupervised learning(の一端) | PCAによる次元圧縮と意味クラスタの可視化 | `daily/2026-08-10.md`学び⑥⑦ |

**このカバレッジの性質を正確に理解しておくこと**: これは全て「訓練済みモデルを"使う"側」の実践。LangChain/HuggingFaceが内部実装を隠しているので、**"何が起きているか"の直感と語彙は身につくが、"どう実装されているか"の数式・アルゴリズムの手も足も動かしていない**。試験は後者(具体的な計算、実装レベルの理解)を問う可能性が高いので、ここは正直に別枠として扱う。

## このプロジェクトではカバーできていない範囲(要注意)

| シラバスのトピック | このプロジェクトでの現状 | 理由 |
|---|---|---|
| Math recap(線形代数) | 触れていない | LangChain/numpyがベクトル演算を隠蔽している |
| Regression / Classification(基礎) | 触れていない | ライブラリのAPIを呼ぶだけで、モデルの中身を実装していない |
| Gradient Descent | 触れていない | 埋め込み・LLMは全て訓練済みモデルを使うだけ、自分で学習ループを書いていない |
| ANN intro / CNN | 触れていない | このプロジェクトにCNNの出番がそもそも無い(画像を扱っていない) |
| Sequence Learning / RNN | 触れていない | Transformerベースのモデルを使うのみ、RNNの実装経験なし |
| Cross-entropy等の損失関数 | 触れていない | 訓練を一度もしていないので損失関数を書いたことがない |

## 埋め方の提案: 別教材に逃げず、このプロジェクトの中に小さな「理論実装」枠を作る

「別のコースを取る」ではなく、**このプロジェクトの中に、上記の未カバー分野だけを狙った小さなスクリプトを足していく**方法を提案する。理由: (1) 専門性の物語が途切れない([specialty-positioning.md](specialty-positioning.md))、(2) 実装の手触りが伴う方が定着しやすいと本人が既に自覚している学習様式(`daily/2026-08-13.md`学び⑤の「探索フェーズ→整理フェーズ」、[rag-direction-and-learning-method.md](rag-direction-and-learning-method.md)参照)に合う。

イメージ(例、実装はまだしていない、次にやる時の叩き台):

- `scripts/theory/gradient_descent_from_scratch.py`: numpyだけでレシートの支出データに線形回帰を当てはめ、gradient descentを手で実装。既存の`aggregations.py`のデータをそのまま使える
- `scripts/theory/embeddings_math.py`: BGE-M3が返す1024次元ベクトルに対して、cosine similarityを自作(既に`src/similarity.py`にある)ではなく、内積・ノルムの数式から書き下して、`docs/notes/`にnumpy実装と数式の対応をメモ
- CNN/RNNは本プロジェクトの題材(テキストのみ)と相性が悪いので、**無理に本プロジェクトに詰め込まず、シラバスのその週だけは素直に講義スライド+別演習で対応する**、と決めておく(全部を1つのプロジェクトに押し込む必要はない)

**この節の使い方**: 試験が近づいたら、上の「カバーできていない範囲」の表を見て、その週だけピンポイントで講義資料に戻る。それ以外は今まで通りプロジェクトを進めればよい、という安心材料として機能させる。
