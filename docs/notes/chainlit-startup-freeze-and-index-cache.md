---
type: learning-note
date: 2026-08-27
topic: [chainlit, huggingface, caching, performance, debugging, asyncio]
status: living-doc
---

# Chainlitアプリが起動しない/遅い問題 — 原因と対応まとめ

## 背景・最初の症状

`chainlit run src/chainlit_app.py` で起動しても、ブラウザ側が「サーバーに接続できませんでした」の画面から進まない状態になっていた。ターミナルにはプロセスが生きている様子(HuggingFace Hubへの大量のHTTPログ)が流れ続けるので、一見サーバーは動いているように見えるが、いつまで経ってもチャット画面(`RAG pipeline 準備完了。`)まで辿り着けない。Mac本体・ターミナルを再起動しても解消しなかった。

実際には**2つの独立した問題**が重なって起きていた。

---

## 問題1: `on_chat_start` の中で毎回、全コーパスの埋め込み計算をしていた

### 症状
サーバープロセス自体は動いているのに、ブラウザが「サーバーに接続できませんでした」から進まない。

### 原因
修正前の `src/chainlit_app.py` は、`build_index(SEMANTIC_PATHS)`(レシート+LinkedIn全件を埋め込みベクトル化する重い処理)を `@cl.on_chat_start` の中、つまり**ブラウザが接続してチャットセッションが始まるたび**に呼んでいた。

`build_index` はCPUで同期的に(ブロッキングで)実行される重い処理なので、実行中は Python の `asyncio` イベントループが専有され、他のWebSocket通信を一切さばけなくなる。結果、ブラウザ側は「接続はできたが応答が返ってこない」状態になり、Chainlitのフロントエンドはそれを「サーバーに接続できませんでした」と表示していた。プロセス自体は生きてログも出ているので、外から見ると「動いているのに繋がらない」という分かりにくい状態になっていた。

### 対応
`build_index()` の呼び出しを `@cl.on_chat_start` の中から**モジュールレベル**(ファイルの先頭、サーバーが接続を受け付け始める前)に移動した。これにより、重い処理はサーバー起動シーケンスの一部として1回だけ実行され、チャットセッションごとに繰り返されなくなった。

```python
# モジュールレベルで1プロセスにつき1回だけ構築する
llm = ChatGoogleGenerativeAI(...)
split_docs, vectors = build_index(SEMANTIC_PATHS)
df = load_receipts_as_dataframe(RECEIPT_PATHS)

@cl.on_chat_start
async def start():
    cl.user_session.set("llm", llm)
    cl.user_session.set("split_docs", split_docs)
    ...
```

### 結果
接続そのものが「重い処理が終わるまで受け付けられない」形になったため、「接続はできたのに固まる」という中途半端な状態はなくなった。

---

## 問題2: HuggingFace Hubへの通信が詰まっていた

### 症状
`HEAD https://huggingface.co/api/resolve-cache/...` や `HEAD .../2_Normalize/config.json` のログが延々と出続ける。

### 原因
埋め込みモデル `BAAI/bge-m3` は `~/.cache/huggingface/hub/models--BAAI--bge-m3` に**既にローカルキャッシュ済み**だった。にもかかわらず、`HF_HUB_OFFLINE` が設定されていなかったため、`sentence-transformers`/`huggingface_hub` が起動のたびに「キャッシュが最新か」をHuggingFace Hubに毎回問い合わせに行っていた。この確認自体は普段は一瞬で終わるが、ネットワークが遅い/不安定なタイミングだと起動全体が詰まって見える。

(`2_Normalize/config.json` の404はエラーではなく正常。bge-m3が持っていないオプションモジュールを念のため問い合わせているだけ。)

