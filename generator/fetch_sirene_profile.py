"""Build an aggregated customer profile from the public SIRENE register.

Uses recherche-entreprises.api.gouv.fr (free, no key). Only aggregates are
written: counts by department x NAF code x size band x commune. No company
name, no SIREN, nothing that identifies a business. The simulated ERP samples
fictitious customers from this profile, so the customer mix (sectors, sizes,
geography) matches the real Lyon-area economy without attaching made-up
histories to real companies.

Output: reference/customer_profile.csv (committed, so generation runs offline).
"""

from __future__ import annotations

import csv
import time
from collections import Counter
from pathlib import Path

import requests

API = "https://recherche-entreprises.api.gouv.fr/search"
DEPARTMENTS = ["69", "01", "38", "42"]
PAGES_PER_QUERY = 4   # 25 results per page -> up to 100 establishments sampled per query
PAUSE_SECONDS = 0.2   # API limit is 7 req/s

# Customer segments of an industrial-supplies distributor, by NAF code
NAF_SEGMENTS = {
    "41.20A": "BTP", "41.20B": "BTP", "43.21A": "BTP", "43.22A": "BTP", "43.22B": "BTP",
    "43.29A": "BTP", "43.31Z": "BTP", "43.32A": "BTP", "43.34Z": "BTP", "43.91B": "BTP",
    "43.99C": "BTP", "42.11Z": "BTP",
    "25.11Z": "Industrie", "25.62B": "Industrie", "28.29B": "Industrie", "22.29A": "Industrie",
    "33.12Z": "Maintenance", "33.20C": "Maintenance", "81.21Z": "Maintenance", "81.30Z": "Maintenance",
}

SIZE_BANDS = {  # INSEE tranche_effectif_salarie -> readable band
    None: "0", "NN": "0", "00": "0", "01": "1-9", "02": "1-9", "03": "1-9",
    "11": "10-49", "12": "10-49", "21": "50-249", "22": "50-249",
    "31": "250+", "32": "250+", "41": "250+", "42": "250+", "51": "250+", "52": "250+", "53": "250+",
}


def search(naf: str, departement: str, page: int) -> dict:
    params = {
        "activite_principale": naf,
        "departement": departement,
        "etat_administratif": "A",
        "per_page": 25,
        "page": page,
    }
    for attempt in range(3):
        response = requests.get(API, params=params, timeout=30)
        if response.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        response.raise_for_status()
        return response.json()
    response.raise_for_status()
    return {}


def main() -> None:
    sampled: Counter = Counter()
    totals: dict[tuple[str, str], int] = {}

    for departement in DEPARTMENTS:
        for naf in NAF_SEGMENTS:
            for page in range(1, PAGES_PER_QUERY + 1):
                payload = search(naf, departement, page)
                time.sleep(PAUSE_SECONDS)
                totals[(departement, naf)] = payload.get("total_results", 0)
                for company in payload.get("results", []):
                    # Department search matches establishments: take the local one, not the head office.
                    for etab in company.get("matching_etablissements", []):
                        if not str(etab.get("code_postal", "")).startswith(departement):
                            continue
                        size = SIZE_BANDS.get(etab.get("tranche_effectif_salarie"), "0")
                        sampled[(departement, naf, size, etab.get("libelle_commune"), etab.get("code_postal"))] += 1
                        break
                if page >= payload.get("total_pages", 0):
                    break
        print(f"departement {departement} done")

    out = Path("reference/customer_profile.csv")
    out.parent.mkdir(exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["departement", "naf_code", "segment", "size_band", "commune", "postal_code",
                         "sampled_count", "total_establishments_dept_naf"])
        for (dep, naf, size, commune, cp), n in sorted(sampled.items()):
            writer.writerow([dep, naf, NAF_SEGMENTS[naf], size, commune, cp, n, totals[(dep, naf)]])
    print(f"{len(sampled)} profile cells, {sum(sampled.values())} establishments sampled -> {out}")


if __name__ == "__main__":
    main()
