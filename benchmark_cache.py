import argparse
import os
import sys
import time
from statistics import mean, median

sys.path.append(os.path.dirname(__file__))

from cache.cache_metrics import get_metrics, reset_metrics
from cache.tier1_cache import clear_l1
from llm.sql_executor import answer_question


def run_query(question: str, force_l2: bool = False):
    if force_l2:
        clear_l1()

    start = time.perf_counter()
    sql, df, source, usage = answer_question(question)
    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "question": question,
        "source": source,
        "elapsed_ms": elapsed_ms,
        "rows": len(df),
        "usage": usage,
        "sql": sql,
    }


def summarize(main_runs, l2_runs):
    total = len(main_runs)
    misses = [r for r in main_runs if r["source"] == "LLM"]
    hits = [r for r in main_runs if r["source"] != "LLM"]
    repeat_runs = main_runs[1:] if len(main_runs) > 1 else []

    total_llm_cost = sum((r["usage"] or {}).get("cost_usd", 0.0) for r in main_runs)
    miss_costs = [(r["usage"] or {}).get("cost_usd", 0.0) for r in misses]
    avg_miss_cost = mean(miss_costs) if miss_costs else None
    est_no_cache_cost = (avg_miss_cost * total) if avg_miss_cost is not None else None
    est_saved_pct = None
    if est_no_cache_cost and est_no_cache_cost > 0:
        est_saved_pct = (1 - (total_llm_cost / est_no_cache_cost)) * 100

    repeat_under_100 = [
        r for r in repeat_runs if r["elapsed_ms"] < 100 and r["source"] != "LLM"
    ]

    print("\n=== Main Runs (natural cache behavior) ===")
    for i, r in enumerate(main_runs, start=1):
        print(
            f"Run {i:02d}: source={r['source']:<8} latency={r['elapsed_ms']:.2f} ms "
            f"rows={r['rows']}"
        )

    if l2_runs:
        print("\n=== Forced L2 Runs (L1 cleared before each run) ===")
        for i, r in enumerate(l2_runs, start=1):
            print(
                f"L2 {i:02d}: source={r['source']:<8} latency={r['elapsed_ms']:.2f} ms "
                f"rows={r['rows']}"
            )

    print("\n=== Summary ===")
    print(f"Total requests: {total}")
    print(f"LLM misses: {len(misses)}")
    print(f"Cache hits: {len(hits)}")
    print(f"Cache hit ratio: {(len(hits) / total * 100) if total else 0:.2f}%")

    if repeat_runs:
        repeat_lat = [r["elapsed_ms"] for r in repeat_runs]
        print(f"Repeat-query median latency: {median(repeat_lat):.2f} ms")
        print(f"Repeat-query avg latency: {mean(repeat_lat):.2f} ms")
        print(
            f"Repeat cached runs under 100 ms: "
            f"{len(repeat_under_100)}/{len(repeat_runs)} "
            f"({(len(repeat_under_100) / len(repeat_runs) * 100):.2f}%)"
        )

    if l2_runs:
        l2_lat = [r["elapsed_ms"] for r in l2_runs]
        print(f"Forced-L2 median latency: {median(l2_lat):.2f} ms")
        print(f"Forced-L2 avg latency: {mean(l2_lat):.2f} ms")

    print(f"Actual LLM cost (USD): ${total_llm_cost:.6f}")
    if est_no_cache_cost is not None:
        print(f"Estimated no-cache cost (USD): ${est_no_cache_cost:.6f}")
    if est_saved_pct is not None:
        print(f"Estimated cost saved by cache: {est_saved_pct:.2f}%")
    else:
        print("Estimated cost saved by cache: n/a (no LLM misses observed)")

    print("\nCache metrics snapshot:", get_metrics())


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Text-to-SQL latency and cache-driven cost savings."
    )
    parser.add_argument(
        "--question",
        default="Show all customers who are from Alabama",
        help="Natural-language query to benchmark.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of sequential runs (first is usually cold, rest warm).",
    )
    parser.add_argument(
        "--force-l2-runs",
        type=int,
        default=3,
        help="Extra runs with L1 cleared each time to observe L2 latency.",
    )
    args = parser.parse_args()

    reset_metrics()
    clear_l1()

    main_runs = [run_query(args.question) for _ in range(args.runs)]
    l2_runs = [run_query(args.question, force_l2=True) for _ in range(args.force_l2_runs)]

    summarize(main_runs, l2_runs)


if __name__ == "__main__":
    main()
