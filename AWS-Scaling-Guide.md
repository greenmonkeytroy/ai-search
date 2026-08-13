# Scaling the Search Prototype on AWS

The prototype (Postgres + pgvector, a FastAPI service, and CSV/image files) moves
to AWS without an architecture change. Each local piece has a managed AWS
equivalent; you keep the same schema, queries, and code, and repoint the
connection string.

## Where Claude fits: build-time only

Claude is a **developer tool, not a runtime component.** Claude Code (VS Code
extension) is used to write and iterate on the schema, ingestion/search code,
Dockerfile, and AWS infrastructure config — on your laptop. The **deployed system
contains no Claude and no chat LLM.** A query comes in, is turned into an
embedding, and Postgres returns ranked matches — that is the entire runtime path.

Consequences for the AWS footprint:

- **No Bedrock-for-Claude and no LLM inference service to run.** The only "AI" at
  runtime is the embedding call, which is lightweight.
- Claude touches AWS only through your own hands (AWS CLI / CDK while building) —
  it is never a service you provision or pay for in the deployment.
- The "RAG answers" and "runtime LLM" options are **out of scope** for this build.

## Service mapping

| Prototype piece | AWS service | Notes |
|---|---|---|
| Docker Postgres + pgvector | **RDS for PostgreSQL** (or Aurora PostgreSQL) | pgvector supported; same `schema.sql` |
| `uvicorn` FastAPI on laptop | **ECS Fargate** (or Lambda) | Containers, no servers to manage |
| Local image files | **S3** | DB stores the S3 URL + vector, not the image |
| OpenAI / CLIP embedding calls | External API, or **Bedrock** for embeddings only | Bedrock keeps data in-account; no Claude/LLM at runtime |
| Building the code & infra | **Claude Code in VS Code** (dev laptop) | Build-time only — not deployed to AWS |

## Database: RDS vs. Aurora

Start on **RDS PostgreSQL** — simpler and cheaper, and it runs pgvector directly.
Move to **Aurora PostgreSQL** only when you need auto-scaling storage, faster
failover, or read replicas to spread search traffic. Both use the identical
schema and queries, so the switch is a later decision, not an upfront one.

pgvector on RDS/Aurora comfortably handles into the **low millions of vectors**
with HNSW indexing. Beyond that (tens of millions or very high query volume),
move only the vector column to **Amazon OpenSearch Service (k-NN)** or a
third-party store like Pinecone, and keep RDS as the system of record.

## Migration path (same code throughout)

1. **Provision RDS PostgreSQL**, then enable pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```
2. **Apply the schema:** `psql <rds-endpoint> -f schema.sql`
3. **Move images to S3** and store the S3 URL in `location_images.image_url`.
4. **Re-run ingestion** against the new endpoint: update the DSN in `ingest.py`
   / `search.py` to the RDS connection string, then `python ingest.py ...`.
5. **Containerize** the FastAPI service and deploy to **ECS Fargate** behind an
   Application Load Balancer.
6. (Optional) **Switch embeddings to Bedrock** if data must stay in-account —
   change only the two functions in `embeddings.py`.

## Reference deployment

```
             Internet
                |
        Application Load Balancer
                |
        ECS Fargate  ── FastAPI (search.py) ── Embedding API / Bedrock (embeddings only)
                |
        RDS PostgreSQL + pgvector  ── S3 (image files)

   (Build-time only, not deployed: Claude Code in VS Code on the dev laptop)
```

Put RDS in a **private subnet** (not publicly reachable); Fargate talks to it
over the VPC. Store the DB credentials in **Secrets Manager** and inject them
into the container, rather than hardcoding the DSN.

## Cost drivers (check current AWS pricing before committing)

- **RDS/Aurora** — driven mainly by instance size and allocated storage; a small
  instance is enough for early production. Add read replicas only when query
  volume needs them.
- **Embeddings** — priced per token (text) or per image. Ingesting the existing
  repository is a **one-time bulk cost**; ongoing cost is just per query.
- **S3** — cheap storage + request costs; negligible next to compute.
- **Fargate** — priced by vCPU/memory per running task; scale task count with
  traffic.

## Security & residency

- **Bedrock** (embeddings only) keeps embedding generation inside the AWS
  account — the natural choice if the client has data-residency requirements.
  No chat LLM runs at runtime regardless.
- Enable **encryption at rest** (RDS + S3) and **in transit** (TLS to RDS).
- Use **IAM roles** for the Fargate task to reach S3/Bedrock/Secrets Manager —
  no static keys in the app.
```
