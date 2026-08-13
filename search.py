"""
Hybrid search API. The core idea: hard filters (state, resource) in the SQL
WHERE clause, semantic ranking via the vector distance operator (<=>).

Run:  uvicorn search:app --reload
Then: GET /search?business=coastal fabrication with dock&state=FL&resource=metal
      GET /image_search?q=aerial view of a port
"""
import os
from fastapi import FastAPI, Query
import psycopg
from pgvector.psycopg import register_vector
from embeddings import embed_text, embed_text_for_clip

DSN = os.environ.get("DATABASE_URL", "postgresql://postgres@localhost/search_proto")
app = FastAPI(
    title="AI Search Prototype",
    description="Hybrid semantic + filtered search over location/industry/image data (Postgres + pgvector).",
)


def _conn():
    conn = psycopg.connect(DSN)
    register_vector(conn)
    return conn


@app.get(
    "/search",
    summary="Search locations by business, state, and resource",
    description="Filters `locations` by business name and (optionally) state/resource, "
                "then ranks matches by semantic similarity between `business` and each "
                "record's embedded description.",
)
def search(
    business: str = Query(..., description="Business/location name (partial match) — also embedded and used to rank results semantically.", examples=["Steelworks"]),
    state: str | None = Query(None, description="Exact match on the state/region field.", examples=["Whyalla"]),
    resource: str | None = Query(None, description="Partial match on the industry/resource type.", examples=["Warehousing"]),
    k: int = Query(10, description="Max number of results to return.", ge=1, le=100),
):
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


@app.get(
    "/image_search",
    summary="Search location images by text description",
    description="Embeds the query text into CLIP space and ranks `location_images` "
                "by similarity, so a text description can match photos directly.",
)
def image_search(
    q: str = Query(..., description="Text description of the image you're looking for.", examples=["steel factory"]),
    k: int = Query(10, description="Max number of results to return.", ge=1, le=100),
):
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
