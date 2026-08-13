"""
Hybrid search API. The core idea: hard filters (region, resource) in the SQL
WHERE clause, semantic ranking via the vector distance operator (<=>).

Run:  uvicorn search:app --reload
Then: GET /search?business=coastal fabrication with dock&region=FL&resource=metal
      GET /image_search?q=aerial view of a port
"""
import os
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
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
    summary="Search locations by business, region, and resource",
    description="Embeds `business` and ranks `locations` by semantic similarity, "
                "optionally narrowed first by region/resource filters. `business` is "
                "not a name match — a descriptive query works even if those words "
                "never appear in any business name.",
)
def search(
    business: str = Query(..., description="Free-text description of the kind of business/location you want — embedded and used to rank results semantically (not a name filter).", example="coastal fabrication with dock access"),
    region: str | None = Query(None, description="Case-insensitive exact match on the state/region field.", example="Whyalla"),
    resource: str | None = Query(None, description="Partial match on the industry/resource type.", example="Warehousing"),
    k: int = Query(10, description="Max number of results to return.", ge=1, le=100, example=10),
):
    qvec = embed_text(business)

    where = ["TRUE"]
    params = {"qvec": qvec, "k": k}
    if region:
        where.append("l.state ILIKE %(region)s"); params["region"] = region.strip()
    if resource:
        where.append("l.industry_name ILIKE %(resource)s"); params["resource"] = f"%{resource}%"

    sql = f"""
        SELECT l.id, l.name, l.industry_name, l.state, img.image_url,
               1 - (l.text_embedding <=> %(qvec)s::vector) AS score
        FROM locations l
        LEFT JOIN LATERAL (
            SELECT image_url FROM location_images
            WHERE location_id = l.id LIMIT 1
        ) img ON TRUE
        WHERE {' AND '.join(where)}
        ORDER BY l.text_embedding <=> %(qvec)s::vector   -- cosine distance, nearest first
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
    q: str = Query(..., description="Text description of the image you're looking for.", example="steel factory"),
    k: int = Query(10, description="Max number of results to return.", ge=1, le=100, example=10),
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


# Serves static/index.html at "/" — defined last so it doesn't shadow the
# /search and /image_search API routes above.
app.mount("/", StaticFiles(directory="static", html=True), name="static")
