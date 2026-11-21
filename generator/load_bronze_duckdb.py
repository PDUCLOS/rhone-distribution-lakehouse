"""Local stand-in for Snowflake's COPY INTO: append every landing batch to bronze.* in DuckDB.

Bronze is append-only, exactly as on Snowflake: a record extracted in several
batches appears several times, and Silver keeps the latest version.

    python generator/load_bronze_duckdb.py [--db warehouse.duckdb]
"""

import argparse
from pathlib import Path

import duckdb

LANDING = Path("data/landing/snowflake")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="warehouse.duckdb")
    args = parser.parse_args()

    batches = sorted(p for p in LANDING.iterdir() if p.is_dir())
    entities = sorted({f.name.removesuffix(".csv.gz") for b in batches for f in b.glob("*.csv.gz")})
    con = duckdb.connect(args.db)
    con.execute("create schema if not exists bronze")
    for entity in entities:
        files = [str(b / f"{entity}.csv.gz") for b in batches if (b / f"{entity}.csv.gz").exists()]
        con.execute(f"""
            create or replace table bronze.{entity} as
            select *, current_timestamp as loaded_at
            from read_csv({files}, header = true, union_by_name = true)
        """)
        n = con.execute(f"select count(*) from bronze.{entity}").fetchone()[0]
        print(f"bronze.{entity:16s} {n:>9,d} rows from {len(files)} batch(es)")
    con.close()


if __name__ == "__main__":
    main()
