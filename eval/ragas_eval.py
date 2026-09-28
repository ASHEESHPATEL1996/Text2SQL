"""
RAGAS-based evaluation for the Text2SQL pipeline.

Standard RAGAS metrics (Faithfulness, Context Precision/Recall) are built for
prose RAG answers and don't decompose SQL text meaningfully, so this script
uses two AspectCritic (LLM-as-judge) metrics tailored to Text2SQL:

  - schema_groundedness: does the generated SQL only reference tables/columns
    that actually exist in the schema (catches hallucinated identifiers)?
  - answer_correctness:  is the generated SQL semantically equivalent to the
    reference SQL for the given question?

Alongside the LLM judges, this script also computes execution accuracy:
run both the generated SQL and the reference SQL against the live database
and compare the resulting rows (order-independent).

Usage:
    .venv/Scripts/python.exe eval/ragas_eval.py
    .venv/Scripts/python.exe eval/ragas_eval.py --dataset eval/golden_dataset.jsonl --limit 10
"""

import argparse
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from dotenv import load_dotenv

from ragas import SingleTurnSample, EvaluationDataset, evaluate
from ragas.metrics import AspectCritic
from ragas.llms import LangchainLLMWrapper
from langchain_openai import ChatOpenAI

from db.db_connection import fetch_df
from db.schema_introspect import get_schema_text
from llm.text_to_sql import generate_sql

load_dotenv()

EVAL_DIR = Path(__file__).resolve().parent
RESULTS_DIR = EVAL_DIR / "results"

JUDGE_MODEL = "gpt-4.1-mini"

GROUNDEDNESS_DEFINITION = (
    "Given the database schema in the context and the SQL query in the response, "
    "return 1 if the SQL query ONLY references tables and columns that exist in the "
    "schema and is syntactically plausible PostgreSQL. Return 0 if it references any "
    "table or column not present in the schema, or is not valid SQL."
)

CORRECTNESS_DEFINITION = (
    "Given the natural language question in the user input and a reference SQL query "
    "in the reference field, judge whether the SQL query in the response would return "
    "the same result set as the reference SQL for that question. Return 1 if they are "
    "semantically equivalent (same intent, same result set), return 0 otherwise. Minor "
    "differences in column order or aliasing do not count against equivalence."
)


def load_dataset(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_rows(df: pd.DataFrame) -> list[tuple]:
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_float_dtype(df[col]):
            df[col] = df[col].round(4)
    rows = [tuple(str(v) for v in row) for row in df.itertuples(index=False, name=None)]
    return sorted(rows)


def execution_match(ref_df: pd.DataFrame | None, gen_df: pd.DataFrame | None) -> bool:
    if ref_df is None or gen_df is None:
        return False
    if ref_df.shape != gen_df.shape:
        return False
    return normalize_rows(ref_df) == normalize_rows(gen_df)


def run_generation(rows: list[dict], schema_text: str) -> list[dict]:
    records = []

    for row in rows:
        question = row["question"]
        reference_sql = row["reference_sql"]

        record = {
            "id": row.get("id"),
            "question": question,
            "reference_sql": reference_sql,
            "category": row.get("category"),
        }

        try:
            generated_sql, usage = generate_sql(question)
            record["generated_sql"] = generated_sql
            record["generation_error"] = None
        except Exception as e:
            record["generated_sql"] = None
            record["generation_error"] = str(e)
            records.append(record)
            continue

        try:
            ref_df = fetch_df(reference_sql)
            record["reference_rows"] = len(ref_df)
        except Exception as e:
            ref_df = None
            record["reference_rows"] = None
            record["reference_exec_error"] = str(e)

        try:
            gen_df = fetch_df(generated_sql)
            record["generated_rows"] = len(gen_df)
            record["generated_exec_error"] = None
        except Exception as e:
            gen_df = None
            record["generated_rows"] = None
            record["generated_exec_error"] = str(e)

        record["execution_match"] = execution_match(ref_df, gen_df)
        records.append(record)

    return records


def run_ragas_judges(records: list[dict], schema_text: str) -> pd.DataFrame:
    judge_llm = LangchainLLMWrapper(ChatOpenAI(model=JUDGE_MODEL, temperature=0))

    groundedness = AspectCritic(
        name="schema_groundedness",
        definition=GROUNDEDNESS_DEFINITION,
        llm=judge_llm,
    )
    correctness = AspectCritic(
        name="answer_correctness",
        definition=CORRECTNESS_DEFINITION,
        llm=judge_llm,
    )

    judged = [r for r in records if r.get("generated_sql")]

    samples = [
        SingleTurnSample(
            user_input=r["question"],
            response=r["generated_sql"],
            reference=r["reference_sql"],
            retrieved_contexts=[schema_text],
        )
        for r in judged
    ]

    if not samples:
        return pd.DataFrame()

    dataset = EvaluationDataset(samples=samples)
    result = evaluate(dataset=dataset, metrics=[groundedness, correctness])
    scores = result.to_pandas()[["schema_groundedness", "answer_correctness"]]

    for r, (_, s) in zip(judged, scores.iterrows()):
        r["schema_groundedness"] = s["schema_groundedness"]
        r["answer_correctness"] = s["answer_correctness"]

    return pd.DataFrame(records)


def summarize(df: pd.DataFrame) -> None:
    total = len(df)
    generated_ok = df["generated_sql"].notna().sum()

    print(f"\n{'=' * 60}")
    print("RAGAS Text2SQL Evaluation Summary")
    print(f"{'=' * 60}")
    print(f"Total questions:        {total}")
    print(f"SQL generated:          {generated_ok}/{total}")

    if "execution_match" in df.columns:
        exec_acc = df["execution_match"].fillna(False).mean()
        print(f"Execution accuracy:     {exec_acc * 100:.1f}%")

    if "schema_groundedness" in df.columns:
        print(f"Schema groundedness:    {df['schema_groundedness'].mean() * 100:.1f}%")

    if "answer_correctness" in df.columns:
        print(f"Answer correctness:     {df['answer_correctness'].mean() * 100:.1f}%")

    print(f"{'=' * 60}\n")

    failures = df[df["execution_match"] != True]  # noqa: E712
    if not failures.empty:
        print("Failing / mismatched cases:")
        cols = [c for c in ["id", "question", "execution_match", "answer_correctness"] if c in failures.columns]
        print(failures[cols].to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation over the golden Text2SQL dataset.")
    parser.add_argument("--dataset", default=str(EVAL_DIR / "golden_dataset.jsonl"))
    parser.add_argument("--limit", type=int, default=None, help="Only evaluate the first N questions.")
    parser.add_argument("--out", default=None, help="Path to write results CSV.")
    args = parser.parse_args()

    rows = load_dataset(Path(args.dataset))
    if args.limit:
        rows = rows[: args.limit]

    print(f"Loaded {len(rows)} golden questions from {args.dataset}")

    schema_text = get_schema_text()

    print("Generating SQL for each question...")
    records = run_generation(rows, schema_text)

    print("Scoring with RAGAS AspectCritic judges...")
    df = run_ragas_judges(records, schema_text)

    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = Path(args.out) if args.out else RESULTS_DIR / f"eval_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.csv"
    df.to_csv(out_path, index=False)
    print(f"Results written to {out_path}")

    summarize(df)


if __name__ == "__main__":
    main()
