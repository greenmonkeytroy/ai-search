"""
Embedding helpers. Swap these two functions to change providers — nothing
else in the prototype needs to change.

Default: OpenAI for text, CLIP (via sentence-transformers) for images.
Fully-local alternative is noted inline.
"""
import os
from functools import lru_cache

# ---- TEXT: OpenAI (hosted API, no GPU needed) -----------------------------
# pip install openai
from openai import OpenAI

_openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
TEXT_MODEL = "text-embedding-3-small"  # 1536 dims — matches schema.sql


def embed_text(text: str) -> list[float]:
    resp = _openai.embeddings.create(model=TEXT_MODEL, input=text)
    return resp.data[0].embedding


# Fully-local text alternative (no API key). Set text_embedding VECTOR(384).
# from sentence_transformers import SentenceTransformer
# _txt = SentenceTransformer("all-MiniLM-L6-v2")
# def embed_text(text): return _txt.encode(text).tolist()


# ---- IMAGES: CLIP, shared text+image space (runs locally on CPU) ----------
# pip install sentence-transformers pillow
from sentence_transformers import SentenceTransformer
from PIL import Image
import requests
from io import BytesIO


@lru_cache(maxsize=1)
def _clip():
    return SentenceTransformer("clip-ViT-B-32")  # 512 dims — matches schema.sql


def embed_image(image_url: str) -> list[float]:
    img = Image.open(BytesIO(requests.get(image_url, timeout=30).content))
    return _clip().encode(img).tolist()


def embed_text_for_clip(text: str) -> list[float]:
    """Embed a TEXT query into CLIP space so it can be matched vs. images."""
    return _clip().encode(text).tolist()
