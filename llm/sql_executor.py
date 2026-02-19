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


def answer_question(question: str):


    l1 = get_l1(question)

    if l1:
        record_l1_hit()
        sql, df = l1
        return sql, df, "L1-cache"

    l2 = get_cached_result(question)

    if l2:
        record_l2_hit()
        sql, df = l2

        # Promote to L1
        set_l1(question, sql, df)

        return sql, df, "L2-cache"


    record_miss()

    sql = generate_sql(question)

    try:
        df = fetch_df(sql)
    except Exception as e:
        raise RuntimeError(f"SQL execution failed: {e}")

    save_to_cache(question, sql, df)  # L2 persistent
    set_l1(question, sql, df)         # L1 memory

    return sql, df, "LLM"

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
