# ANN(Approximate Nearest Neighbor)・HNSW・ChromaDB/pgvectorの構造

> 明日(2026-08-28)のChromaDB導入の前に見返す用。「ANNはArtificial Neural Networkではない」「Neighborと言われてもピンと来ない」への図解。
> 関連: [when-vector-db-becomes-necessary.md](when-vector-db-becomes-necessary.md)

---

## 0. まず「Neighbor(近傍)」という言葉の感覚をつかむ

BGE-M3で埋め込んだ各chunkは、1024次元空間の中の**1つの点**。「意味が近い文章 = 空間の中で近くにある点」という前提がRAGの土台(これ自体は既に何週間も前提にしている)。

**Nearest Neighbor検索 = 「クエリという点から見て、一番近くにある点(たち)を探す」**、それだけ。現実の「近所さん(neighbor)」と同じ言葉を使っているのは、比喩ではなく文字通り「空間的に近い」という意味だから。

```mermaid
graph TD
    Q(("クエリベクトル<br/>(質問を埋め込んだ点)"))
    Q --- D1["doc1"]
    Q --- D2["doc2"]
    Q --- D3["doc3(一番近い neighbor)"]
    Q --- D4["doc4"]
    Q --- D5["doc5"]
    Q --- DN["...doc4000(全件)"]

    style D3 fill:#4a9,stroke:#333
```

上の図が**素朴な総当たり(ブルートフォース)検索**。クエリが**全ドキュメントと1個ずつ距離を測っている**、これが今`src/similarity.py`でやっていること。4,000件なら一瞬だが、これが数百万件になると「全員に声をかけて回る」ようなもので、遅くなる。

## 1. HNSWは「全員に聞く」代わりに「知り合いを辿る」

HNSW = **H**ierarchical **N**avigable **S**mall **W**orld。3つの単語がそれぞれ役割を持つ。

```mermaid
flowchart TD
    subgraph L2["Layer 2(最上層 = 高速道路。ノードが少なく、長距離の繋がりのみ)"]
        A2((A)) --- C2((C))
    end
    subgraph L1["Layer 1(中間層。もう少しノードが増える)"]
        A1((A)) --- D1((D))
        D1 --- C1((C))
    end
    subgraph L0["Layer 0(最下層 = 一般道。全ノードが存在、密な繋がり)"]
        A0((A)) --- B0((B))
        B0 --- D0((D))
        D0 --- F0((F))
        F0 --- C0((C))
        C0 --- E0((E))
    end

    Start(["検索スタート地点<br/>(固定のエントリーポイント)"]) --> A2
    A2 -->|"このLayerでクエリに一番近いのはC"| C2
    C2 -.1つ下の層へ降りる.-> C1
    C1 -->|"このLayerで最寄りを再探索"| D1
    D1 -.また1つ下へ.-> D0
    D0 -->|"最下層でさらに細かく最寄りを探す"| F0
    F0 --> Result(["近似最近傍として返す"])
```

- **Hierarchical(階層的)**: 上の層ほどノードが少なく「高速道路」的な長距離ジャンプができる。下の層に行くほどノードが増え「一般道」的に密になる
- **Navigable(たどれる)**: 今いるノードから「クエリに一番近い隣のノードへ」を繰り返すだけ(greedy)で、迷わず目的地に近づける
- **Small World(スモールワールド)**: 少ないホップ数でどのノードにも辿り着けるグラフの性質(六次の隔たりと同じ発想)。この性質のおかげでgreedyな移動が機能する

**流れ**: 上の層(高速道路)で大まかな方向に飛ぶ → 1つ下の層に降りる → その層でまた最寄りへ移動 → さらに下へ…という「大まかに絞ってから細かく絞る」の繰り返し。全件と比較する必要がないので、数百万件でも高速。「近似的」なのは、greedyな移動が本当の最近傍を見逃す可能性があるから(それでも実用上十分な精度が出ることが多い)。

## 2. ChromaDB vs pgvector: 構造の違い

```mermaid
flowchart LR
    subgraph Chroma["ChromaDB構成"]
        App1["アプリ<br/>(このプロジェクト)"] --> CDB[("ChromaDB<br/>ベクトル専用<br/>プロセス内 or 別サーバー")]
        CDB --> HNSW1["内部でHNSWインデックスを保持"]
    end

    subgraph PG["pgvector構成"]
        App2["アプリ"] --> PGDB[("PostgreSQL")]
        PGDB --> T1["既存テーブル<br/>(users, sessions等)"]
        PGDB --> T2["vector型カラム<br/>(pgvector拡張が追加)"]
        T2 --> HNSW2["同じくHNSW等の<br/>インデックスをPostgres内に保持"]
    end
```

**同じ点**: どちらも内部でHNSW相当のANNインデックスを使い、「近似最近傍検索」という核の機能は同じ。

**違う点**: ChromaDBは**ベクトル検索専用に切り出されたシステム**。pgvectorは**PostgreSQLという汎用DBに追加された拡張機能**で、既存のテーブル(構造化データ)と同じDBの中でベクトル検索も行える。「どちらが優れているか」ではなく、「単体のツールを1つ足すか、既に使っているDBに機能を足すか」という構成の違い。

## 3. 明日、このプロジェクトで何が変わるか

```mermaid
flowchart LR
    subgraph Now["現在(2026-08-27時点)"]
        A1["build_index()"] --> B1["Pythonリスト<br/>+ .cache/*.pkl"]
        B1 --> C1["search():<br/>総当たりでcosine類似度計算"]
        C1 --> D1["_match_known_companies():<br/>手作りのcompany文字列一致フィルタ"]
    end

    subgraph Tomorrow["明日導入する形"]
        A2["build_index()"] --> B2["ChromaDBの<br/>collection"]
        B2 --> C2["search():<br/>collection.query()<br/>(内部はHNSW)"]
        C2 --> D2["where={'company': ...}<br/>ChromaDBネイティブのメタデータフィルタ"]
    end

    Now -.関数シグネチャは変えずに中身だけ差し替え.-> Tomorrow
```

**やることの本質**: `build_index()`と`search()`という「入口」は変えず、中身の実装だけを「Pythonリストの総当たり」から「ChromaDBのHNSWインデックス」に差し替える。今日手作りした`_match_known_companies`は、ChromaDBの`where`フィルタに置き換えて比較する。これが今日話した「後から差し替えやすい設計にしていたから、今この移行が低コストでできる」の実地確認になる。

---

## まとめ(1文ずつ)

- **Nearest Neighbor** = 埋め込み空間の中で「クエリに近い点」を探すこと、文字通りの意味
- **ANN(この文脈)** = Approximate Nearest Neighbor、近似的に高速でNearest Neighborを探すアルゴリズム。Artificial Neural Networkとは別物
- **HNSW** = 階層構造(高速道路→一般道)を使って、全件比較せずgreedyに近傍へたどり着く具体的なANN手法
- **ChromaDB** = HNSW等を内部で使う、ベクトル検索専用のスタンドアロンなシステム
- **pgvector** = 同じくHNSW等を使うが、PostgreSQLの拡張として既存の構造化データと同居する
