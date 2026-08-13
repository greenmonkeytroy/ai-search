"""
Embedding helpers. Swap these two functions to change providers — nothing
else in the prototype needs to change.

Default: local sentence-transformers for text, CLIP (also sentence-
transformers) for images. Hosted OpenAI alternative is noted inline.
"""
from functools import lru_cache

# ---- TEXT: local sentence-transformers model (no API key, no GPU needed) --
# pip install sentence-transformers
from sentence_transformers import SentenceTransformer

_txt = SentenceTransformer("all-MiniLM-L6-v2")  # 384 dims — matches schema.sql


def embed_text(text: str) -> list[float]:
    return _txt.encode(text).tolist()


# Hosted alternative: OpenAI text-embedding-3-small (1536 dims, needs
# OPENAI_API_KEY). Set text_embedding VECTOR(1536) in schema.sql to use it.
# from openai import OpenAI
# _openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
# def embed_text(text):
#     return _openai.embeddings.create(model="text-embedding-3-small", input=text).data[0].embedding


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
