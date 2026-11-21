"""Nightly extract from the ERP (PostgreSQL) for the Snowflake slow path.

Writes gzip CSV files to data/landing/snowflake/<batch_id>/, one per entity:

- daily_sales      order lines AGGREGATED to day x customer x product x branch x rep x channel
- orders           order headers changed in the window (status lifecycle)
- shipments        shipments dispatched in the window, with their order date
- invoices         invoices changed in the window
- payments         payments received in the window
- purchase_orders  supplier POs ordered or received in the window
- customers, products, suppliers, branches, sales_reps, calendar   full snapshots

Usage:
    python generator/extract_daily.py --backfill          # whole history, one batch
    python generator/extract_daily.py --date 2026-10-30   # one business day
"""

from __future__ import annotations

import argparse
import gzip
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import psycopg

LANDING = Path("data/landing/snowflake")

DELTA_QUERIES = {
    "daily_sales": """
        select o.order_date as sale_date, o.customer_id, l.product_id, o.branch_id, o.rep_id, o.channel,
               count(distinct o.order_id)                                         as order_count,
               count(*)                                                           as line_count,
               sum(l.qty_ordered) filter (where not l.is_return)                  as qty_ordered,
               sum(l.qty_shipped) filter (where not l.is_return)                  as qty_shipped,
               coalesce(-sum(l.qty_shipped) filter (where l.is_return), 0)        as qty_returned,
               round(sum(l.qty_shipped * l.unit_price), 2)                        as net_amount,
               round(sum(l.qty_shipped * l.unit_cost), 2)                         as cost_amount,
               round(sum(l.qty_ordered * l.unit_price) filter (where not l.is_return), 2) as ordered_amount
        from erp.sales_order_lines l
        join erp.sales_orders o using (order_id)
        where o.order_date >= %(start)s and o.order_date < %(end)s
        group by 1, 2, 3, 4, 5, 6""",
    "orders": """
        select order_id, order_number, customer_id, branch_id, rep_id, channel, order_date, status, created_at, updated_at
        from erp.sales_orders where updated_at >= %(start)s and updated_at < %(end)s""",
    "shipments": """
        select s.shipment_id, s.order_id, o.order_date, s.shipped_on, s.delivered_on, s.carrier
        from erp.shipments s left join erp.sales_orders o using (order_id)
        where coalesce(s.delivered_on, s.shipped_on) >= %(start)s and s.shipped_on < %(end)s
           or o.order_date >= %(start)s and o.order_date < %(end)s""",
    "invoices": """
        select invoice_id, invoice_number, order_id, customer_id, invoice_date, due_date,
               amount_excl_tax, vat_amount, status, updated_at
        from erp.invoices where updated_at >= %(start)s and updated_at < %(end)s""",
    "payments": """
        select payment_id, invoice_id, paid_on, amount_paid, payment_method
        from erp.payments where paid_on >= %(start)s and paid_on < %(end)s""",
    "purchase_orders": """
        select purchase_order_id, supplier_id, product_id, ordered_on, expected_on, received_on, qty_ordered, unit_cost
        from erp.purchase_orders
        where ordered_on >= %(start)s and ordered_on < %(end)s
           or received_on >= %(start)s and received_on < %(end)s""",
}

SNAPSHOT_TABLES = ["customers", "products", "suppliers", "branches", "sales_reps", "calendar"]


def export(con: psycopg.Connection, query: str, params: dict, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    sql = psycopg.ClientCursor(con).mogrify(query, params)
    rows = 0
    with gzip.open(path, "wb") as f, con.cursor().copy(f"copy ({sql}) to stdout with (format csv, header true)") as copy:
        for chunk in copy:
            f.write(chunk)
            rows += bytes(chunk).count(b"\n")
    return rows - 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date", help="Business date to extract (YYYY-MM-DD)")
    group.add_argument("--backfill", action="store_true", help="Extract the full history as one batch")
    parser.add_argument("--dsn", default="postgresql://localhost/rhone_erp")
    args = parser.parse_args()

    if args.backfill:
        start, end, batch_id = date(2000, 1, 1), date(2100, 1, 1), "backfill"
    else:
        start = date.fromisoformat(args.date)
        end, batch_id = start + timedelta(days=1), start.isoformat()

    out = LANDING / batch_id
    extracted_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with psycopg.connect(args.dsn) as con:
        for entity, query in DELTA_QUERIES.items():
            n = export(con, f"select q.*, '{batch_id}' as batch_id, timestamp '{extracted_at}' as extracted_at from ({query}) q",
                       {"start": start, "end": end}, out / f"{entity}.csv.gz")
            print(f"{entity:16s} {n:>9,d}")
        for table in SNAPSHOT_TABLES:
            n = export(con, f"select t.*, '{batch_id}' as batch_id, timestamp '{extracted_at}' as extracted_at from erp.{table} t",
                       {}, out / f"{table}.csv.gz")
            print(f"{table:16s} {n:>9,d}  (snapshot)")
    print(f"batch {batch_id} -> {out}")


if __name__ == "__main__":
    main()
