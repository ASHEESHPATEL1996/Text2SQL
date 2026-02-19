import hashlib
import json

import pandas as pd

from db.db_connection import execute, fetch_df


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


ensure_cache_table()


def make_key(question: str) -> str:
    return hashlib.sha256(question.strip().lower().encode()).hexdigest()


def get_cached_result(question: str):
    key = make_key(question)

    query = """
    SELECT sql_query, result_json
    FROM query_cache
    WHERE cache_key = :key
    """

    df = fetch_df(query, {"key": key})

    if df.empty:
        return None

    sql = df.iloc[0]["sql_query"]
    result_json = df.iloc[0]["result_json"]

    if isinstance(result_json, str):
        result_json = json.loads(result_json)

    result_df = pd.DataFrame(result_json)

    return sql, result_df


def save_to_cache(question: str, sql: str, result_df: pd.DataFrame):
    key = make_key(question)

    result_json = result_df.to_dict(orient="records")
    row_count = len(result_df)

    insert = """
    INSERT INTO query_cache
    (cache_key, question, sql_query, result_json, row_count)
    VALUES (:key, :question, :sql, CAST(:result AS JSONB), :count)
    ON CONFLICT (cache_key) DO NOTHING
    """

    execute(
        insert,
        {
            "key": key,
            "question": question,
            "sql": sql,
            "result": json.dumps(result_json),
            "count": row_count,
        },
    )
