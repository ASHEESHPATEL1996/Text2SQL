from db.db_connection import fetch_df
from llm.text_to_sql import generate_sql

from cache.tier1_cache import get_l1, set_l1
from cache.tier2_cache import get_cached_result, save_to_cache
from cache.cache_metrics import (
    record_l1_hit,
    record_l2_hit,
    record_miss,
    get_metrics,
    hit_rate
)

from observability.langfuse_client import langfuse
import time


def answer_question(question: str):

    # Start end-to-end root span (Langfuse v3 API)
    trace = langfuse.start_span(
        name="text-to-sql-request",
        input={"question": question}
    )

    start_time = time.time()

    l1 = get_l1(question)

    if l1:
        record_l1_hit()
        sql, df = l1

        trace.update(
            metadata={
                "cache_source": "L1",
                "rows_returned": len(df)
            },
            output={"sql": sql}
        )

        trace.end()
        langfuse.flush()
        return sql, df, "L1-cache", None

    l2 = get_cached_result(question)

    if l2:
        record_l2_hit()
        sql, df = l2

        # Promote to L1
        set_l1(question, sql, df)

        trace.update(
            metadata={
                "cache_source": "L2",
                "promoted_to_L1": True,
                "rows_returned": len(df)
            },
            output={"sql": sql}
        )

        trace.end()
        langfuse.flush()
        return sql, df, "L2-cache", None


    record_miss()

    trace.update(metadata={"cache_source": "LLM"})

    # SQL generation already tracked in text_to_sql.py
    sql, usage = generate_sql(question)

    exec_span = trace.span(name="sql-execution")

    try:
        df = fetch_df(sql)

        execution_time = time.time() - start_time

        exec_span.update(
            output={
                "rows_returned": len(df),
                "execution_time_sec": execution_time
            }
        )
        exec_span.end()

    except Exception as e:

        exec_span.update(
            output={"error": str(e)}
        )
        exec_span.end()

        trace.update(level="ERROR")
        trace.end()
        langfuse.flush()

        raise RuntimeError(f"SQL execution failed: {e}")

    save_to_cache(question, sql, df)  # L2 persistent
    set_l1(question, sql, df)         # L1 memory

    trace.update(
        metadata={
            "rows_returned": len(df),
            "execution_time_sec": execution_time,
            "saved_to_cache": True
        },
        output={"sql": sql}
    )

    trace.end()
    langfuse.flush()

    return sql, df, "LLM", usage

if __name__ == "__main__":

    questions = [
        "Show all customers who are from alabama",
        "Show all customers who are from alabama",
        "List all customers",
        "Show all customers who are from alabama"
    ]

    for q in questions:
        sql, result, source = answer_question(q)

        print("\nSource:", source)
        print("Rows:", len(result))

    print("\n📊 Cache Metrics:")
    print(get_metrics())
    print("Hit Rate:", round(hit_rate() * 100, 2), "%")
