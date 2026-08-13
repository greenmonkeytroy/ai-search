"""
Hybrid search API. The core idea: hard filters (state, industry, radius) in the
SQL WHERE clause, semantic ranking via the vector distance operator (<=>).

Run:  uvicorn search:app --reload
Then: GET /search?q=coastal manufacturing site&state=FL&radius_km=50&lon=-81.6&lat=30.3
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
def search(q: str, state: str | None = None, industry_code: str | None = None,
           lon: float | None = None, lat: float | None = None,
           radius_km: float | None = None, k: int = 10):
    qvec = embed_text(q)

    where, params = ["TRUE"], {"qvec": qvec, "k": k}
    if state:
        where.append("state = %(state)s"); params["state"] = state
    if industry_code:
        where.append("industry_code = %(ind)s"); params["ind"] = industry_code
    if lon is not None and lat is not None and radius_km is not None:
        where.append("ST_DWithin(geom, ST_MakePoint(%(lon)s, %(lat)s)::geography, %(rad)s)")
        params.update(lon=lon, lat=lat, rad=radius_km * 1000)

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
