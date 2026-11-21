"""Upload nightly extract batches to the Snowflake stage, then load bronze.

    pip install snowflake-connector-python
    export SNOWFLAKE_ACCOUNT=... SNOWFLAKE_USER=... SNOWFLAKE_PASSWORD=...
    python generator/push_to_snowflake.py                 # every batch folder
    python generator/push_to_snowflake.py --batch 2026-10-29

PUT skips files already on the stage (same name and checksum), and COPY skips
files already loaded, so running it twice is harmless.
"""

import argparse
import os
from pathlib import Path

import snowflake.connector

LANDING = Path("data/landing/snowflake")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", help="Only this batch folder (default: all)")
    parser.add_argument("--no-load", action="store_true", help="Upload only, do not call bronze.load_all()")
    args = parser.parse_args()

    batches = [LANDING / args.batch] if args.batch else sorted(p for p in LANDING.iterdir() if p.is_dir())
    con = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role="SYSADMIN",
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "RD_WH"),
        database="RHONE",
        schema="BRONZE",
    )
    cur = con.cursor()
    for batch in batches:
        for f in sorted(batch.glob("*.csv.gz")):
            cur.execute(f"put 'file://{f.resolve()}' @landing/{batch.name}/ auto_compress = false overwrite = false")
        print(f"uploaded {batch.name}")
    if not args.no_load:
        cur.execute("call bronze.load_all()")
        print(cur.fetchone()[0])
        for table, rows in cur.execute(
            "select table_name, row_count from information_schema.tables where table_schema = 'BRONZE' order by 1"
        ):
            print(f"bronze.{table.lower():16s} {rows:>9,d}")
    con.close()


if __name__ == "__main__":
    main()
