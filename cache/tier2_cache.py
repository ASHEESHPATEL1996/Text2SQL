import hashlib
import json
import os

import pandas as pd

from cache.embeddings import EMBEDDING_MODEL, embed_text
from db.db_connection import execute, fetch_df

SEMANTIC_CACHE_ENABLED = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true"
SEMANTIC_SIMILARITY_THRESHOLD = float(os.getenv("SEMANTIC_SIMILARITY_THRESHOLD", "0.82"))


def ensure_cache_table():
    check_sql = """
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'query_cache'
    );
    """

    exists = fetch_df(check_sql).iloc[0, 0]
    if not exists:
        print("query_cache table not found - creating...")
        create_sql = """
        CREATE TABLE query_cache (
            cache_key TEXT PRIMARY KEY,
            question TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            result_json JSONB,
            row_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        execute(create_sql)
        print("query_cache table created")

    ensure_semantic_schema()


def ensure_semantic_schema():
    execute("CREATE EXTENSION IF NOT EXISTS vector;")
    execute(
        """
        ALTER TABLE query_cache
        ADD COLUMN IF NOT EXISTS embedding_model TEXT,
        ADD COLUMN IF NOT EXISTS embedding vector(1536);
        """
    )
    execute(
        """
        CREATE INDEX IF NOT EXISTS query_cache_embedding_hnsw
        ON query_cache
        USING hnsw (embedding vector_cosine_ops);
        """
    )


ensure_cache_table()


def make_key(question: str) -> str:
    return hashlib.sha256(question.strip().lower().encode()).hexdigest()


def _to_vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in values) + "]"


def _load_result(sql: str, result_json):
    if isinstance(result_json, str):
        result_json = json.loads(result_json)
    return sql, pd.DataFrame(result_json)


def _safe_embed(text: str) -> list[float]:
    try:
        return embed_text(text)
    except Exception:
        return []


def get_cached_result(question: str):
    key = make_key(question)
    exact_query = """
    SELECT sql_query, result_json
    FROM query_cache
    WHERE cache_key = :key
    """
    exact_df = fetch_df(exact_query, {"key": key})
    if not exact_df.empty:
        sql = exact_df.iloc[0]["sql_query"]
        result_json = exact_df.iloc[0]["result_json"]
        sql, result_df = _load_result(sql, result_json)
        return sql, result_df, {"type": "exact", "similarity": 1.0}

    if not SEMANTIC_CACHE_ENABLED:
        return None

    query_embedding = _safe_embed(question)
    if not query_embedding:
        return None

    semantic_query = """
    SELECT
        sql_query,
        result_json,
        (1 - (embedding <=> CAST(:query_vec AS vector))) AS similarity
    FROM query_cache
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> CAST(:query_vec AS vector)
    LIMIT 1
    """
    vector_literal = _to_vector_literal(query_embedding)
    semantic_df = fetch_df(semantic_query, {"query_vec": vector_literal})
    if semantic_df.empty:
        return None

    similarity = float(semantic_df.iloc[0]["similarity"])
    if similarity < SEMANTIC_SIMILARITY_THRESHOLD:
        return None

    sql = semantic_df.iloc[0]["sql_query"]
    result_json = semantic_df.iloc[0]["result_json"]
    sql, result_df = _load_result(sql, result_json)
    return sql, result_df, {"type": "semantic", "similarity": round(similarity, 4)}


def save_to_cache(question: str, sql: str, result_df: pd.DataFrame):
    key = make_key(question)
    result_json = result_df.to_dict(orient="records")
    row_count = len(result_df)
    question_embedding = _safe_embed(question) if SEMANTIC_CACHE_ENABLED else []
    vector_literal = _to_vector_literal(question_embedding) if question_embedding else None

    insert = """
    INSERT INTO query_cache
    (cache_key, question, sql_query, result_json, row_count, embedding_model, embedding)
    VALUES (
        :key,
        :question,
        :sql,
        CAST(:result AS JSONB),
        :count,
        :embedding_model,
        CASE WHEN :embedding IS NULL THEN NULL ELSE CAST(:embedding AS vector) END
    )
    ON CONFLICT (cache_key)
    DO UPDATE SET
        question = EXCLUDED.question,
        sql_query = EXCLUDED.sql_query,
        result_json = EXCLUDED.result_json,
        row_count = EXCLUDED.row_count,
        embedding_model = EXCLUDED.embedding_model,
        embedding = EXCLUDED.embedding
    """
    execute(
        insert,
        {
            "key": key,
            "question": question,
            "sql": sql,
            "result": json.dumps(result_json),
            "count": row_count,
            "embedding_model": EMBEDDING_MODEL if vector_literal else None,
            "embedding": vector_literal,
        },
    )
