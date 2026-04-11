import os

from openai import OpenAI


EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def embed_text(text: str) -> list[float]:
    value = (text or "").strip()
    if not value:
        return []

    client = _get_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=value)
    return response.data[0].embedding
