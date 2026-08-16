---
source: Semantics & Pragmatics course, University of Tübingen
authored_by: [ai-assisted, yamato-notes]
confidence: mixed
date: 2026-06-15
tags: [pragmatics, implicature, gricean, neo-gricean]
---

# Neo-Gricean Implicature

## 背景: Grice から Neo-Grice へ

Grice (1975) は会話の含意(conversational implicature)を、協調原則(Cooperative Principle)と 4 つの maxims で説明した:

- **Quantity**: 必要なだけ情報を提供する(過不足なく)
- **Quality**: 真実だと信じることを言う
- **Relation**: 関連性のあることを言う
- **Manner**: 明瞭に、簡潔に、順序立てて言う

Grice の枠組みは影響力が大きかったが、maxim 同士が競合するケース(例: quantity と manner がぶつかる時どちらが勝つか)を体系的に説明できなかった。

Neo-Gricean pragmatics(Horn 1984, Levinson 2000)はこの問題を、**2 つ(あるいは 3 つ)の原則の相互作用**として再構築した。

> **Yamato のメモ**: これ、LLM の応答生成にそのまま当てはまる気がする。Gemini や Claude が「言われてないことを推測しすぎる / 補いすぎる」現象は、モデルが暗黙に Q や I 原則で動いてるからでは? Week 4 の theory-mapping で書きたい。

## Horn (1984) の Q-principle と R-principle

Horn は Grice の 4 maxims を 2 原則に統合した:

### Q-principle(hearer 志向)
「言えるだけ言え」— 話者は情報的に強い表現を選ぶべき。Q は聞き手のためのもの。

**例**: 「some students passed」→ 「not all students passed」の含意。

なぜか: もし全員合格していたら話者は "all" と言ったはず。"some" を選んだ = "all" は成立していない、と聞き手が推論する。これが **scalar implicature**(尺度含意)。

Horn scale: `<all, most, many, some, few>` のような、情報の強さで並ぶ表現群。

### R-principle(speaker 志向)
「必要以上に言うな」— 話者は最小限の労力で意図を伝えるべき。R は話者のためのもの。

**例**: 「John broke a finger」→ 「John broke his own finger」の解釈。

なぜか: もし他人の指なら話者はそう明示したはず。しない = デフォルト(自分の指)と推論する。

> **Yamato のメモ**: R-principle って、要は「言外の意味を最大化する」ってことか。ちょっと LLM の hallucination と関係ある? モデルが「デフォルトの読み」に流れすぎると事実じゃない情報を「補って」しまう。R-principle 過剰、みたいな。

## Levinson (2000) の 3 原則

Levinson は Horn の 2 原則をさらに分割し、3 つの heuristic として定式化した:

### Q-heuristic
「言われていないことは、成立していない」

### I-heuristic
「単純に述べられたことは、stereotype 的に解釈せよ」

### M-heuristic
「有標な表現には、有標な解釈を割り当てよ」

M の例: 「Sue caused the car to stop」vs 「Sue stopped the car」
- 後者は無標: 普通の方法で止めた(ブレーキを踏んだ)
- 前者は有標: 普通じゃない方法(引っ張った、木にぶつけた、など)

## 実装への含意(RAG 設計との接点)

このセクションは授業内容というより、Yamato の Week 4 theory-mapping ネタメモ。

- **Q-heuristic ↔ Retrieval の recall**: 検索が取ってこなかった情報は「存在しない」と扱うべきか? Neo-Grice 的には Yes(hearer は Q で読む)。しかし RAG では recall 失敗が「情報が存在しない」を意味しない。ここに緊張がある
- **I-heuristic ↔ LLM の default reasoning**: モデルが「言われてないこと」を stereotype 的に補うのは、まさに I-heuristic の実装。ただしこれが hallucination の温床にもなる
- **M-heuristic ↔ Query rewriting**: 有標な質問(例: 「なぜ 3 月 15 日に会議があったのか?」)は、標準的な質問(「会議はいつ?」)と違う情報を求めている。Query intent classification で扱うべき領域

## 未解決の疑問(次回の授業で確認)

- Q と I の競合が起きる場合、どちらが優先されるか?(Horn は Q > R、Levinson は文脈依存と言うが基準が曖昧)
- Scalar implicature の cancelability(「some students passed — actually, all of them did」)を RAG のレスポンス生成で明示的に扱う方法?
- Neo-Grice は monolingual 前提だが、cross-lingual 会話での implicature 計算はどうなる?(Yamato の RAG は日英だから、これ気になる)

## 参考文献

- Grice, H. P. (1975). Logic and conversation.
- Horn, L. R. (1984). Toward a new taxonomy for pragmatic inference: Q-based and R-based implicature.
- Levinson, S. C. (2000). Presumptive meanings: The theory of generalized conversational implicature.