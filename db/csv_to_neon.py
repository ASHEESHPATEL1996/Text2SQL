import os
import re
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

NEON_DB_URL = os.getenv("NEON_DB")  # recommended

if not NEON_DB_URL:
    raise ValueError("Please set NEON_DB_URL environment variable")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_FOLDER = os.path.join(BASE_DIR, "data_dump")

engine = create_engine(NEON_DB_URL)


def clean_name(name: str) -> str:
    """Make safe SQL table/column names"""
    cleaned = re.sub(r"[^a-z0-9_]+", "_", name.lower().strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")

    if not cleaned:
        return "unnamed"

    if cleaned[0].isdigit():
        return f"t_{cleaned}"

    return cleaned


def upload_all_csv():

    if not os.path.exists(DATA_FOLDER):
        raise FileNotFoundError(f"Folder not found: {DATA_FOLDER}")

    files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".csv")]

    if not files:
        raise ValueError("No CSV files found in data_dump")

    print(f"Found {len(files)} CSV files\n")

    for file in files:

        path = os.path.join(DATA_FOLDER, file)

        table_name = clean_name(os.path.splitext(file)[0])

        print(f"Uploading {file} table `{table_name}`")

        df = pd.read_csv(path)

        # Clean column names
        df.columns = [clean_name(col) for col in df.columns]

        df.to_sql(
            table_name,
            engine,
            if_exists="replace",   # change to "append" if needed
            index=False,
            method="multi"
        )

        print(f"{len(df)} rows uploaded")

    print("All CSV files successfully uploaded to Neon!")


if __name__ == "__main__":
    upload_all_csv()
