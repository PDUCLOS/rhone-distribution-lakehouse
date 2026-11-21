"""Simulated ERP of "Rhône Distribution", a fictitious B2B industrial-supplies distributor.

Deterministic (fixed seed) and vectorised. Writes one Parquet file per ERP table
to data/generated/erp/ plus anomaly_manifest.csv, the ground truth of every
defect injected on purpose (the dbt tests must find exactly these).

The customer mix (NAF sector, size band, commune) is sampled from the aggregated
SIRENE profile in reference/customer_profile.csv. Names, contacts and histories
are fictitious: emails use the reserved example.com domain, phone numbers use
the ARCEP range reserved for fiction (04 65 71 xx xx).

Usage:
    python generator/generate_erp.py                 # ~2 years, ~1 200 customers
    python generator/generate_erp.py --scale 10      # 10x customers, same rules
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

OUT_DIR = Path("data/generated/erp")
PROFILE = Path("reference/customer_profile.csv")

BRANCHES = pd.DataFrame(
    [
        (1, "LYG", "Lyon Gerland", "Lyon", "69007", date(2004, 3, 1)),
        (2, "VEN", "Vénissieux", "Vénissieux", "69200", date(2011, 9, 1)),
        (3, "VIL", "Villefranche-sur-Saône", "Villefranche-sur-Saône", "69400", date(2015, 1, 5)),
        (4, "BOU", "Bourgoin-Jallieu", "Bourgoin-Jallieu", "38300", date(2018, 6, 1)),
        (5, "STE", "Saint-Étienne", "Saint-Étienne", "42000", date(2020, 2, 3)),
    ],
    columns=["branch_id", "branch_code", "branch_name", "city", "postal_code", "opened_on"],
)

# family: (price median EUR, price sigma, margin rate range, qty median, unit)
FAMILIES = {
    "EPI": (18, 0.6, (0.32, 0.42), 6, "unité"),
    "Outillage électroportatif": (210, 0.5, (0.22, 0.30), 1, "unité"),
    "Outillage à main": (24, 0.6, (0.30, 0.40), 2, "unité"),
    "Fixation et visserie": (9, 0.7, (0.38, 0.50), 20, "boîte"),
    "Quincaillerie": (14, 0.6, (0.33, 0.45), 5, "unité"),
    "Plomberie et chauffage": (38, 0.8, (0.25, 0.35), 4, "unité"),
    "Électricité": (22, 0.8, (0.27, 0.37), 8, "unité"),
    "Consommables atelier": (11, 0.5, (0.35, 0.48), 10, "unité"),
    "Signalisation et sécurité": (45, 0.6, (0.28, 0.38), 3, "unité"),
    "Manutention et levage": (160, 0.7, (0.20, 0.28), 1, "unité"),
}

# share of each family in a segment's purchases
SEGMENT_AFFINITY = {
    "BTP": [0.14, 0.10, 0.10, 0.18, 0.08, 0.14, 0.12, 0.04, 0.07, 0.03],
    "Industrie": [0.12, 0.10, 0.10, 0.16, 0.08, 0.04, 0.08, 0.20, 0.04, 0.08],
    "Maintenance": [0.16, 0.08, 0.12, 0.12, 0.10, 0.10, 0.12, 0.12, 0.06, 0.02],
}

# monthly seasonality per segment (Jan..Dec)
SEASONALITY = {
    "BTP": [0.85, 0.95, 1.10, 1.15, 1.10, 1.12, 1.05, 0.40, 1.08, 1.12, 1.05, 0.75],
    "Industrie": [0.95, 1.00, 1.05, 1.05, 1.00, 1.05, 0.95, 0.50, 1.05, 1.10, 1.10, 0.85],
    "Maintenance": [0.95, 0.95, 1.00, 1.05, 1.05, 1.05, 1.00, 0.70, 1.00, 1.05, 1.05, 0.90],
}

SIZE_ACTIVITY = {"0": 0.5, "1-9": 1.0, "10-49": 2.6, "50-249": 5.0, "250+": 9.0}
SIZE_DISCOUNT = {"0": 0.03, "1-9": 0.06, "10-49": 0.10, "50-249": 0.15, "250+": 0.20}

FIRST_NAMES = ["Camille", "Julien", "Sarah", "Thomas", "Léa", "Nicolas", "Inès", "Mathieu", "Chloé",
               "Antoine", "Manon", "Hugo", "Emma", "Lucas", "Clara", "Karim", "Sofia", "Yanis",
               "Pauline", "Romain", "Nadia", "Bastien", "Elodie", "Mehdi"]
LAST_NAMES = ["Martin", "Bernard", "Dubois", "Moreau", "Laurent", "Girard", "Bonnet", "Mercier",
              "Faure", "Rousseau", "Blanc", "Guerin", "Chevalier", "Perrin", "Morel", "Fontaine",
              "Garnier", "Roux", "Lambert", "Vidal", "Benali", "Da Silva", "Nguyen", "Lefevre"]
SEGMENT_WORDS = {
    "BTP": ["Bâtiment", "Construction", "Rénovation", "Électricité", "Plomberie", "Charpente", "Façades"],
    "Industrie": ["Mécanique", "Usinage", "Métallerie", "Plasturgie", "Chaudronnerie", "Industries"],
    "Maintenance": ["Maintenance", "Services", "Propreté", "Espaces Verts", "Dépannage", "Technique"],
}
SUPPLIER_WORDS = ["Pro", "Indus", "Tech", "Fix", "Equip", "Outil", "Sécur", "Therm", "Volt", "Lift"]


# --------------------------------------------------------------------------- calendar
def easter(year: int) -> date:
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def french_holidays(years: range) -> set[date]:
    out: set[date] = set()
    for y in years:
        e = easter(y)
        out |= {date(y, 1, 1), date(y, 5, 1), date(y, 5, 8), date(y, 7, 14), date(y, 8, 15),
                date(y, 11, 1), date(y, 11, 11), date(y, 12, 25),
                e + timedelta(days=1), e + timedelta(days=39), e + timedelta(days=50)}
    return out


def build_calendar(start: date, end: date) -> pd.DataFrame:
    days = pd.date_range(start, end, freq="D")
    holidays = french_holidays(range(start.year, end.year + 1))
    cal = pd.DataFrame({"calendar_date": days.date})
    cal["iso_day_of_week"] = days.day_of_week + 1
    cal["is_holiday"] = cal["calendar_date"].isin(holidays)
    cal["is_business_day"] = (cal["iso_day_of_week"] <= 5) & ~cal["is_holiday"]
    return cal


# --------------------------------------------------------------------------- masters
def build_reps(rng: np.random.Generator) -> pd.DataFrame:
    rows, rep_id = [], 1
    for branch_id, n in zip(BRANCHES.branch_id, [6, 5, 3, 3, 3]):
        for _ in range(n):
            rows.append((rep_id, branch_id, rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES),
                         date(2026, 10, 30) - timedelta(days=int(rng.integers(200, 4000)))))
            rep_id += 1
    return pd.DataFrame(rows, columns=["rep_id", "branch_id", "first_name", "last_name", "hired_on"])


def build_suppliers(rng: np.random.Generator) -> pd.DataFrame:
    n = 32
    names = [f"{rng.choice(SUPPLIER_WORDS)}{rng.choice(SUPPLIER_WORDS).lower()} {suffix}"
             for suffix in rng.choice(["SAS", "SA", "GmbH", "SpA", "SL"], n)]
    country = np.where(np.char.endswith(np.array([s for s in names]), "GmbH"), "DE",
              np.where(np.char.endswith(np.array(names), "SpA"), "IT",
              np.where(np.char.endswith(np.array(names), "SL"), "ES", "FR")))
    lead = rng.integers(3, 15, n)
    reliability = rng.beta(8, 2, n)  # share of POs received on time
    return pd.DataFrame({
        "supplier_id": np.arange(1, n + 1),
        "supplier_name": [f"{name} #{i:02d}" for i, name in enumerate(names, 1)],
        "country_code": country,
        "standard_lead_time_days": lead,
        "reliability_score": reliability.round(3),
    })


def build_products(rng: np.random.Generator, suppliers: pd.DataFrame, scale: float) -> pd.DataFrame:
    frames, next_id = [], 1
    supplier_ids = suppliers.supplier_id.to_numpy()
    for f_idx, (family, (price, sigma, margin, _, unit)) in enumerate(FAMILIES.items()):
        n = int(150 * max(1.0, scale ** 0.5))
        fam_suppliers = rng.choice(supplier_ids, size=4, replace=False)
        list_price = np.round(np.exp(rng.normal(np.log(price), sigma, n)), 2).clip(0.5)
        margin_rate = rng.uniform(*margin, n)
        frames.append(pd.DataFrame({
            "product_id": np.arange(next_id, next_id + n),
            "sku": [f"RD-{f_idx + 1:02d}-{i:05d}" for i in range(1, n + 1)],
            "product_name": [f"{family} — réf. {i:04d}" for i in range(1, n + 1)],
            "product_family": family,
            "sales_unit": unit,
            "list_price_2024": list_price,
            "unit_cost_2024": np.round(list_price * (1 - margin_rate), 2),
            "supplier_id": rng.choice(fam_suppliers, n),
            # Zipf-like popularity inside the family
            "popularity": 1.0 / np.arange(1, n + 1) ** 0.9,
        }))
        next_id += n
    products = pd.concat(frames, ignore_index=True)
    products["popularity"] = products.groupby("product_family")["popularity"].transform(lambda p: p / p.sum())
    products["is_active"] = True
    return products


def branch_for(postal_codes: pd.Series) -> np.ndarray:
    pc = postal_codes.astype(str)
    dep = pc.str[:2]
    north_69 = pc.str[:3].isin(["694", "696", "697", "698"]) | pc.isin(["69400", "69220", "69480"])
    east_lyon = pc.str[:3].isin(["692", "693", "691"]) & ~north_69
    return np.select(
        [dep == "38", dep == "42", dep == "01", north_69, east_lyon],
        [4, 5, 3, 3, 2],
        default=1,
    )


def build_customers(rng: np.random.Generator, reps: pd.DataFrame, n: int, start: date, end: date) -> pd.DataFrame:
    profile = pd.read_csv(PROFILE, dtype={"postal_code": str, "departement": str})
    weights = profile["sampled_count"] / profile["sampled_count"].sum()
    picked = profile.iloc[rng.choice(len(profile), size=n, p=weights)].reset_index(drop=True)

    first = rng.choice(FIRST_NAMES, n)
    last = rng.choice(LAST_NAMES, n)
    words = np.array([rng.choice(SEGMENT_WORDS[s]) for s in picked.segment])
    legal = rng.choice(["SARL", "SAS", "EURL", "SA"], n, p=[0.45, 0.35, 0.15, 0.05])
    names = [f"{lg} {ln} {w}" for lg, ln, w in zip(legal, last, words)]
    slugs = pd.Series(names).str.lower().str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii")
    slugs = slugs.str.replace(r"[^a-z]+", "-", regex=True).str.strip("-")

    customers = pd.DataFrame({
        "customer_id": np.arange(1, n + 1),
        "account_code": [f"C{100000 + i}" for i in range(1, n + 1)],
        "company_name": names,
        "segment": picked.segment,
        "naf_code": picked.naf_code,
        "size_band": picked.size_band,
        "city": picked.commune.str.title(),
        "postal_code": picked.postal_code,
        "contact_name": [f"{f} {l}" for f, l in zip(first, last)],
        "contact_email": [f"{f.lower()}.{l.lower().replace(' ', '')}@{s}.example.com"
                          for f, l, s in zip(pd.Series(first).str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii"),
                                             pd.Series(last).str.normalize("NFKD").str.encode("ascii", "ignore").str.decode("ascii"),
                                             slugs)],
        "contact_phone": [f"04 65 71 {rng.integers(0, 100):02d} {rng.integers(0, 100):02d}" for _ in range(n)],
        "payment_terms_days": rng.choice([30, 45, 60], n, p=[0.5, 0.3, 0.2]),
    })
    customers["branch_id"] = branch_for(customers.postal_code)
    reps_by_branch = reps.groupby("branch_id")["rep_id"].apply(list).to_dict()
    customers["rep_id"] = [rng.choice(reps_by_branch[b]) for b in customers.branch_id]

    size_mult = customers.size_band.map(SIZE_ACTIVITY).to_numpy()
    customers["activity"] = rng.lognormal(0, 0.9, n) * size_mult              # Pareto-ish spend
    customers["basket_mean"] = 1.2 + 0.6 * np.log1p(size_mult) + rng.gamma(2, 0.3, n)
    customers["discount_rate"] = (customers.size_band.map(SIZE_DISCOUNT) + rng.normal(0, 0.02, n)).clip(0, 0.3).round(3)
    customers["credit_limit"] = (np.round(customers.activity * 4000, -2)).clip(1000, 150000)

    customers["is_late_payer"] = rng.random(n) < 0.15
    horizon = (end - start).days
    created_offset = np.where(rng.random(n) < 0.10, rng.integers(30, horizon - 60, n), -rng.integers(30, 3000, n))
    customers["created_at"] = [start + timedelta(days=int(o)) for o in created_offset]

    churn = rng.random(n) < 0.12
    churn_offset = rng.integers(200, horizon - 45, n)
    customers["churn_date"] = [start + timedelta(days=int(o)) if c else None for c, o in zip(churn, churn_offset)]
    # A churner acquired late cannot leave before joining
    customers.loc[customers.churn_date.notna() & (customers.churn_date <= customers.created_at + timedelta(days=120)), "churn_date"] = None
    return customers


# --------------------------------------------------------------------------- transactions
def build_orders(rng, customers, calendar, start, end, scale_lambda):
    cal = calendar[calendar.is_business_day | (calendar.iso_day_of_week == 6)].reset_index(drop=True)
    days = pd.DatetimeIndex(pd.to_datetime(cal.calendar_date))
    n_c, n_d = len(customers), len(cal)

    seg_idx = customers.segment.map({"BTP": 0, "Industrie": 1, "Maintenance": 2}).to_numpy()
    season = np.array([SEASONALITY[s] for s in ["BTP", "Industrie", "Maintenance"]])[:, days.month - 1]   # 3 x D
    weekday = np.where(cal.iso_day_of_week == 6, 0.12, 1.0)                                                 # Saturday: counter only
    years = (days - pd.Timestamp(start)).days.to_numpy() / 365.25
    trend = 1.03 ** years

    base = 0.055 * scale_lambda * customers.activity.to_numpy()[:, None]
    rate = base * season[seg_idx] * (weekday * trend)[None, :]

    day_num = (days - pd.Timestamp(start)).days.to_numpy()[None, :]
    created = np.array([(c - start).days for c in customers.created_at])[:, None]
    rate = np.where(day_num < created, 0.0, rate)

    churn_num = np.array([(c - start).days if c is not None else 10 ** 6 for c in customers.churn_date])[:, None]
    decay_window = 120
    pre = (day_num >= churn_num - decay_window) & (day_num < churn_num)
    fade = 1 - 0.65 * (day_num - (churn_num - decay_window)) / decay_window     # 1 -> 0.35
    rate = np.where(pre, rate * fade, rate)
    rate = np.where(day_num >= churn_num, 0.0, rate)

    counts = rng.poisson(rate)
    ci, di = np.nonzero(counts)
    reps = counts[ci, di]
    ci, di = np.repeat(ci, reps), np.repeat(di, reps)

    cust = customers.iloc[ci].reset_index(drop=True)
    order_dates = cal.calendar_date.to_numpy()[di]
    is_saturday = cal.iso_day_of_week.to_numpy()[di] == 6
    big = cust.size_band.isin(["50-249", "250+"]).to_numpy()
    channel = np.where(is_saturday, "comptoir",
              np.where(big & (rng.random(len(cust)) < 0.45), "edi",
                       rng.choice(["comptoir", "commercial", "web"], len(cust), p=[0.38, 0.34, 0.28])))
    hour = rng.integers(7, 18, len(cust))
    minute = rng.integers(0, 60, len(cust))
    created_at = pd.to_datetime(order_dates) + pd.to_timedelta(hour, "h") + pd.to_timedelta(minute, "m")

    orders = pd.DataFrame({
        "order_id": np.arange(1, len(cust) + 1),
        "customer_id": cust.customer_id,
        "branch_id": cust.branch_id,
        "rep_id": cust.rep_id,
        "channel": channel,
        "order_date": order_dates,
        "created_at": created_at,
    }).sort_values(["created_at", "order_id"]).reset_index(drop=True)
    orders["order_id"] = np.arange(1, len(orders) + 1)
    orders["order_number"] = "CMD-" + pd.to_datetime(orders.order_date).dt.strftime("%y%m") + "-" + orders.order_id.astype(str).str.zfill(7)
    # Pre-churn flag (drives smaller baskets and slower payments downstream)
    churn_by_c = dict(zip(customers.customer_id, customers.churn_date))
    od = pd.to_datetime(orders.order_date)
    cd = pd.to_datetime(orders.customer_id.map(churn_by_c))
    orders["_pre_churn"] = (cd.notna() & (od >= cd - pd.Timedelta(days=decay_window)) & (od < cd)).to_numpy()
    return orders


def build_lines(rng, orders, customers, products, suppliers, start):
    cust = customers.set_index("customer_id").loc[orders.customer_id]
    basket = cust.basket_mean.to_numpy() * np.where(orders._pre_churn, 0.6, 1.0)
    n_lines = 1 + rng.poisson(np.maximum(basket - 1, 0.1))
    oi = np.repeat(np.arange(len(orders)), n_lines)
    n = len(oi)

    seg = cust.segment.to_numpy()[oi]
    families = list(FAMILIES)
    fam_idx = np.empty(n, dtype=int)
    for s, aff in SEGMENT_AFFINITY.items():
        m = seg == s
        fam_idx[m] = rng.choice(len(families), m.sum(), p=aff)

    product_id = np.empty(n, dtype=int)
    for k, fam in enumerate(families):
        m = fam_idx == k
        fp = products[products.product_family == fam]
        product_id[m] = rng.choice(fp.product_id.to_numpy(), m.sum(), p=fp.popularity.to_numpy())

    prod = products.set_index("product_id").loc[product_id]
    qty_median = np.array([FAMILIES[f][3] for f in prod.product_family])
    qty = np.maximum(1, np.round(rng.lognormal(np.log(qty_median), 0.7))).astype(int)

    order_dates = pd.to_datetime(orders.order_date.to_numpy()[oi])
    years = ((order_dates - pd.Timestamp(start)).days.to_numpy()) / 365.25
    inflation = 1.025 ** years
    discount = cust.discount_rate.to_numpy()[oi]
    unit_price = np.round(prod.list_price_2024.to_numpy() * inflation * (1 - discount), 2)
    unit_cost = np.round(prod.unit_cost_2024.to_numpy() * inflation, 2)

    # Stockouts: unreliable suppliers and peak months ship short
    reliability = suppliers.set_index("supplier_id").loc[prod.supplier_id, "reliability_score"].to_numpy()
    peak = np.isin(order_dates.month, [3, 4, 5, 6, 9, 10])
    p_short = (1 - reliability) * 0.12 + np.where(peak, 0.015, 0.0)
    short = rng.random(n) < p_short
    qty_shipped = np.where(short, np.floor(qty * rng.uniform(0, 0.7, n)), qty).astype(int)

    is_return = rng.random(n) < 0.012
    qty = np.where(is_return, -qty, qty)
    qty_shipped = np.where(is_return, qty, qty_shipped)

    lines = pd.DataFrame({
        "order_id": orders.order_id.to_numpy()[oi],
        "product_id": product_id,
        "qty_ordered": qty,
        "qty_shipped": qty_shipped,
        "unit_price": unit_price,
        "unit_cost": unit_cost,
        "discount_rate": discount,
        "is_return": is_return,
    })
    lines["line_no"] = lines.groupby("order_id").cumcount() + 1
    lines.insert(0, "order_line_id", np.arange(1, n + 1))
    return lines


def add_business_days(dates: pd.Series, n: np.ndarray) -> pd.Series:
    return pd.Series(np.busday_offset(dates.to_numpy().astype("datetime64[D]"), n, roll="forward")).dt.date


def build_fulfilment(rng, orders, lines, customers, end):
    n = len(orders)
    counter = (orders.channel == "comptoir").to_numpy()
    ship_lag = np.where(counter, 0, rng.choice([0, 1, 2], n, p=[0.3, 0.5, 0.2]))
    deliver_lag = np.where(counter, 0, rng.choice([1, 2, 3], n, p=[0.55, 0.35, 0.10]))
    shipped = add_business_days(pd.to_datetime(orders.order_date), ship_lag)
    delivered = add_business_days(pd.to_datetime(shipped), deliver_lag)

    shipments = pd.DataFrame({
        "shipment_id": orders.order_id,
        "order_id": orders.order_id,
        "shipped_on": shipped,
        "delivered_on": delivered,
        "carrier": np.where(counter, "retrait comptoir", rng.choice(["Geodis", "DB Schenker", "Flotte RD"], n, p=[0.4, 0.3, 0.3])),
    })
    shipments = shipments[pd.to_datetime(shipments.shipped_on) <= pd.Timestamp(end)].copy()
    shipments.loc[pd.to_datetime(shipments.delivered_on) > pd.Timestamp(end), "delivered_on"] = None

    amounts = (lines.assign(amount=lines.qty_shipped * lines.unit_price)
               .groupby("order_id")["amount"].sum().round(2))
    inv = orders[orders.order_id.isin(shipments.order_id)][["order_id", "customer_id", "order_date", "_pre_churn"]].copy()
    inv = inv.merge(shipments[["order_id", "shipped_on"]], on="order_id")
    inv["invoice_id"] = np.arange(1, len(inv) + 1)
    inv["invoice_number"] = "FAC-" + inv.invoice_id.astype(str).str.zfill(8)
    inv["invoice_date"] = inv.shipped_on
    terms = customers.set_index("customer_id").loc[inv.customer_id, "payment_terms_days"].to_numpy()
    inv["due_date"] = (pd.to_datetime(inv.invoice_date) + pd.to_timedelta(terms, "D")).dt.date
    inv["amount_excl_tax"] = inv.order_id.map(amounts).fillna(0).to_numpy()
    inv["vat_amount"] = (inv.amount_excl_tax * 0.20).round(2)

    late = customers.set_index("customer_id").loc[inv.customer_id, "is_late_payer"].to_numpy()
    m = len(inv)
    delay = np.where(late, rng.normal(26, 12, m), rng.normal(-3, 6, m)).clip(-25, 150)
    delay = delay + np.where(inv._pre_churn, rng.normal(18, 6, m), 0)
    never = late & (rng.random(m) < 0.02)
    paid_on = (pd.to_datetime(inv.due_date) + pd.to_timedelta(np.round(delay), "D")).dt.date
    paid_on = pd.Series(np.maximum(pd.to_datetime(paid_on), pd.to_datetime(inv.invoice_date))).dt.date
    is_paid = ~never & (pd.to_datetime(paid_on) <= pd.Timestamp(end)).to_numpy()

    payments = pd.DataFrame({
        "invoice_id": inv.invoice_id[is_paid].to_numpy(),
        "paid_on": paid_on[is_paid].to_numpy(),
        "amount_paid": (inv.amount_excl_tax + inv.vat_amount)[is_paid].round(2).to_numpy(),
        "payment_method": rng.choice(["virement", "LCR", "chèque", "carte"], int(is_paid.sum()), p=[0.62, 0.22, 0.08, 0.08]),
    })
    payments.insert(0, "payment_id", np.arange(1, len(payments) + 1))
    inv["status"] = np.where(is_paid, "paid", np.where(never, "disputed", "open"))
    inv["_paid_on"] = np.where(is_paid, paid_on, None)
    return shipments, inv, payments


def build_purchase_orders(rng, lines, orders, products, suppliers, end):
    df = lines[["order_id", "product_id", "qty_shipped"]].merge(orders[["order_id", "order_date"]], on="order_id")
    df = df[df.qty_shipped > 0]
    df["week"] = pd.to_datetime(df.order_date).dt.to_period("W-SUN").dt.start_time
    weekly = df.groupby(["product_id", "week"], as_index=False)["qty_shipped"].sum()
    weekly = weekly.merge(products[["product_id", "supplier_id", "unit_cost_2024"]], on="product_id")
    weekly = weekly.merge(suppliers[["supplier_id", "standard_lead_time_days", "reliability_score"]], on="supplier_id")
    n = len(weekly)
    on_time = rng.random(n) < weekly.reliability_score.to_numpy()
    slip = np.where(on_time, rng.integers(-1, 2, n), rng.integers(3, 15, n))
    ordered = weekly.week + pd.Timedelta(days=4)
    expected = ordered + pd.to_timedelta(weekly.standard_lead_time_days, "D")
    received = expected + pd.to_timedelta(slip, "D")
    po = pd.DataFrame({
        "purchase_order_id": np.arange(1, n + 1),
        "supplier_id": weekly.supplier_id,
        "product_id": weekly.product_id,
        "ordered_on": ordered.dt.date,
        "expected_on": expected.dt.date,
        "received_on": np.where(received <= pd.Timestamp(end), received.dt.date, None),
        "qty_ordered": np.ceil(weekly.qty_shipped * 1.1).astype(int),
        "unit_cost": weekly.unit_cost_2024.round(2),
    })
    return po[po.ordered_on <= end]


def lifecycle(orders, shipments, invoices, end):
    """Order status and updated_at, so incremental extraction has something to pick up."""
    ship = shipments.set_index("order_id")
    inv = invoices.set_index("order_id")
    status = np.full(len(orders), "created", dtype=object)
    updated = pd.to_datetime(orders.created_at).copy()

    has_ship = orders.order_id.isin(ship.index).to_numpy()
    status[has_ship] = "shipped"
    s_dates = pd.to_datetime(orders.order_id.map(ship.shipped_on)) + pd.Timedelta(hours=17)
    updated = np.where(has_ship, np.maximum(updated, s_dates), updated)

    has_inv = orders.order_id.isin(inv.index).to_numpy()
    status[has_inv] = "invoiced"
    paid = pd.to_datetime(orders.order_id.map(inv["_paid_on"]))
    is_paid = paid.notna().to_numpy()
    status[is_paid] = "paid"
    updated = np.where(is_paid, np.maximum(updated, paid + pd.Timedelta(hours=10)), updated)

    orders["status"] = status
    orders["updated_at"] = pd.to_datetime(updated)
    invoices["updated_at"] = pd.to_datetime(invoices["_paid_on"]).fillna(pd.to_datetime(invoices.invoice_date)) + pd.Timedelta(hours=10)
    return orders, invoices


# --------------------------------------------------------------------------- anomalies
def inject_anomalies(rng, customers, orders, lines, shipments, invoices):
    """Inject defects on purpose. Each is recorded in the manifest with its exact count.

    Line-level defects only hit lines that are alone in their
    (order date, customer, product) grain, so they stay detectable after the
    daily aggregation that feeds Snowflake.
    """
    manifest = []
    keyed = lines.merge(orders[["order_id", "order_date", "customer_id"]], on="order_id")
    grain_size = keyed.groupby(["order_date", "customer_id", "product_id"])["order_line_id"].transform("size")
    alone = keyed[(grain_size == 1) & ~keyed.is_return & (keyed.qty_shipped > 0)].order_line_id.to_numpy()
    picked = rng.choice(alone, 37, replace=False)

    zero_price = picked[:25]
    lines.loc[lines.order_line_id.isin(zero_price), "unit_price"] = 0.0
    manifest.append(("zero_price_line", "erp.sales_order_lines", len(zero_price)))

    negative = picked[25:]
    m = lines.order_line_id.isin(negative)
    lines.loc[m, "qty_ordered"] = -lines.loc[m, "qty_ordered"].abs()
    lines.loc[m, "qty_shipped"] = lines.loc[m, "qty_ordered"]
    manifest.append(("negative_qty_not_flagged_as_return", "erp.sales_order_lines", len(negative)))

    late_ship = rng.choice(shipments[shipments.carrier != "retrait comptoir"].index, 15, replace=False)
    od = shipments.loc[late_ship, "order_id"].map(orders.set_index("order_id").order_date)
    shipments.loc[late_ship, "shipped_on"] = (pd.to_datetime(od) - pd.to_timedelta(rng.integers(2, 10, 15), "D")).dt.date.to_numpy()
    manifest.append(("shipped_before_order", "erp.shipments", 15))

    max_order = orders.order_id.max()
    orphans = invoices.sample(10, random_state=7).copy()
    orphans["invoice_id"] = np.arange(invoices.invoice_id.max() + 1, invoices.invoice_id.max() + 11)
    orphans["invoice_number"] = "FAC-" + orphans.invoice_id.astype(str).str.zfill(8)
    orphans["order_id"] = np.arange(max_order + 100001, max_order + 100011)
    orphans["status"] = "open"
    orphans["_paid_on"] = None
    invoices = pd.concat([invoices, orphans], ignore_index=True)
    manifest.append(("orphan_invoice", "erp.invoices", 10))

    no_cp = rng.choice(customers.index, 8, replace=False)
    customers.loc[no_cp, "postal_code"] = None
    manifest.append(("customer_missing_postal_code", "erp.customers", 8))

    return customers, lines, shipments, invoices, pd.DataFrame(manifest, columns=["anomaly_type", "source_table", "expected_count"])


# --------------------------------------------------------------------------- main
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scale", type=float, default=1.0, help="Customer-count multiplier")
    parser.add_argument("--start", default="2024-11-01")
    parser.add_argument("--end", default="2026-10-30")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)

    calendar = build_calendar(start, end)
    reps = build_reps(rng)
    suppliers = build_suppliers(rng)
    products = build_products(rng, suppliers, args.scale)
    customers = build_customers(rng, reps, int(1200 * args.scale), start, end)
    orders = build_orders(rng, customers, calendar, start, end, 1.0)
    lines = build_lines(rng, orders, customers, products, suppliers, start)
    shipments, invoices, payments = build_fulfilment(rng, orders, lines, customers, end)
    purchase_orders = build_purchase_orders(rng, lines, orders, products, suppliers, end)
    orders, invoices = lifecycle(orders, shipments, invoices, end)
    customers, lines, shipments, invoices, manifest = inject_anomalies(rng, customers, orders, lines, shipments, invoices)

    now = pd.Timestamp(end) + pd.Timedelta(hours=20)
    customers["updated_at"] = now
    lines = lines.merge(orders[["order_id", "created_at", "updated_at"]], on="order_id")

    tables = {
        "branches": BRANCHES,
        "sales_reps": reps,
        "suppliers": suppliers,
        "products": products.drop(columns=["popularity"]),
        "customers": customers.drop(columns=["activity", "basket_mean", "is_late_payer", "churn_date"]),
        "sales_orders": orders.drop(columns=["_pre_churn"]),
        "sales_order_lines": lines,
        "shipments": shipments,
        "invoices": invoices.drop(columns=["_pre_churn", "_paid_on", "shipped_on", "order_date"]),
        "payments": payments,
        "purchase_orders": purchase_orders,
        "calendar": calendar,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(OUT_DIR / f"{name}.parquet", index=False)
        print(f"{name:20s} {len(df):>9,d} rows")

    manifest.to_csv(OUT_DIR.parent / "anomaly_manifest.csv", index=False)
    # Hidden truth for ML evaluation only (never loaded into the ERP)
    customers[["customer_id", "churn_date", "is_late_payer"]].to_parquet(OUT_DIR.parent / "ground_truth_customers.parquet", index=False)
    print(f"anomalies: {manifest.expected_count.sum()} injected -> {OUT_DIR.parent / 'anomaly_manifest.csv'}")


if __name__ == "__main__":
    main()
