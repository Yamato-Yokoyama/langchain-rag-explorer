# LangChain RAG Explorer

> Multilingual Personal Knowledge Base with Pragmatic Reasoning
> Built by [Yamato Yokoyama](https://linkedin.com/in/yamato-yokoyama/) · Computational Linguistics BA · University of Tübingen

A multilingual (Japanese / English) RAG assistant over my own data (LinkedIn connections, personal expense receipts, linguistics class notes), built as both a working tool and a study in mapping Semantics & Pragmatics theory (Speech Acts, Common Ground, Gricean maxims) onto real RAG / agent failure modes.

**Status:** Actively developed since 2026-08-07. Core RAG + LangGraph router + multi-agent verification + MCP tooling are implemented and running. See [Notable Findings](#notable-findings-the-debugging-journey) below.

**Roadmap:** v1 closes this personal-data RAG once retrieval is measured (#42 nDCG@10) and the README is current; negation (#17) and CI (#38) move to v2. v2 rebuilds the assistant on the Amazon ESCI Japanese product data as a conversational shopping assistant. See [docs/roadmap.md](docs/roadmap.md).

## Why?

See [docs/why.md](docs/why.md) for the full story. Short version: I got frustrated with Gemini/NotebookLM losing context in long sessions, realized this is the same problem discourse pragmatics tries to formalize, and decided to build a system that treats context management as a first-class concern.

## Architecture

| Layer | Technology | Status |
|---|---|---|
| Chat UI | Chainlit | ✅ |
| Orchestration | LangChain + LangGraph (router → verification agent) | ✅ |
| State Management | LangGraph checkpointer (SQLite, persists across restarts) | ✅ |
| LLM | Google Gemini Flash | ✅ |
| Embeddings | BGE-M3 (sentence-transformers) | ✅ |
| Vector Store | ChromaDB | ✅ |
| Tooling | MCP server (receipt PDF → structured JSON) | ✅ |
| CI | GitHub Actions (pytest + pip-audit) | ✅ |
| Orchestration (containers) | Docker / Kubernetes | 📋 planned, see [Issue #41](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/41) |

## What it does

Ask it things like:

- *"Who are the SAP people I've connected with recently, and what are their roles?"* → routes to a structured LinkedIn query
- *"What did I spend on groceries in September?"* → routes to a deterministic pandas aggregation (not LLM arithmetic, see below)
- *"What's the Q-principle?"* → routes to semantic search over class notes, answer is checked by a second agent before being returned
- Multi-turn: *"...and what about M.S.?"* resolves the pronoun against conversation history (LangGraph checkpointer, survives process restarts)

Query routing (`src/graph_router.py`) is a LangGraph state machine: `contextualize → router → {semantic, aggregation, table_display, linkedin_table} → [critic, semantic only] → record_history`.

## Multi-agent verification (critic node)

The semantic-search branch adds a second, independently-prompted LLM call that checks whether the generated answer is actually supported by the retrieved evidence, rather than trusting the first answer at face value. It doesn't know "the truth" (no agent does) — it only checks *groundedness*: does the answer match what was retrieved. See [docs/notes/multi-agent-101-tutorial/](docs/notes/multi-agent-101-tutorial/).

It has already caught a real bug in my own data: two different LinkedIn contacts sharing the same initials had been silently merged into one answer.

## MCP tool: receipt automation

`src/receipt_mcp_server.py` exposes an `extract_receipt` tool (via the Model Context Protocol) that turns a manual task — reading a receipt PDF and typing the line items into JSON by hand — into something any MCP-compatible client can call directly. See [docs/notes/mcp-101-tutorial/](docs/notes/mcp-101-tutorial/).

## Notable findings (the debugging journey)

This project is as much about *why RAG fails* as about making it work. A few findings that came from treating retrieval failures as things to diagnose, not just patch:

- **Speech Act mismatch in retrieval**: the query "Q-principleって何?" ranked the Q-principle chunk 5th instead of 1st (score 0.3833 vs 0.4510 for the top chunk). The chunk is not long (275 chars, shorter than the top three), so the better explanation is that the embedding matched the question's form more than its content. Rewriting the query into a definition-style statement (`expand_query_to_definition`) moved it to 2nd to 4th place over four runs, but never 1st, because the rewriter kept guessing the wrong field for the term (quantum physics, business). Re-measured on 2026-10-05. Earlier notes called this "Chunk Size dilution"; the chunk length does not support that.
- **Chainlit + asyncio**: building the vector index inside `@cl.on_chat_start` blocked the event loop for every other connection.
- **LLM arithmetic is unreliable at scale**: expense totals computed by the LLM directly were off by real money at `top_k=171`; replaced with deterministic pandas aggregation, LLM only picks which function to call. See [src/aggregations.py](src/aggregations.py).
- **Vision extraction errors**: the MCP receipt tool sends each PDF to the Gemini API, and the model misread a price (2x the correct value on one line item). The tool itself has no automatic check yet. The error was caught by comparing the extracted items with the receipt total in a separate review step before saving, not by trusting the model. An automatic `sum(items) == total` check is planned (see docs/notes/mcp-101-tutorial/01_why_and_what.md).
- **`pip-audit` found 39 known vulnerabilities** across 4 dependencies the first time it was run in CI — a reminder that a clean test suite says nothing about dependency security.

## ML side-track: Speech Act classification baseline

Independent of the RAG pipeline, `src/ml/` has a from-scratch Naive Bayes / Logistic Regression baseline for Speech Act classification (DailyDialog, TF-IDF features, Macro F1 0.539 → 0.700). Not yet wired into the router — see [Issue #39](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/39) (closed) and [docs/experiments.md](docs/experiments.md) for the results and how it connects back to the Speech Act mismatch finding above.

## Quick Start

```bash
git clone https://github.com/Yamato-Yokoyama/langchain-rag-explorer.git
cd langchain-rag-explorer

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your GEMINI_API_KEY (get one at https://aistudio.google.com/apikey)

chainlit run src/chainlit_app.py
```

Running the test suite / dependency scan locally (same as CI):

```bash
pytest src/embedding_quality_test.py -v
pip install pip-audit && pip-audit -r requirements.txt
```

## Repository Structure

```
langchain-rag-explorer/
├── docs/
│   ├── data-flow/           # How each loader turns raw data into Documents
│   ├── notes/               # 101-style tutorials (LangGraph, GitHub Actions, MCP, multi-agent)
│   ├── why.md
│   └── requirements.md
├── src/
│   ├── chainlit_app.py       # Chat UI entry point
│   ├── graph_router.py       # LangGraph state machine (router + critic)
│   ├── router.py             # Intent routing + branch handlers
│   ├── rag_pipeline.py       # Embedding/search/generation
│   ├── receipt_mcp_server.py # MCP tool for receipt PDF → JSON
│   ├── aggregations.py       # Deterministic pandas aggregations
│   └── ml/                   # Speech Act classification (independent side-track)
├── .github/workflows/ci.yml  # pytest + pip-audit
├── notebooks/
├── requirements.txt
└── README.md
```

## Known Limitations / Open Work

- No Kubernetes/container deployment yet ([Issue #41](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/41))
- No quantitative retrieval evaluation harness yet — current findings are real but individually diagnosed, not benchmarked at scale ([Issue #42](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues/42))
- Speech Act classifier (`src/ml/`) is trained but not yet wired into query routing
- Negation/exclusion queries, multi-entity relationship queries, and long-conversation history pruning are known gaps (see [open issues](https://github.com/Yamato-Yokoyama/langchain-rag-explorer/issues))
- `pip-audit` currently reports 39 known dependency vulnerabilities (`continue-on-error: true` in CI, not yet triaged/upgraded)

## About the Author

Yamato Yokoyama · Computational Linguistics BA (2028) at University of Tübingen · Previously at Temple University Japan (CS) · Former LinkedIn Japan Student Club Ambassador · AI Engineering Intern at MetaMoJi

## License

MIT
