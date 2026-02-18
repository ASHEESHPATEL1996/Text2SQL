import os
import pandas as pd
from sqlalchemy import create_engine

from dotenv import load_dotenv

load_dotenv()

NEON_DB_URL = os.getenv("NEON_DB")

if not NEON_DB_URL:
    raise ValueError("NEON_DB_URL not found")

engine = create_engine(NEON_DB_URL)

# 🔹 List tables
tables = pd.read_sql("""
SELECT table_name
FROM information_schema.tables
WHERE table_schema='public'
""", engine)

print("Tables:")
print(tables)