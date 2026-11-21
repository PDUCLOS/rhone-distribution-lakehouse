"""Load the generated ERP Parquet files into PostgreSQL (schema erp).

    python generator/load_postgres.py [--dsn postgresql://localhost/rhone_erp]
"""

import argparse
import io
from pathlib import Path

import pandas as pd
import psycopg

GENERATED = Path("data/generated/erp")
# Parents first, so the declared foreign keys are satisfied
LOAD_ORDER = ["branches", "sales_reps", "suppliers", "products", "customers", "sales_orders",
              "sales_order_lines", "shipments", "invoices", "payments", "purchase_orders", "calendar"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default="postgresql://localhost/rhone_erp")
    args = parser.parse_args()

    with psycopg.connect(args.dsn, autocommit=False) as con:
        con.execute(Path("sql/erp_schema.sql").read_text())
        for table in LOAD_ORDER:
            df = pd.read_parquet(GENERATED / f"{table}.parquet")
            cols = [c[0] for c in con.execute(f"select * from erp.{table} limit 0").description]
            buffer = io.StringIO()
            df[cols].to_csv(buffer, index=False, header=False, na_rep="\\N")
            buffer.seek(0)
            with con.cursor().copy(f"copy erp.{table} ({', '.join(cols)}) from stdin with (format csv, null '\\N')") as copy:
                copy.write(buffer.read())
            print(f"erp.{table:20s} {len(df):>9,d}")
        con.commit()


if __name__ == "__main__":
    main()
