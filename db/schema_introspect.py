import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

NEON_DB_URL = os.getenv("NEON_DB")

if not NEON_DB_URL:
    raise ValueError("NEON_DB_URL not found")

engine = create_engine(NEON_DB_URL)

def fetch_schema():

    query = text("""
    SELECT
        table_name,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position
    """)

    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

    schema = {}

    for table, col, dtype in rows:
        schema.setdefault(table, []).append((col, dtype))

    return schema


def get_row_counts(schema):

    counts = {}

    with engine.connect() as conn:
        for table in schema.keys():

            try:
                count = conn.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).scalar()

            except Exception:
                count = "unknown"

            counts[table] = count

    return counts


def format_schema(schema, counts):

    lines = []

    for table, columns in schema.items():

        row_info = counts.get(table, "unknown")

        lines.append(f"Table: {table} (rows: {row_info})")

        for col, dtype in columns:
            lines.append(f"  - {col} ({dtype})")

        lines.append("")

    return "\n".join(lines)


def get_schema_text():

    schema = fetch_schema()
    counts = get_row_counts(schema)

    formatted = format_schema(schema, counts)

    return formatted


if __name__ == "__main__":
    print(get_schema_text())
