# AI Search Prototype — Postgres + pgvector

A minimal, runnable starter for semantic + hybrid search over location, industry,
and image data. Prototype today on a laptop; the same code scales to a dedicated
vector DB later with only the storage layer swapped.

## What's here

| File | Purpose |
|---|---|
| `schema.sql` | Tables, vector columns, HNSW + geo indexes |
| `embeddings.py` | Text (OpenAI) + image (CLIP) embedding helpers — swap providers here |
| `ingest.py` | Read a CSV, embed rows, insert into Postgres |
| `search.py` | FastAPI hybrid search + text-to-image search endpoints |
| `sample_data.csv` | 5 example records to smoke-test |

## Setup (about 15 minutes)

1. **Postgres with extensions.** Easiest is Docker:
   ```bash
   docker run -d --name pgv -e POSTGRES_DB=search_proto \
     -p 5432:5432 -e POSTGRES_HOST_AUTH_METHOD=trust pgvector/pgvector:pg16
   # postgis: use the `postgis/postgis` image, or `CREATE EXTENSION postgis` if available
   psql postgresql://localhost/search_proto -f schema.sql
   ```

2. **Python deps.**
   ```bash
   pip install "psycopg[binary]" pgvector openai sentence-transformers pillow \
     requests fastapi uvicorn
   export OPENAI_API_KEY=sk-...        # or switch to the local model in embeddings.py
   ```

3. **Ingest + search.**
   ```bash
   python ingest.py sample_data.csv
   uvicorn search:app --reload
   # http://localhost:8000/search?q=coastal%20fabrication%20with%20dock&state=FL
   ```

## Why this scales

- **HNSW indexing** in pgvector handles low-millions of rows well. When you outgrow
  it, move only the vector column to Pinecone / Weaviate / Qdrant — Postgres stays
  the source of truth and the query shape barely changes.
- **Embedding provider is one function.** Swap the hosted API for a self-hosted
  model without touching ingest/search logic. (Change the `VECTOR(n)` dimension in
  `schema.sql` to match the new model.)
- **Hybrid from day one.** Filters and semantic ranking are in the same SQL query,
  so adding a reranker (e.g. Cohere Rerank) later is an app-layer change only.

## Next steps to consider

- Add a reranking pass over the top ~50 vector hits for higher precision.
- Batch-embed during ingestion (send N texts per API call) for large loads.
- Add an LLM step that turns a natural-language query into structured filters
  (state, industry, radius) before the vector search.
