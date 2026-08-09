# LangChain RAG Explorer

> Multilingual Personal Knowledge Base with Pragmatic Reasoning
> Built by [Yamato Yokoyama](https://linkedin.com/in/yamato-yokoyama/) · Computational Linguistics BA · University of Tübingen

A multilingual (Japanese / English, German later) RAG system built as both a portfolio project and a study in mapping Semantics & Pragmatics theory (Common Ground, QUD, Speech Acts) onto real RAG / agent architecture.

**Status:** Week 1 in progress (2026-08-07 → 2026-09-03). See [daily notes](daily/) for build-in-public log.

## Why?

See [docs/why.md](docs/why.md) for the full story. Short version: I got frustrated with Gemini/NotebookLM losing context in long sessions, realized this is the same problem discourse pragmatics tries to formalize, and decided to build a system that treats context management as a first-class concern.

## Planned Architecture

| Layer | Technology | Status |
|---|---|---|
| Chat UI | Chainlit | Week 2 |
| Orchestration | LangChain | ✅ Basic (Week 1) |
| State Management | LangGraph | Week 3 |
| LLM | Google Gemini Flash | ✅ Wired (Week 1) |
| Embeddings | BGE-M3 (sentence-transformers) | Week 2 |
| Vector Store | ChromaDB → pgvector | Week 2 / Week 3 |
| Persistence | PostgreSQL + SQLAlchemy + Alembic | Week 3 |

## Current State (as of 2026-08-09)

- Raw Gemini SDK Hello World (`src/hello_gemini.py`)
- LangChain equivalent (`src/hello_langchain.py`)
- Manual conversation loop with history (`src/chat_manual.py`)
- LangChain conversation loop with `SystemMessage` (`src/chat_langchain.py`)
- Thought Summary experimentation (see [daily/2026-08-09.md](daily/2026-08-09.md))

## Theory to Implementation Mapping (Week 4)

This is what the project is really about. See `docs/theory-mapping.md` (Week 4).

| Concept (Pragmatics) | Implementation |
|---|---|
| Common Ground | Session Store + Vector DB |
| Context Set | Retrieved candidates |
| QUD Stack | LangGraph state machine |
| Implicature | Query intent classification |
| Felicity Conditions | Tool use pre-conditions |
| Speech Act | Function calling |

## Quick Start (Week 1 minimum)

```bash
git clone https://github.com/Yamato-Yokoyama/langchain-rag-explorer.git
cd langchain-rag-explorer

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your GEMINI_API_KEY (get one at https://aistudio.google.com/apikey)

python src/hello_langchain.py
python src/chat_langchain.py
```

## Repository Structure

langchain-rag-explorer/
├── daily/ # Daily build-in-public notes
├── docs/ # Public project documentation
│ ├── why.md
│ └── requirements.md
├── src/ # Implementation
│ ├── hello_gemini.py
│ ├── hello_langchain.py
│ ├── chat_manual.py
│ └── chat_langchain.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md


## Weekly Roadmap

- Week 1 (8/7 – 8/13): Foundation — Gemini SDK, LangChain basics, single-doc RAG
- Week 2 (8/14 – 8/20): Documents & Multilingual — LinkedIn CSV ingestion, Chainlit UI, BGE-M3 + ChromaDB
- Week 3 (8/21 – 8/27): State & Session — LangGraph, PostgreSQL migration, hierarchical history
- Week 4 (8/28 – 9/3): Theory Mapping & Ship — pragmatics-to-implementation docs, portfolio prep, SAP application

## About the Author

Yamato Yokoyama · Computational Linguistics BA (2028) at University of Tübingen · Previously at Temple University Japan (CS) · Former LinkedIn Japan Student Club Ambassador · AI Engineering Intern at MetaMoJi

## License

MIT