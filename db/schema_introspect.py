from db.db_connection import fetch_df


def quote_identifier(identifier: str) -> str:
    """Safely quote PostgreSQL identifiers such as table names."""
    return '"' + identifier.replace('"', '""') + '"'


def get_schema_text() -> str:
    """
    Returns a human-readable schema description
    for use in LLM prompts.
    """
    tables_query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
    """

    tables_df = fetch_df(tables_query)

    if tables_df.empty:
        return "No tables found in database."

    schema_lines = []

    for table in tables_df["table_name"]:
        cols_query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = :table
        ORDER BY ordinal_position;
        """
        cols_df = fetch_df(cols_query, {"table": table})

        columns = [
            f"{row['column_name']} ({row['data_type']})"
            for _, row in cols_df.iterrows()
        ]

        quoted_table = quote_identifier(table)
        count_query = f"SELECT COUNT(*) AS cnt FROM {quoted_table};"
        count_df = fetch_df(count_query)

        row_count = int(count_df.iloc[0]["cnt"])

        schema_lines.append(
            f"Table: {table} - {row_count} rows\n"
            f"Columns: {', '.join(columns)}"
        )

    return "\n\n".join(schema_lines)


if __name__ == "__main__":
    schema = get_schema_text()

    print("\nDatabase Schema:\n")
    print(schema)
