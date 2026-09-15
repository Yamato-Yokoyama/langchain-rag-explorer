# LangChain RAG Explorer

> Multilingual Personal Knowledge Base with Pragmatic Reasoning
> Built by [Yamato Yokoyama](https://linkedin.com/in/yamato-yokoyama/) · Computational Linguistics BA · University of Tübingen

A multilingual (Japanese / English) RAG system built as both a portfolio project and a study in mapping Semantics & Pragmatics theory (Common Ground, QUD, Speech Acts) onto real RAG / agent architecture — over my own course notes, LinkedIn connections, and monthly living-expense receipts.

**Status:** Actively developed since 2026-08-07. Multi-source ingestion, a 4-way intent router, and a LangGraph state graph with multi-turn (deictic) resolution run end-to-end through a Chainlit chat UI. See [daily notes](daily/) for the build-in-public log, and [Current State](#current-state) below for what's actually working today.

## Why?

See [docs/why.md](docs/why.md) for the full story. Short version: I got frustrated with Gemini/NotebookLM losing context in long sessions, realized this is the same problem discourse pragmatics tries to formalize, and decided to build a system that treats context management as a first-class concern.

## Architecture

| Layer | Technology | Status |
|---|---|---|
| Chat UI | Chainlit | ✅ Done |
| Orchestration | LangChain | ✅ Done |
| State Management | LangGraph (conditional-edge router + checkpointer + multi-turn deixis resolution) | ✅ Done |
| LLM | Google Gemini Flash | ✅ Wired |
| Embeddings | BGE-M3 (sentence-transformers) | ✅ Done |
| Vector Store | ChromaDB (cosine similarity) | ✅ Done |
| Deterministic aggregation | pandas (groupby fallback for arithmetic queries) | ✅ Done |
| Multi-thread / durable session persistence | PostgreSQL or similar | Not started (see [Known Limitations](#known-limitations)) |

## Current State

As of 2026-09-08:

- **Ingestion**: monthly receipt JSON (`src/load_receipts.py`), LinkedIn connections/shares CSV (`src/load_linkedin.py`), and markdown course notes (`src/load_markdown.py`) all load into a shared BGE-M3 / ChromaDB index.
- **Routing**: `src/router.py` classifies each query into one of 4 intents (semantic search / aggregation / table display / LinkedIn table) and dispatches to the matching handler, falling back to deterministic pandas aggregation (`src/aggregations.py`) where the LLM was shown to miscalculate over large result sets (e.g. systematic errors on month-by-month totals once results exceeded top_k).
- **Multi-turn**: `src/graph_router.py` reimplements the router as a LangGraph `StateGraph` with a `MemorySaver` checkpointer, plus a query-rewriting node (`src/query_rewriting.py`) that resolves deictic follow-ups (e.g. "それぞれの役職は?") against conversation history.
- **UI**: `src/chainlit_app.py` wires the whole graph into a Chainlit chat session.

Run it:

```bash
git clone https://github.com/Yamato-Yokoyama/langchain-rag-explorer.git
cd langchain-rag-explorer

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your GEMINI_API_KEY (get one at https://aistudio.google.com/apikey)

PYTHONPATH=. chainlit run src/chainlit_app.py
```

## Theory to Implementation Mapping

This is what the project is really about: using pragmatics theory to diagnose *why* a RAG system fails on a given query, and choosing a fix per failure type instead of one generic fix for everything. Written up in [docs/specialty-positioning.md](docs/specialty-positioning.md) and [docs/rag-direction-and-learning-method.md](docs/rag-direction-and-learning-method.md), with worked examples in [daily/interview-prep/insights.md](daily/interview-prep/insights.md) and [daily/interview-prep/pragmatics-in-rag-query-processing.md](daily/interview-prep/pragmatics-in-rag-query-processing.md).

| Concept (Pragmatics) | Implementation |
|---|---|
| Common Ground | Checkpointer-backed conversation history |
| QUD / deixis resolution | `contextualize_query` node in `src/graph_router.py` |
| Implicature / intent | Query intent classification (`src/router.py`) |
| Felicity Conditions | Metadata pre-filtering before retrieval (`_match_known_companies`, `_match_known_initials`) |
| Speech Act | Dispatch to semantic / aggregation / table-display handlers |

## Known Limitations

Tracked as open issues, not blind spots — several map directly onto semantics/pragmatics problems this project is meant to keep exploring:

- Cross-entity queries ("compare people at company A and company B") — Issue #16
- Multi-thread / long-session history pruning (current checkpointer is in-memory, single-thread) — Issue #22
- Negation / exclusion queries ("everyone except...") — Issue #17
- More general text-to-pandas / text-to-SQL query generation — Issue #19

## Repository Structure

```
langchain-rag-explorer/
├── daily/                     # Daily build-in-public notes + interview-prep write-ups
├── docs/                      # Design notes, theory mapping, LangGraph tutorial
├── data/                      # Personal corpus: receipts JSON, LinkedIn CSV, class notes
├── src/
│   ├── chainlit_app.py        # Chat UI entrypoint
│   ├── graph_router.py        # LangGraph state graph (routing + multi-turn)
│   ├── router.py               # Intent classification + handlers
│   ├── query_rewriting.py     # Deixis resolution / query contextualization
│   ├── aggregations.py        # Deterministic pandas fallback
│   ├── rag_pipeline.py        # Load → Split → Embed → Search
│   └── load_*.py              # Per-source loaders (receipts, LinkedIn, markdown)
├── .env.example
├── requirements.txt
└── README.md
```

## About the Author

Yamato Yokoyama · Computational Linguistics BA (2028) at University of Tübingen · Previously at Temple University Japan (CS) · Former LinkedIn Japan Student Club Ambassador · AI Engineering Intern at MetaMoJi

## License

MIT