### 対応
モデルはローカルに揃っているので、オフラインモードを強制:

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
chainlit run src/chainlit_app.py
```

**注意**: `.env` に書いても効かない。`src/rag_pipeline.py` の `load_dotenv()` は `__main__` ブロック内(ファイル末尾)で呼ばれており、`embeddings = HuggingFaceEmbeddings(...)`(モジュール冒頭)より後に実行されるため。シェルの起動プロファイルで `export` するか、`load_dotenv()` をファイル冒頭・embeddings初期化より前に移す必要がある(未対応・today's TODO)。

### 結果
ネットワーク往復をスキップしてキャッシュだけを使うようになり、モデル読み込みが一瞬になった。

---

## なぜ2回目以降の起動がさらに速くなったか — pickleキャッシュの仕組み

`src/rag_pipeline.py` の `build_index()` に、計算済みの `(split_docs, vectors)` をディスクに保存して使い回す仕組みを追加した。

### 何をキャッシュしているか
- `split_docs`: チャンクに分割されたドキュメント本文(`Document`オブジェクトのリスト)。JSON(レシート)は「1レシート=1Document」で既に分割済み、Markdownはヘッダーでさらに分割。
- `vectors`: 各チャンクを埋め込みモデルでベクトル化した数値配列のリスト(`split_docs`と同じ順番・件数で対応)

この2つをタプル `(split_docs, vectors)` として1個のpickleファイルに保存している。キャッシュは**渡された全ファイル(レシート全月分+LinkedIn CSV全部)をまとめて1つ**であり、JSONファイル1個ごとではない。

### キャッシュキー(ハッシュ)の仕組み
`_index_cache_path()` が対象ファイル群の「パス+更新日時+サイズ」を連結してSHA-256ハッシュ化し、`.cache/index_<hash>.pkl` というファイル名にする。データファイルが1つでも変わればハッシュが変わり、**キャッシュ全体が作り直しになる**(部分更新はできない)。

### pickleとは
Pythonの標準機能で、メモリ上のPythonオブジェクト(リストや自作クラスのインスタンスなど)をそのままバイナリファイルに保存し、あとで全く同じ形で読み戻せる仕組み(`pickle.dump` / `pickle.load`)。JSONと違い、`Document`オブジェクトのような複雑な構造もそのまま保存できる。自分のマシンで自分が生成したファイルを読むだけなら安全だが、出所不明のpickleを読み込むのは危険(任意コード実行の恐れ)なので配布・共有はしない。

### 結果
データファイルが変わっていない限り、2回目以降の起動では埋め込み計算(数分)を丸ごとスキップしてpickleを読み込むだけになり、起動が一瞬になった。ポート番号(8000番台かどうか)はこの問題と無関係で、ポートを変えても挙動は変わらない。

---

## まだ理解が浅い/今後の検討点

- **これは本来のDB(ChromaDB/pgvector)の代替にはなっていない**。`docs/requirements.md` / `files/02_PLAN.md` では元々 `Week 1-2: ChromaDB` → `Week 3+: pgvector` への移行が計画されていた。今回のpickleキャッシュは「毎回の再計算をサボる」ための応急処置であり、検索自体は相変わらず全ベクトル総当たり(`src/similarity.py` のcosine類似度をfor文的に比較)。件数が増えたときのインデックス検索や、レシート1件だけの増分更新、複数プロセスからの同時アクセスといった、本来のVector DBが持つ利点はまだ得られていない。
- `.cache/` はデータファイル(レシートJSON・LinkedIn CSV)の変更には追従するが、**埋め込みモデル自体を変えた場合(bge-m3→別モデル等)はキャッシュキーに含まれず、古いベクトルを使い続けてしまう**。モデル変更時は手動で `.cache/` を消す必要がある。
- ~~`HF_HUB_OFFLINE=1` を恒久化する対応(`.env` 読み込み順の修正、または起動プロファイルへの追記)はまだ未実施。~~ **[2026-08-29 解決]** ターミナルへの`export`のみで恒久化しておらず、新しいターミナルセッションで同じ問題が再発した。`.env`に`HF_HUB_OFFLINE=1`/`TRANSFORMERS_OFFLINE=1`を追記し、`src/rag_pipeline.py`の`load_dotenv()`を`embeddings`初期化より前(ファイル冒頭)に移動して、確実に読み込まれるようにした。詳細: [daily/interview-prep/git-branch-pr-merge-workflow.md](../../daily/interview-prep/git-branch-pr-merge-workflow.md)は関係ないが、経緯は本セッションの会話記録を参照。
- **[2026-08-29 追記]** ここで説明しているpickleキャッシュ(`.cache/`, `_index_cache_path`)は、この後ChromaDB移行(`feat/chromadb-migration`)で置き換えられ、現在は存在しない。`build_index()`は代わりにChromaDBの`collection`を返し、永続化もChromaDB自身(`chroma_db/`)が担う。このファイルは当時の設計判断の記録として残す。

## 関連ファイル
- `src/chainlit_app.py` — `build_index()` のモジュールレベル化
- `src/rag_pipeline.py` — pickleキャッシュ(`_index_cache_path`, `build_index(use_cache=True)`)、`embeddings` 初期化、`load_dotenv()` の呼び出し位置
- `src/similarity.py` — 検索時のcosine類似度計算
- `.gitignore` — `.cache/` を追加
