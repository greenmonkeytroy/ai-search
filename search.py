"""
Hybrid search API. The core idea: hard filters (state, resource) in the SQL
WHERE clause, semantic ranking via the vector distance operator (<=>).

Run:  uvicorn search:app --reload
Then: GET /search?business=coastal fabrication with dock&state=FL&resource=metal
      GET /image_search?q=aerial view of a port
"""
import os
from fastapi import FastAPI
import psycopg
from pgvector.psycopg import register_vector
from embeddings import embed_text, embed_text_for_clip

DSN = os.environ.get("DATABASE_URL", "postgresql://postgres@localhost/search_proto")
app = FastAPI()


def _conn():
    conn = psycopg.connect(DSN)
    register_vector(conn)
    return conn


@app.get("/search")
def search(business: str, state: str | None = None, resource: str | None = None, k: int = 10):
    qvec = embed_text(business)

    where = ["name ILIKE %(business)s"]
    params = {"business": f"%{business}%", "qvec": qvec, "k": k}
    if state:
        where.append("state = %(state)s"); params["state"] = state
    if resource:
        where.append("industry_name ILIKE %(resource)s"); params["resource"] = f"%{resource}%"

    sql = f"""
        SELECT id, name, industry_name, state,
               1 - (text_embedding <=> %(qvec)s::vector) AS score
        FROM locations
        WHERE {' AND '.join(where)}
        ORDER BY text_embedding <=> %(qvec)s::vector   -- cosine distance, nearest first
        LIMIT %(k)s
    """
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@app.get("/image_search")
def image_search(q: str, k: int = 10):
    # Embed the text query into CLIP space, then match against image vectors.
    qvec = embed_text_for_clip(q)
    sql = """
        SELECT i.id, i.image_url, l.name,
               1 - (i.image_embedding <=> %(qvec)s::vector) AS score
        FROM location_images i JOIN locations l ON l.id = i.location_id
        ORDER BY i.image_embedding <=> %(qvec)s::vector
        LIMIT %(k)s
    """
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(sql, {"qvec": qvec, "k": k})
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
