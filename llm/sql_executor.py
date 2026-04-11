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

    with langfuse.start_as_current_observation(
        name="text-to-sql-request",
        as_type="span",
        input={"question": question},
    ) as trace:

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

            langfuse.flush()
            return sql, df, "L1-cache", None

        l2 = get_cached_result(question)

        if l2:
            sql, df, cache_meta = l2
            hit_type = cache_meta.get("type", "exact")
            similarity = cache_meta.get("similarity")
            record_l2_hit("semantic" if hit_type == "semantic" else "exact")

            set_l1(question, sql, df)

            trace.update(
                metadata={
                    "cache_source": f"L2-{hit_type}",
                    "promoted_to_L1": True,
                    "rows_returned": len(df),
                    "similarity": similarity
                },
                output={"sql": sql}
            )

            langfuse.flush()
            if hit_type == "semantic":
                return sql, df, "L2-semantic-cache", None
            return sql, df, "L2-cache", None

        record_miss()

        trace.update(metadata={"cache_source": "LLM"})

        sql, usage = generate_sql(question)

        with trace.start_as_current_observation(
            name="sql-execution",
            as_type="span",
        ) as exec_span:

            try:
                df = fetch_df(sql)

                execution_time = time.time() - start_time

                exec_span.update(
                    output={
                        "rows_returned": len(df),
                        "execution_time_sec": execution_time
                    }
                )

            except Exception as e:

                exec_span.update(
                    output={"error": str(e)}
                )

                trace.update(level="ERROR")
                langfuse.flush()

                raise RuntimeError(f"SQL execution failed: {e}") from e

        save_to_cache(question, sql, df)
        set_l1(question, sql, df)

        trace.update(
            metadata={
                "rows_returned": len(df),
                "execution_time_sec": execution_time,
                "saved_to_cache": True
            },
            output={"sql": sql}
        )

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
        sql, result, source, usage = answer_question(q)

        print("\nSource:", source)
        print("Rows:", len(result))

    print("\n Cache Metrics:")
    print(get_metrics())
    print("Hit Rate:", round(hit_rate() * 100, 2), "%")
