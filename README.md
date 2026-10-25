# AI Ticket Raising System

Streamlit UI + Flask backend + ChromaDB (RAG over company docs) + SQLite storage,
powered by Gemini for classification, sentiment, priority, summarization, and
response generation.

## Folder Structure

```
ticket-system/
├── knowledge_base/              # Company docs embedded into ChromaDB (once)
│   ├── billing_policy.md
│   ├── refund_policy.md
│   ├── subscription_policy.md
│   ├── premium_plan.md
│   ├── technical_support.md
│   └── account_security.md
│
├── backend/
│   ├── config.py                 # Env vars, paths, constants
│   ├── db.py                     # SQLite schema + CRUD
│   ├── vector_store.py           # ChromaDB client + retrieval
│   ├── ingest.py                 # ONE-TIME script: embed knowledge_base/*.md
│   ├── llm_service.py            # Gemini calls (classify/sentiment/priority/summary/response)
│   └── app.py                    # Flask API (raise ticket, list tickets, pending queue)
│
├── frontend/
│   └── streamlit_app.py          # "Raise Your Ticket" UI + pending tickets list
│
├── data/                          # Created automatically at runtime
│   ├── tickets.db                 # SQLite database (git-ignored)
│   └── chroma_store/              # ChromaDB persistent vector store (git-ignored)
│
├── .env                           # Your real secrets (git-ignored)
├── .env.example                   # Template to copy to .env
├── .gitignore
├── requirements.txt
└── README.md
```

## 1. Setup

```bash
cd ticket-system
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Copy the env template and add your Gemini API key (from
https://aistudio.google.com/apikey):

```bash
cp .env.example .env
# then edit .env and set GEMINI_API_KEY=...
```

## 2. Embed the knowledge base (run ONCE)

This reads every `.md` file in `knowledge_base/`, splits it into chunks, and
embeds it into a local persistent ChromaDB collection in `data/chroma_store/`.
Re-run it any time you add/edit a knowledge base file (it's idempotent —
existing chunk IDs are upserted, not duplicated).

```bash
cd backend
python ingest.py
```

## 3. Run the backend

```bash
cd backend
python app.py
```

The Flask API will be available at `http://127.0.0.1:5000`. It automatically
creates `data/tickets.db` (SQLite) with the `tickets` table on first run.

## 4. Run the frontend

In a second terminal:

```bash
cd frontend
streamlit run streamlit_app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`).

## How a ticket is processed

1. Customer submits **Subject** + **Description** in the Streamlit UI.
2. Flask embeds the query and retrieves the top-matching chunks from the
   ChromaDB knowledge base (RAG).
3. A single Gemini call classifies the ticket:
   - **Category**: Billing / Technical / Account / Subscription / Security / Other
   - **Sentiment**: Positive / Neutral / Negative
   - **Priority**: Low / Medium / High / Critical
   - **Summary**: one-line summary
   - **needs_human_review**: true/false
   - **ai_response**: a suggested reply grounded in the retrieved docs
4. If `needs_human_review` is true, the customer sees:
   > "Our support team will contact you soon."
   and the ticket appears in the **Pending Tickets** list at the bottom of the UI.
5. If AI can confidently resolve it, the customer sees the AI-generated response directly.
6. Every ticket (subject, description, category, sentiment, priority, summary,
   response, review flag) is stored in SQLite (`data/tickets.db`).

## Notes

- `GEMINI_MODEL` defaults to `gemini-3.5-flash` in `.env` — change it there if
  you want to point at a different Gemini model.
- Document embeddings use ChromaDB's built-in local embedding model (MiniLM),
  so ingestion doesn't consume any Gemini API quota — only ticket analysis calls do.
- To reset everything, delete `data/tickets.db` and `data/chroma_store/`, then
  re-run `python ingest.py`.
