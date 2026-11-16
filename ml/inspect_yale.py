"""Step 1 — inspect the Yale ED admission file before we write any training code.

Usage:
    python inspect_yale.py PATH_TO_YALE_FILE            # .rdata / .RData / .csv / .parquet
    python inspect_yale.py PATH --slim data/yale_slim.parquet   # also save only the columns we need

Prints: shape, column groups, the candidate outcome/ESI/arrival/age/sex/vitals/complaint/ID
columns, their values and ranges (temperature units, oxygen device), and missingness.
It does not train anything and does not decide anything; we read the output together.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd


def load(path: Path) -> pd.DataFrame:
    suf = path.suffix.lower()
    if suf in (".rdata", ".rda", ".rds"):
        import pyreadr  # loads the whole file; needs several GB of RAM for the full Yale set

        res = pyreadr.read_r(str(path))
        print(f"R objects in file: {list(res.keys())}")
        name = max(res, key=lambda k: res[k].shape[0] * res[k].shape[1])
        print(f"using largest object: {name!r}")
        return res[name]
    if suf == ".parquet":
        return pd.read_parquet(path)
    if suf in (".csv", ".gz"):
        return pd.read_csv(path, low_memory=False)
    sys.exit(f"don't know how to read {suf}")


# Patterns are guesses from the paper; we confirm from the printout, never assume.
CANDIDATES = {
    "outcome": r"dispo|admit|outcome",
    "esi": r"^esi$|acuity|triage_level",
    "arrival": r"arriv",
    "age": r"^age",
    "sex": r"gender|^sex",
    "vitals": r"vital|^triage_",
    "complaint": r"^cc_|complaint",
    "patient_id": r"(^|_)(id|mrn|pat|patient)(_|$)",
    "site": r"dep_name|site|department|^ed$",
    "prior_visits": r"^n_|previous|prior",
    "SENSITIVE_do_not_use": r"race|ethnic|insur|relig|lang|marital|employ",
}


def show_values(s: pd.Series, n=12):
    if pd.api.types.is_numeric_dtype(s) and s.nunique() > 15:
        d = s.describe(percentiles=[0.01, 0.5, 0.99])
        print(f"      numeric  min={d['min']:.4g} p1={d['1%']:.4g} median={d['50%']:.4g} "
              f"p99={d['99%']:.4g} max={d['max']:.4g}")
    else:
        vc = s.value_counts(dropna=False).head(n)
        print("      " + ", ".join(f"{k!r}: {v}" for k, v in vc.items()))
    print(f"      missing: {s.isna().mean():.1%}  dtype: {s.dtype}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--slim", type=Path, help="write a parquet with only the needed columns")
    args = ap.parse_args()

    df = load(args.path)
    print(f"\nSHAPE: {df.shape[0]:,} rows x {df.shape[1]:,} columns")
    print(f"memory: {df.memory_usage(deep=True).sum() / 1e9:.2f} GB")

    prefixes = Counter(re.split(r"[_.]", c)[0] for c in df.columns)
    print("\nCOLUMN GROUPS (prefix: count):")
    print("  " + ", ".join(f"{p}:{n}" for p, n in prefixes.most_common(40)))

    found = {}
    for label, pat in CANDIDATES.items():
        cols = [c for c in df.columns if re.search(pat, c, re.I)]
        found[label] = cols
        print(f"\n== {label}: {len(cols)} column(s)")
        if label == "complaint":
            print(f"   first 40: {cols[:40]}")
            if cols:
                tops = df[cols].apply(pd.to_numeric, errors="coerce").sum().sort_values(ascending=False)
                print("   most common:", ", ".join(f"{c}={int(v):,}" for c, v in tops.head(25).items()))
            continue
        for c in cols[:25]:
            print(f"   {c}")
            show_values(df[c])

    # Temperature units: Fahrenheit medians sit around 98, Celsius around 37.
    for c in df.columns:
        if re.search(r"temp", c, re.I) and pd.api.types.is_numeric_dtype(df[c]):
            med = df[c].median()
            unit = "looks like °F" if med > 50 else "looks like °C"
            print(f"\nTEMPERATURE {c}: median {med:.2f} -> {unit}")

    if args.slim:
        keep = sorted(set(sum((v for k, v in found.items() if k != "SENSITIVE_do_not_use"), [])))
        # sensitive columns are saved separately-labelled only for the subgroup check, never as features
        keep += found["SENSITIVE_do_not_use"]
        args.slim.parent.mkdir(parents=True, exist_ok=True)
        df[keep].to_parquet(args.slim, index=False)
        print(f"\nwrote {args.slim} with {len(keep)} columns")


if __name__ == "__main__":
    main()
