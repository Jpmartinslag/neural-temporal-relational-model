"""ECB Bank Lending Survey signal.

Selected series:
    BLS.Q.{country}.ALL.BC.E.SME.B3.ST.S.DINX

This is the diffusion index for credit standards affecting SME enterprise
loans, backward-looking three months. Quarterly observations are averaged to
calendar-year values; the overlay then applies the t-1 lag.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[4]
RAW = BASE / "data/raw/european_panel/ecb/bls_all_test.csv"
OUT = BASE / "data/raw/european_panel/ecb/bls_credit_standards_sme_annual.csv"


def build_credit_standards(countries: list[str]) -> pd.DataFrame:
    if not RAW.exists():
        raise FileNotFoundError(f"Missing ECB BLS raw CSV: {RAW}")

    wanted = {f"BLS.Q.{country}.ALL.BC.E.SME.B3.ST.S.DINX" for country in countries}
    rows = []
    for chunk in pd.read_csv(RAW, usecols=["KEY", "REF_AREA", "TIME_PERIOD", "OBS_VALUE"], chunksize=250_000):
        sub = chunk[chunk["KEY"].isin(wanted)].copy()
        if not sub.empty:
            rows.append(sub)
    if not rows:
        raise ValueError("No ECB BLS SME credit-standard rows found.")

    df = pd.concat(rows, ignore_index=True)
    df["reference_year"] = df["TIME_PERIOD"].astype(str).str[:4].astype(int)
    df["value"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    return (
        df.groupby(["REF_AREA", "reference_year"], as_index=False)["value"]
        .mean()
        .rename(columns={"REF_AREA": "country", "value": "eu_credit_standards"})
        .sort_values(["country", "reference_year"])
        .reset_index(drop=True)
    )


def get_credit_standards(countries: list[str], refresh: bool = False) -> dict[tuple[str, int], float]:
    if refresh or not OUT.exists():
        annual = build_credit_standards(countries)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        annual.to_csv(OUT, index=False)
    else:
        annual = pd.read_csv(OUT)
        missing = set(countries) - set(annual["country"].unique())
        if missing:
            annual = build_credit_standards(sorted(set(countries) | set(annual["country"].unique())))
            OUT.parent.mkdir(parents=True, exist_ok=True)
            annual.to_csv(OUT, index=False)
    annual = annual[annual["country"].isin(countries)].copy()
    return {
        (str(row.country), int(row.reference_year)): float(row.eu_credit_standards)
        for row in annual.itertuples(index=False)
        if pd.notna(row.eu_credit_standards)
    }


def main() -> None:
    annual = build_credit_standards(["FR", "NL", "BE", "PT"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    annual.to_csv(OUT, index=False)
    print("=== ECB BLS SME credit standards ===")
    print(f"saved={OUT}")
    for country, sub in annual.groupby("country"):
        print(
            f"{country}: years={sub['reference_year'].min()}-{sub['reference_year'].max()} "
            f"n={len(sub)}"
        )


if __name__ == "__main__":
    main()
