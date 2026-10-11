"""
Run every query in sql/ against the clean data with DuckDB and save the results.

DuckDB runs standard analytical SQL (CTEs, window functions) directly on the
CSV files, so no database server is needed. The same queries run on
Snowflake, BigQuery or Postgres with small syntax changes.

Run:  python src/run_sql.py
Out:  outputs/sql_results/<query_name>.csv
"""

from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "sql_results"
OUT.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
con.execute(f"""
    CREATE VIEW transactions AS
    SELECT * FROM read_csv_auto('{ROOT / "data/clean/transactions_clean.csv.gz"}', timestampformat='%Y-%m-%d %H:%M:%S');
    CREATE VIEW members  AS SELECT * FROM read_csv_auto('{ROOT / "data/raw/members.csv"}');
    CREATE VIEW partners AS SELECT * FROM read_csv_auto('{ROOT / "data/raw/payout_partners.csv"}');
""")

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)

for path in sorted((ROOT / "sql").glob("*.sql")):
    df = con.execute(path.read_text()).df()
    df.to_csv(OUT / f"{path.stem}.csv", index=False)
    print(f"\n=== {path.stem} ({len(df)} rows) ===")
    print(df.head(15).to_string(index=False))
