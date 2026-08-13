# Container image for the FastAPI search service (search.py).
# Deploys to ECS Fargate per the AWS scaling guide.
FROM python:3.12-slim

# System deps for psycopg + pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY embeddings.py ingest.py search.py ./

EXPOSE 8000

# DATABASE_URL and OPENAI_API_KEY are injected at runtime (env / Secrets Manager),
# never baked into the image.
CMD ["uvicorn", "search:app", "--host", "0.0.0.0", "--port", "8000"]
