from db.db_connection import fetch_df
from llm.text_to_sql import generate_sql

def answer_question(question: str):

    sql = generate_sql(question)

    try:
        df = fetch_df(sql)
    except Exception as e:
        raise RuntimeError(f"SQL execution failed: {e}")

    return sql, df


if __name__ == "__main__":

    q = "Show all customers who are from alabama"

    sql, result = answer_question(q)

    print("\nGenerated SQL:\n")
    print(sql)

    print("\nQuery Result:\n")
    print(result)