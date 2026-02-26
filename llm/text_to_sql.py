import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
import streamlit as st

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from db.schema_introspect import get_schema_text

try:
    from langchain_community.callbacks.manager import get_openai_callback
except ImportError:
    # Fallback if langchain_community is not available
    from contextlib import contextmanager
    @contextmanager
    def get_openai_callback():
        class CB:
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            total_cost = 0.0
        yield CB()



load_dotenv()

# Import langfuse from observability module (which handles fallback)
from observability.langfuse_client import langfuse

def get_secret(key: str):
    """Works locally (.env) and on Streamlit Cloud."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


OPENAI_API_KEY = get_secret("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found")

print("OpenAI API Key loaded successfully")


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)


_SCHEMA = None


def get_schema_cached():
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = get_schema_text()
    return _SCHEMA


def refresh_schema():
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

    if "```" in sql:
        parts = sql.split("```")
        for p in parts:
            if "SELECT" in p.upper():
                sql = p.strip()
                break

    prefixes = ["sql", "SQL", "Query:", "SQL Query:"]
    for p in prefixes:
        if sql.lower().startswith(p.lower()):
            sql = sql[len(p):].strip()

    return sql


FORBIDDEN = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]


def validate_sql(sql: str) -> bool:

    upper = sql.upper().strip()

    if not upper.startswith("SELECT"):
        return False

    if any(word in upper for word in FORBIDDEN):
        return False

    return True


def generate_sql(question: str):

    schema = get_schema_cached()

    # Start ROOT TRACE (not span)
    trace = langfuse.start_trace(
        name="text-to-sql",
        input={"question": question}
    )

    # Generation created from TRACE
    generation = trace.start_generation(
        name="sql-generation",
        model="gpt-4o-mini",
        input={
            "question": question,
            "schema_preview": schema[:2000]
        }
    )

    try:

        # Capture token usage
        with get_openai_callback() as cb:

            response = chain.invoke({
                "schema": schema,
                "question": question
            })

            raw_output = response.content
            sql = clean_sql(raw_output)

            if not validate_sql(sql):
                raise ValueError(f"Unsafe SQL generated:\n{raw_output}")

            # Token usage metrics
            usage = {
                "prompt_tokens": cb.prompt_tokens,
                "completion_tokens": cb.completion_tokens,
                "total_tokens": cb.total_tokens,
                "cost_usd": cb.total_cost
            }

        # Log success
        generation.update(
            output={"sql": sql},
            metadata=usage
        )
        generation.end()

        trace.update(
            output={"sql": sql},
            metadata={"success": True}
        )

        return sql, usage

    except Exception as e:

        # Log error to Langfuse
        generation.update(
            output={"error": str(e)},
            level="ERROR",
            status_message=str(e)
        )
        generation.end()
        trace.update(
            output={"error": str(e)},
            level="ERROR",
            status_message=str(e)
        )

        raise

    finally:
        trace.end()
        # Ensure logs are sent immediately
        langfuse.flush()


if __name__ == "__main__":

    q = "Show all customers who are from alabama"
    print("Question:\n", q)

    sql = generate_sql(q)

    print("\nClean SQL Output:\n")
    print(sql)
