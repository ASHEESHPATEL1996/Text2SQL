import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from db.schema_introspect import get_schema_text


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found")

print("OpenAI API Key loaded successfully")

llm = ChatOpenAI(
    model="gpt-4.1-mini",   # cheap + reliable
    temperature=0           # deterministic output
)


_SCHEMA = None


def get_schema_cached():
    """Fetch schema once and cache in memory."""
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = get_schema_text()
    return _SCHEMA


def refresh_schema():
    """Manually refresh schema (if DB structure changes)."""
    global _SCHEMA
    _SCHEMA = get_schema_text()
print("Database schema loaded and cached in memory")

prompt = ChatPromptTemplate.from_template(
    """
You are a PostgreSQL expert.

Convert the natural language question into a SQL query.

DATABASE SCHEMA:
{schema}

STRICT RULES:
- Only SELECT queries
- Prefer a single table
- Avoid JOINs unless absolutely necessary
- Use subqueries only when needed
- No window functions unless required
- Use CTEs only if necessary
- No aggregation unless required
- Use only existing tables and columns
- Keep query short and readable
- Return ONLY raw SQL
- No markdown
- No explanations
- Output must start with SELECT

QUESTION:
{question}
"""
)

chain = prompt | llm



def clean_sql(output: str) -> str:
    sql = output.strip()

    # Remove markdown blocks
    if "```" in sql:
        parts = sql.split("```")
        for p in parts:
            if "SELECT" in p.upper():
                sql = p.strip()
                break

    # Remove common prefixes
    prefixes = ["sql", "SQL", "Query:", "SQL Query:"]
    for p in prefixes:
        if sql.lower().startswith(p.lower()):
            sql = sql[len(p):].strip()

    return sql



FORBIDDEN = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]


def validate_sql(sql: str) -> bool:

    upper = sql.upper().strip()

    # Must be SELECT
    if not upper.startswith("SELECT"):
        return False

    # Block destructive operations
    if any(word in upper for word in FORBIDDEN):
        return False

    return True



def generate_sql(question: str):

    schema = get_schema_cached()

    response = chain.invoke({
        "schema": schema,
        "question": question
    })

    raw_output = response.content
    sql = clean_sql(raw_output)

    if not validate_sql(sql):
        raise ValueError(f"Unsafe SQL generated:\n{raw_output}")

    return sql


if __name__ == "__main__":

    q = "Show all customers who are from alabama"
    print("Question:\n", q)

    sql = generate_sql(q)

    print("\nClean SQL Output:\n")
    print(sql)
