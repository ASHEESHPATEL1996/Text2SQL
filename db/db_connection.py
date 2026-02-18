import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv


load_dotenv()

NEON_DB_URL = os.getenv("NEON_DB")

if not NEON_DB_URL:
    raise ValueError("NEON_DB_URL not found in environment")


engine = create_engine(
    NEON_DB_URL,
    pool_pre_ping=True,    # handles stale connections
    pool_size=5,
    max_overflow=10
)

def fetch_df(sql: str, params: dict = None):

    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn, params=params)

    return df

def execute(sql: str, params: dict = None):

    with engine.begin() as conn:
        conn.execute(text(sql), params or {})


def fetch_scalar(sql: str, params: dict = None):

    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {}).scalar()

    return result

def test_connection():

    try:
        val = fetch_scalar("SELECT 1")
        return val == 1
    except Exception:
        return False


if __name__ == "__main__":

    if test_connection():
        print("Neon connection successful")
    else:
        print("Connection failed")
