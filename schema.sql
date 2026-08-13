-- Prototype schema for AI-powered location + industry + image search
-- Postgres 14+ with the pgvector and postgis extensions.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;

-- One row per location record. Structured columns live alongside the
-- embedding, so hybrid queries (filters + semantic search) are plain SQL.
CREATE TABLE IF NOT EXISTS locations (
    id            BIGSERIAL PRIMARY KEY,
    name          TEXT        NOT NULL,
    description   TEXT,                       -- free text used for the text embedding
    industry_code TEXT,                       -- e.g. NAICS
    industry_name TEXT,
    state         TEXT,
    geom          GEOGRAPHY(Point, 4326),     -- lon/lat for radius queries via PostGIS
    created_at    TIMESTAMPTZ DEFAULT now(),

    -- Text embedding. Dimension MUST match your model:
    --   OpenAI text-embedding-3-small = 1536
    --   Voyage voyage-3               = 1024
    --   sentence-transformers all-MiniLM-L6-v2 = 384
    text_embedding  VECTOR(1536)
);

-- One row per image, linked to a location. Kept in its own table because a
-- location can have many images, and image vectors use a different model.
CREATE TABLE IF NOT EXISTS location_images (
    id           BIGSERIAL PRIMARY KEY,
    location_id  BIGINT REFERENCES locations(id) ON DELETE CASCADE,
    image_url    TEXT NOT NULL,
    -- CLIP ViT-B/32 = 512 dims. Text and image CLIP vectors share this space,
    -- so a text query can be matched directly against image_embedding.
    image_embedding VECTOR(512)
);

-- Approximate-nearest-neighbor indexes. HNSW gives good recall + speed and
-- scales into the low millions of rows before you need a dedicated vector DB.
CREATE INDEX IF NOT EXISTS idx_locations_text_emb
    ON locations USING hnsw (text_embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_images_emb
    ON location_images USING hnsw (image_embedding vector_cosine_ops);

-- B-tree / GiST indexes for the hard filters that run alongside semantic search.
CREATE INDEX IF NOT EXISTS idx_locations_industry ON locations (industry_code);
CREATE INDEX IF NOT EXISTS idx_locations_state    ON locations (state);
CREATE INDEX IF NOT EXISTS idx_locations_geom     ON locations USING gist (geom);
