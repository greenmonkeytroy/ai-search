# Local dev Postgres with both pgvector and postgis.
# pgvector/pgvector:pg16 ships pgvector precompiled; postgis isn't included,
# so add it from the same pgdg apt repo the base image already uses.
FROM pgvector/pgvector:pg16

RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-16-postgis-3 \
    && rm -rf /var/lib/apt/lists/*
