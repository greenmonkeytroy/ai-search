"""
Ingestion: read records from a CSV, embed them, upsert into Postgres.

CSV columns expected (image_url optional):
    name, description, industry_code, industry_name, state, lon, lat, image_url

Run:  python ingest.py sample_data.csv
"""
import csv
import os
import sys
import psycopg
from pgvector.psycopg import register_vector
from embeddings import embed_text, embed_image

DSN = os.environ.get("DATABASE_URL", "postgresql://postgres@localhost/search_proto")


def ingest(csv_path: str):
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        with conn.cursor() as cur, open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                text = f"{row['name']}. {row.get('description', '')} " \
                       f"Industry: {row.get('industry_name', '')}."
                tvec = embed_text(text)

                cur.execute(
                    """
                    INSERT INTO locations
                        (name, description, industry_code, industry_name,
                         state, geom, text_embedding)
                    VALUES (%s, %s, %s, %s, %s,
                            ST_MakePoint(%s, %s)::geography, %s)
                    RETURNING id
                    """,
                    (row["name"], row.get("description"), row.get("industry_code"),
                     row.get("industry_name"), row.get("state"),
                     float(row["lon"]), float(row["lat"]), tvec),
                )
                loc_id = cur.fetchone()[0]

                url = row.get("image_url")
                if url:
                    cur.execute(
                        "INSERT INTO location_images (location_id, image_url, image_embedding) "
                        "VALUES (%s, %s, %s)",
                        (loc_id, url, embed_image(url)),
                    )
                print(f"ingested #{loc_id}: {row['name']}")
        conn.commit()


if __name__ == "__main__":
    ingest(sys.argv[1] if len(sys.argv) > 1 else "sample_data.csv")
