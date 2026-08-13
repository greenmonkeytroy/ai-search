# AI Search Prototype — Postgres + pgvector

A minimal, runnable starter for semantic + hybrid search over location, industry,
and image data. Prototype today on a laptop; the same code scales to a dedicated
vector DB later with only the storage layer swapped.

## What's here

| File | Purpose |
|---|---|
| `schema.sql` | Tables, vector columns, HNSW + geo indexes |
| `embeddings.py` | Text (local sentence-transformers) + image (CLIP) embedding helpers — swap providers here |
| `ingest.py` | Read a CSV, embed rows, insert into Postgres |
| `search.py` | FastAPI hybrid search + text-to-image search endpoints |
| `sample_data.csv` | 5 example records to smoke-test |
| `postgres.Dockerfile` | Local dev Postgres image with pgvector + postgis |

## Setup (about 15 minutes)

1. **Postgres with extensions.** `schema.sql` needs both pgvector and postgis,
   and no single official image ships both — `postgres.Dockerfile` builds one
   from `pgvector/pgvector:pg16` plus the postgis apt package. The container's
   default role is `postgres` (trust auth, no password), which is what
   `DATABASE_URL` below assumes. Applying the schema doesn't require a `psql`
   client on the host — pipe it into the container instead:
   ```bash
   docker build -t pgv-postgis -f postgres.Dockerfile .
   docker run -d --name pgv -e POSTGRES_DB=search_proto \
     -p 5432:5432 -e POSTGRES_HOST_AUTH_METHOD=trust pgv-postgis
   docker exec -i pgv psql -U postgres -d search_proto < schema.sql
   ```

2. **Python deps.**
   ```bash
   pip install -r requirements.txt
   ```
   The default text embedding model (`all-MiniLM-L6-v2`, in `embeddings.py`)
   runs locally — no API key needed. Only set `OPENAI_API_KEY` if you switch
   to the commented-out OpenAI alternative (and update `VECTOR(n)` in
   `schema.sql` to match its dimension).

3. **Ingest + search.**
   ```bash
   export DATABASE_URL=postgresql://postgres@localhost/search_proto
   python ingest.py sample_data.csv
   uvicorn search:app --reload
   # http://localhost:8000/search?business=fabrication&region=Whyalla&resource=metal
   ```
   `/search` takes three filters: `business` (required — matched against the
   name and used to rank results semantically), `region`, and `resource`
   (matched against industry). `k` controls result count (default 10).

## Why this scales

- **HNSW indexing** in pgvector handles low-millions of rows well. When you outgrow
  it, move only the vector column to Pinecone / Weaviate / Qdrant — Postgres stays
  the source of truth and the query shape barely changes.
- **Embedding provider is one function.** Swap the local model for a hosted API
  (or vice versa) without touching ingest/search logic. (Change the `VECTOR(n)`
  dimension in `schema.sql` to match the new model.)
- **Hybrid from day one.** Filters and semantic ranking are in the same SQL query,
  so adding a reranker (e.g. Cohere Rerank) later is an app-layer change only.

## Version control & push

This folder is a git repository (`main` branch) with an initial commit already
made. The `origin` remote points at:

    https://github.com/greenmonkeytroy/ai-search.git

To push from your own machine (VS Code terminal, in this folder):

```bash
git push -u origin main       # first push; sets main to track origin
# VS Code will use your GitHub login, or prompt to authorize
```

After pushing, future changes are just:

```bash
git add -A
git commit -m "your message"
git push
```

### Verify the push worked
1. Refresh the GitHub repo page — you should see all 15 files.
2. Confirm `.env` is NOT listed on GitHub (only `.env.example`). It is
   git-ignored; never commit real secrets.
3. Confirm there is no `node_modules/` on GitHub.

## Next steps to consider

- Add a reranking pass over the top ~50 vector hits for higher precision.
- Batch-embed during ingestion (send N texts per API call) for large loads.
- Add an LLM step that turns a natural-language query into structured filters
  (state, industry, radius) before the vector search.
