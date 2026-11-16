"""Yale ED admission model: training CLI + predict_admission() for the backend.

Train (from the repo root):
    python -m ml.admission train ml/data/yale_slim.parquet            # 40% sample by default
    python -m ml.admission train ml/data/yale_slim.parquet --frac 0.2 # faster
    python -m ml.admission train ... --site-holdout                    # extra: train on 2 sites, test on the 3rd

Use (backend):
    from ml.admission import predict_admission
    predict_admission({...contract features...}, "triage")

Design rules (see README):
* The model sees ONLY the fields in the shared contract (A6) — the same fields at training and at
  prediction time. Yale's ~200 chief-complaint columns are collapsed into our 8 categories with one
  fixed priority order, so training rows look exactly like the one-category rows the app sends.
* No post-triage data, no history, no race/ethnicity/insurance/religion/language as features.
* Split: train 70% / calibration 15% / test 15%. Isotonic calibration is fitted on the calibration
  split only (always applied, so the test set is never used to make a choice). Test is used once.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

try:
    from . import common
except ImportError:  # allows `python admission.py` from inside ml/
    import common

COMPLAINTS = ["chest_pain", "shortness_of_breath", "stroke_signs", "abdominal_pain", "trauma",
              "altered_mental_status", "fever_infection", "other"]

# Priority order when a Yale visit has several complaint columns set: first match wins.
# Keyword patterns are matched against the Yale column name without its "cc_" prefix.
COMPLAINT_PATTERNS = [
    ("stroke_signs", r"stroke|facial|aphasia|slurred|speech|hemipar|^tia$|neurologic"),
    ("chest_pain", r"chest"),
    ("shortness_of_breath", r"breath|dyspn|^sob$|respirat|wheez|asthma|copd"),
    ("altered_mental_status", r"altered|mental|confus|unrespons|letharg|disorient"),
    ("trauma", r"trauma|fall|injur|motorvehicle|mvc|mva|assault|lacerat|fracture|wound|burn|stab|gunshot|bicycle|motorcycle"),
    ("fever_infection", r"fever|infect|sepsis|cellulit|abscess|^uti$|urinarytractinfection|chills"),
    ("abdominal_pain", r"abd|flank|epigastr"),
]

FEATURES_BASE = ["age", "sex_male", "arrival_ambulance",
                 *[f"cc_{c}" for c in COMPLAINTS],
                 "heart_rate", "sbp", "dbp", "resp_rate", "spo2", "temp_c", "on_oxygen"]
FEATURES = {"ambulance": FEATURES_BASE, "triage": FEATURES_BASE + ["esi"]}
MODEL_NAMES = {"ambulance": "yale_xgb_ambulance_v1", "triage": "yale_xgb_triage_v1"}

# Physiologically implausible values become missing (typos in the source data).
PLAUSIBLE = {"heart_rate": (20, 300), "sbp": (40, 300), "dbp": (10, 200), "resp_rate": (3, 80),
             "spo2": (40, 100), "temp_c": (25, 45), "age": (18, 120)}

SENSITIVE = r"race|ethnic|insur|relig|lang|marital|employ"


# --------------------------------------------------------------------------- column detection
def _pick(df, pattern, label, required=True, exclude=None):
    cols = [c for c in df.columns if re.search(pattern, c, re.I)
            and not (exclude and re.search(exclude, c, re.I))]
    if not cols:
        if required:
            sys.exit(f"could not find the {label} column (pattern {pattern!r}). "
                     f"Pass it explicitly with --col {label}=COLUMN")
        return None
    if len(cols) > 1:
        print(f"  note: several {label} candidates {cols[:6]}; using {cols[0]!r} (override with --col)")
    return cols[0]


def detect_columns(df, overrides: dict) -> dict:
    spec = {
        "outcome": (r"^disposition$|dispo", True, r"previous|prior"),
        "esi": (r"^esi$|acuity", True, None),
        "age": (r"^age$|^age_", True, None),
        "sex": (r"^gender$|^sex$", True, None),
        "arrival": (r"^arrivalmode$|arrival_?mode", True, None),
        "heart_rate": (r"vital.*(hr|pulse|heart)", False, None),
        "sbp": (r"vital.*sbp|systolic", False, None),
        "dbp": (r"vital.*dbp|diastolic", False, None),
        "resp_rate": (r"vital.*(rr|resp)", False, None),
        "spo2": (r"vital.*(o2|spo2|sat)$|spo2", False, r"device"),
        "o2_device": (r"o2_?device|oxygen_?device", False, None),
        "temp": (r"vital.*temp|temperature", False, None),
        "site": (r"^dep_name$|^site$|department", False, None),
        "patient_id": (r"(^|_)(mrn|patient_?id|pat_?id|subject_?id)($|_)", False, None),
    }
    cols = {}
    for key, (pat, req, excl) in spec.items():
        cols[key] = overrides.get(key) or _pick(df, pat, key, req, excl)
    cols["complaints"] = [c for c in df.columns if re.match(r"cc_", c, re.I)]
    cols["sensitive"] = [c for c in df.columns if re.search(SENSITIVE, c, re.I)]
    return cols


def complaint_mapping(cc_cols: list[str]) -> dict:
    """Yale complaint column -> our category (columns that match nothing map to 'other')."""
    mapping = {}
    for c in cc_cols:
        name = re.sub(r"^cc_", "", c, flags=re.I).lower()
        cat = "other"
        for category, pat in COMPLAINT_PATTERNS:
            if re.search(pat, name):
                cat = category
                break
        mapping[c] = cat
    return mapping


def _o2_on(v):
    """Oxygen-device column -> 1 (on oxygen), 0 (room air), NaN (unknown). Printed for review."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return np.nan
    s = str(v).strip().lower()
    if s in ("", "nan", "na", "none", "unknown"):
        return np.nan
    if re.search(r"room|^ra$|^0(\.0)?$|^no($|ne)|^false$", s):
        return 0.0
    return 1.0


# --------------------------------------------------------------------------- feature building
def build_training_frame(df, cols: dict, verbose=True):
    import pandas as pd

    out = pd.DataFrame(index=df.index)

    # outcome
    raw = df[cols["outcome"]].astype(str).str.lower()
    y = pd.Series(np.where(raw.str.contains("admit"), 1.0,
                           np.where(raw.str.contains("disch"), 0.0, np.nan)), index=df.index)
    if verbose:
        print("\noutcome values -> label:")
        for v, n in df[cols["outcome"]].value_counts(dropna=False).head(10).items():
            lab = "admit=1" if "admit" in str(v).lower() else "discharge=0" if "disch" in str(v).lower() else "DROPPED"
            print(f"  {v!r:30} {n:>9,}  {lab}")

    out["age"] = pd.to_numeric(df[cols["age"]], errors="coerce")
    sex = df[cols["sex"]].astype(str).str.lower().str[0]
    out["sex_male"] = np.where(sex == "m", 1.0, np.where(sex == "f", 0.0, np.nan))

    arr = df[cols["arrival"]].astype(str).str.lower()
    out["arrival_ambulance"] = np.where(arr.str.contains(r"ambul|ems|paramedic"), 1.0,
                                        np.where(df[cols["arrival"]].isna(), np.nan, 0.0))
    if verbose:
        print("\narrival mode values -> ambulance?")
        for v, n in df[cols["arrival"]].value_counts(dropna=False).head(12).items():
            amb = bool(re.search(r"ambul|ems|paramedic", str(v).lower()))
            print(f"  {v!r:30} {n:>9,}  {'ambulance' if amb else 'not ambulance'}")

    # complaint: one category per visit, by priority order
    mapping = complaint_mapping(cols["complaints"])
    cat = pd.Series("other", index=df.index)
    assigned = pd.Series(False, index=df.index)
    for category, _ in COMPLAINT_PATTERNS:
        src = [c for c, m in mapping.items() if m == category]
        if not src:
            continue
        hit = (df[src].apply(pd.to_numeric, errors="coerce").fillna(0) > 0).any(axis=1) & ~assigned
        cat[hit] = category
        assigned |= hit
    for c in COMPLAINTS:
        out[f"cc_{c}"] = (cat == c).astype(float)
    if verbose:
        print("\ncomplaint category counts (one per visit):")
        for c, n in cat.value_counts().items():
            print(f"  {c:24} {n:>9,}")

    def num(key):
        return pd.to_numeric(df[cols[key]], errors="coerce") if cols.get(key) else pd.Series(np.nan, index=df.index)

    out["heart_rate"], out["sbp"], out["dbp"] = num("heart_rate"), num("sbp"), num("dbp")
    out["resp_rate"], out["spo2"] = num("resp_rate"), num("spo2")
    t = num("temp")
    temp_unit = "F" if t.median() > 50 else "C"
    out["temp_c"] = (t - 32) * 5 / 9 if temp_unit == "F" else t
    if cols.get("o2_device"):
        out["on_oxygen"] = df[cols["o2_device"]].map(_o2_on)
        if verbose:
            print("\noxygen device values -> on_oxygen:")
            for v, n in df[cols["o2_device"]].value_counts(dropna=False).head(12).items():
                print(f"  {v!r:30} {n:>9,}  {_o2_on(v)}")
    else:
        out["on_oxygen"] = np.nan
    out["esi"] = pd.to_numeric(df[cols["esi"]], errors="coerce").where(lambda s: s.between(1, 5))

    for k, (lo, hi) in PLAUSIBLE.items():
        bad = ~out[k].between(lo, hi) & out[k].notna()
        if bad.any() and verbose:
            print(f"  {k}: {int(bad.sum()):,} implausible values set to missing")
        out.loc[bad, k] = np.nan

    if verbose:
        print(f"\ntemperature unit detected: °{temp_unit}" + (" (converted to °C)" if temp_unit == "F" else ""))
        print("missing share per feature:")
        print("  " + ", ".join(f"{k}={out[k].isna().mean():.0%}" for k in FEATURES["triage"] if not k.startswith("cc_")))

    meta = {"complaint_mapping": mapping, "temp_unit_source": temp_unit, "columns": cols}
    return out, y, meta


def features_to_row(features: dict, stage: str) -> np.ndarray:
    """Contract features dict (A6) -> model input row. Same columns and units as training."""
    f = dict(features)
    cc = f.get("complaint_category") or "other"
    if cc not in COMPLAINTS:
        raise ValueError(f"complaint_category must be one of {COMPLAINTS}, got {cc!r}")
    age = f.get("age")
    if age is not None and float(age) < 18:
        raise ValueError("Yale model was trained on adults only (age >= 18)")
    sex = f.get("sex")
    if sex not in ("M", "F", None):
        raise ValueError("sex must be 'M', 'F' or None")
    am = f.get("arrival_mode")
    if am not in ("ambulance", "walk_in", None):
        raise ValueError("arrival_mode must be 'ambulance', 'walk_in' or None")

    def val(k):
        v = f.get(k)
        if v is None:
            return np.nan
        v = float(v)
        lo, hi = PLAUSIBLE.get(k, (-np.inf, np.inf))
        return v if lo <= v <= hi else np.nan

    row = {
        "age": val("age"),
        "sex_male": {"M": 1.0, "F": 0.0}.get(sex, np.nan),
        "arrival_ambulance": {"ambulance": 1.0, "walk_in": 0.0}.get(am, np.nan),
        **{f"cc_{c}": float(c == cc) for c in COMPLAINTS},
        "heart_rate": val("heart_rate"), "sbp": val("sbp"), "dbp": val("dbp"),
        "resp_rate": val("resp_rate"), "spo2": val("spo2"), "temp_c": val("temp_c"),
        "on_oxygen": np.nan if f.get("on_oxygen") is None else float(bool(f["on_oxygen"])),
        "esi": np.nan if f.get("esi") is None else float(f["esi"]),
    }
    return np.array([[row[k] for k in FEATURES[stage]]], dtype=float)


# --------------------------------------------------------------------------- baseline: partial NEWS2
def news2_partial(fr) -> np.ndarray:
    """NEWS2 from the 6 vitals Yale has (no consciousness). Used only as a comparison baseline."""
    def band(x, rules):
        pts = np.full(len(x), np.nan)
        for cond, p in rules:
            pts = np.where(np.isnan(pts) & cond(x), p, pts)
        return np.where(np.isnan(x), np.nan, pts)

    rr = fr["resp_rate"].to_numpy(float)
    sp = fr["spo2"].to_numpy(float)
    sbp = fr["sbp"].to_numpy(float)
    hr = fr["heart_rate"].to_numpy(float)
    t = fr["temp_c"].to_numpy(float)
    ox = fr["on_oxygen"].to_numpy(float)
    parts = [
        band(rr, [(lambda x: x <= 8, 3), (lambda x: x <= 11, 1), (lambda x: x <= 20, 0), (lambda x: x <= 24, 2), (lambda x: x > 24, 3)]),
        band(sp, [(lambda x: x <= 91, 3), (lambda x: x <= 93, 2), (lambda x: x <= 95, 1), (lambda x: x > 95, 0)]),
        np.where(np.isnan(ox), np.nan, ox * 2),
        band(sbp, [(lambda x: x <= 90, 3), (lambda x: x <= 100, 2), (lambda x: x <= 110, 1), (lambda x: x <= 219, 0), (lambda x: x > 219, 3)]),
        band(hr, [(lambda x: x <= 40, 3), (lambda x: x <= 50, 1), (lambda x: x <= 90, 0), (lambda x: x <= 110, 1), (lambda x: x <= 130, 2), (lambda x: x > 130, 3)]),
        band(np.round(t, 1), [(lambda x: x <= 35.0, 3), (lambda x: x <= 36.0, 1), (lambda x: x <= 38.0, 0), (lambda x: x <= 39.0, 1), (lambda x: x > 39.0, 2)]),
    ]
    stack = np.vstack(parts)
    total = np.nansum(stack, axis=0)
    total[np.isnan(stack).all(axis=0)] = np.nan
    return total


# --------------------------------------------------------------------------- training
def _fit_xgb(X, y, seed=42):
    import xgboost as xgb
    from sklearn.model_selection import train_test_split

    Xtr, Xes, ytr, yes = train_test_split(X, y, test_size=0.1, stratify=y, random_state=seed)
    model = xgb.XGBClassifier(
        n_estimators=2000, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.8,
        min_child_weight=5, tree_method="hist", eval_metric="logloss", early_stopping_rounds=50,
        n_jobs=-1, random_state=seed)
    model.fit(Xtr, ytr, eval_set=[(Xes, yes)], verbose=False)
    print(f"  trees used (early stopping): {model.best_iteration + 1}")
    return model


def _calibration_table(y, p, bins=10):
    edges = np.quantile(p, np.linspace(0, 1, bins + 1))
    idx = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, bins - 1)
    return [{"mean_predicted": float(p[idx == b].mean()), "observed_rate": float(y[idx == b].mean()),
             "n": int((idx == b).sum())} for b in range(bins) if (idx == b).any()]


def _evaluate(y, p, label):
    from sklearn.metrics import brier_score_loss
    res = common.auc_with_ci(y, p)
    res["prevalence"] = float(np.mean(y))
    res["brier"] = brier_score_loss(y, p)
    res["at_0.8"] = common.binary_report(y, p, 0.8)
    res["at_0.5"] = common.binary_report(y, p, 0.5)
    print(f"  {label:38} AUC {res['auc']:.3f} (95% CI {res['ci95'][0]:.3f}-{res['ci95'][1]:.3f})  "
          f"n={res['n']:,}  @0.8 sens {res['at_0.8']['sensitivity'] or 0:.2f} ppv {res['at_0.8']['ppv'] or 0:.2f}")
    return res


def train(path: Path, frac: float, overrides: dict, site_holdout: bool, seed=42):
    import pandas as pd
    from sklearn.isotonic import IsotonicRegression
    from sklearn.model_selection import GroupShuffleSplit, train_test_split

    t0 = time.time()
    if path.suffix.lower() == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix.lower() in (".rdata", ".rda", ".rds"):
        import pyreadr
        res = pyreadr.read_r(str(path))
        df = res[max(res, key=lambda k: res[k].size)]
    else:
        df = pd.read_csv(path, low_memory=False)
    print(f"loaded {len(df):,} rows x {df.shape[1]} cols in {time.time() - t0:.0f}s")

    cols = detect_columns(df, overrides)
    print("\ncolumns used:")
    for k, v in cols.items():
        if k == "complaints":
            print(f"  complaints: {len(v)} cc_ columns")
        else:
            print(f"  {k:12} -> {v}")
    if not cols["complaints"]:
        sys.exit("no cc_ complaint columns found; tell Role 1 the complaint column names")

    if frac < 1:
        df = df.sample(frac=frac, random_state=seed)
        print(f"\nusing a {frac:.0%} random sample: {len(df):,} visits (paper: performance plateaus by 50%)")

    X, y, meta = build_training_frame(df, cols)
    keep = y.notna() & X["age"].notna()
    X, y, df = X[keep], y[keep].astype(int), df[keep]
    print(f"\nvisits with a usable label: {len(y):,}; admitted {y.mean():.1%}")

    # train 70 / calib 15 / test 15 — by patient if an ID exists
    idx = np.arange(len(y))
    if cols["patient_id"]:
        g = df[cols["patient_id"]].to_numpy()
        tr, rest = next(GroupShuffleSplit(1, test_size=0.3, random_state=seed).split(idx, groups=g))
        ca_i, te_i = next(GroupShuffleSplit(1, test_size=0.5, random_state=seed).split(rest, groups=g[rest]))
        ca, te = rest[ca_i], rest[te_i]
        split_desc = f"70/15/15 by patient ID ({cols['patient_id']})"
    else:
        tr, rest = train_test_split(idx, test_size=0.3, stratify=y, random_state=seed)
        ca, te = train_test_split(rest, test_size=0.5, stratify=y.iloc[rest], random_state=seed)
        split_desc = ("70/15/15 random by visit, stratified. No patient ID in the data, so repeat visits by "
                      "the same patient can fall in train and test (results slightly optimistic).")
    print(f"split: {split_desc}\n  train {len(tr):,}  calib {len(ca):,}  test {len(te):,}")

    common.ARTIFACTS.mkdir(exist_ok=True)
    yte = y.iloc[te].to_numpy()
    amb_mask = X["arrival_ambulance"].iloc[te].to_numpy() == 1
    results, bundle = {}, {"features": FEATURES, "model_names": MODEL_NAMES, **meta,
                           "trained_rows": int(len(tr)), "split": split_desc}

    for stage in ("ambulance", "triage"):
        print(f"\n== {stage} model ({len(FEATURES[stage])} features)")
        f = FEATURES[stage]
        model = _fit_xgb(X[f].iloc[tr].to_numpy(), y.iloc[tr].to_numpy(), seed)
        p_ca = model.predict_proba(X[f].iloc[ca].to_numpy())[:, 1]
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(p_ca, y.iloc[ca])
        p_raw = model.predict_proba(X[f].iloc[te].to_numpy())[:, 1]
        p_te = iso.predict(p_raw)
        r = _evaluate(yte, p_te, f"{stage} (all arrivals, calibrated)")
        r["auc_uncalibrated"] = common.auc_with_ci(yte, p_raw, n_boot=0)["auc"]
        from sklearn.metrics import brier_score_loss
        r["brier_uncalibrated"] = brier_score_loss(yte, p_raw)
        r["calibration"] = "isotonic (fitted on calibration split)"
        r["calibration_table_test"] = _calibration_table(yte, p_te)
        r["model"] = MODEL_NAMES[stage]
        r["features"] = f
        r["split"] = split_desc
        # subgroup check (report only — sensitive columns are never features)
        sub = {}
        sexes = X["sex_male"].iloc[te].to_numpy()
        for name, m in [("female", sexes == 0), ("male", sexes == 1)]:
            sub[f"sex_{name}"] = common.auc_with_ci(yte[m], p_te[m], n_boot=0)
        ages = X["age"].iloc[te].to_numpy()
        for lo, hi in [(18, 45), (45, 65), (65, 80), (80, 200)]:
            m = (ages >= lo) & (ages < hi)
            sub[f"age_{lo}_{hi if hi < 200 else 'plus'}"] = common.auc_with_ci(yte[m], p_te[m], n_boot=0)
        for sc in cols["sensitive"]:
            if re.search(r"race|ethnic", sc, re.I):
                vals = df[sc].iloc[te].astype(str).to_numpy()
                for v in pd.Series(vals).value_counts().head(6).index:
                    m = vals == v
                    if m.sum() >= 200:
                        sub[f"{sc}={v}"] = common.auc_with_ci(yte[m], p_te[m], n_boot=0)
        r["subgroups_auc"] = sub
        results[f"yale_{stage}"] = r
        results[f"yale_{stage}_ambulance_arrivals_only"] = _evaluate(
            yte[amb_mask], p_te[amb_mask], f"{stage} (ambulance arrivals only)")

        model.get_booster().save_model(str(common.ARTIFACTS / f"yale_{stage}.ubj"))
        bundle[f"isotonic_{stage}"] = {"x": iso.X_thresholds_.tolist(), "y": iso.y_thresholds_.tolist()}

    # comparison baselines on the same test rows
    esi_te = X["esi"].iloc[te].to_numpy()
    print("\n== baselines (same test rows)")
    base = {"esi_only": common.auc_with_ci(yte, -esi_te),
            "news2_partial_6_of_7": common.auc_with_ci(yte, news2_partial(X.iloc[te]))}
    for k, v in base.items():
        if v["auc"] is not None:
            print(f"  {k:38} AUC {v['auc']:.3f} (n={v['n']:,})")
    base["note"] = ("ESI alone = the triage nurse's acuity score as a predictor. Partial NEWS2 uses 6 of 7 "
                    "parameters (Yale has no consciousness field).")
    results["yale_baselines"] = base

    if site_holdout and cols["site"]:
        results["yale_site_holdout"] = _site_holdout(X, y, df[cols["site"]], seed)

    (common.ARTIFACTS / "yale_meta.json").write_text(json.dumps(common._clean(bundle), indent=1))
    (common.ARTIFACTS / "complaint_mapping.json").write_text(
        json.dumps({c: m for c, m in sorted(meta["complaint_mapping"].items(), key=lambda kv: kv[1])}, indent=1))

    # Headline keys follow the B5 contract; extra keys are additive.
    results["yale_ambulance_arrivals_only"] = results.pop("yale_ambulance_ambulance_arrivals_only")
    for k, v in results.items():
        common.update_metrics(k, v, notes=[
            "Yale models use only contract fields (age, sex, arrival mode, 8 complaint categories, triage vitals, "
            "+ESI for triage). The paper's 0.87/0.92 used many more variables and is not comparable.",
            "Ambulance-stage model uses triage vitals as a stand-in for paramedic vitals.",
        ])
    print(f"\ndone in {time.time() - t0:.0f}s. artifacts in {common.ARTIFACTS}")


def _site_holdout(X, y, site, seed):
    from sklearn.isotonic import IsotonicRegression
    out = {}
    f = FEATURES["triage"]
    for s in site.dropna().unique():
        te = (site == s).to_numpy()
        tr = ~te
        idx = np.where(tr)[0]
        rng = np.random.default_rng(seed)
        rng.shuffle(idx)
        cut = int(len(idx) * 0.85)
        m = _fit_xgb(X[f].iloc[idx[:cut]].to_numpy(), y.iloc[idx[:cut]].to_numpy(), seed)
        iso = IsotonicRegression(out_of_bounds="clip").fit(
            m.predict_proba(X[f].iloc[idx[cut:]].to_numpy())[:, 1], y.iloc[idx[cut:]])
        p = iso.predict(m.predict_proba(X[f].iloc[te].to_numpy())[:, 1])
        out[f"test_site={s}"] = _evaluate(y[te].to_numpy(), p, f"triage, trained without site {s}")
    return out


# --------------------------------------------------------------------------- inference
_MODELS: dict = {}
_META: dict = {}


def _load():
    if _MODELS:
        return
    meta_p = common.ARTIFACTS / "yale_meta.json"
    if not meta_p.exists():
        return  # not trained yet; predict_admission raises a clear error
    import xgboost as xgb
    _META.update(json.loads(meta_p.read_text()))
    for stage in ("ambulance", "triage"):
        b = xgb.Booster()
        b.load_model(str(common.ARTIFACTS / f"yale_{stage}.ubj"))
        b.set_param({"nthread": 1})
        _MODELS[stage] = b


def _label(feat, v, cc):
    if feat.startswith("cc_"):
        return f"Complaint: {cc.replace('_', ' ')}"
    return {
        "age": lambda: f"Age {v:.0f}",
        "sex_male": lambda: "Male" if v == 1 else "Female",
        "arrival_ambulance": lambda: "Arrived by ambulance" if v == 1 else "Walk-in arrival",
        "heart_rate": lambda: f"Heart rate {v:.0f}",
        "sbp": lambda: f"Systolic BP {v:.0f}",
        "dbp": lambda: f"Diastolic BP {v:.0f}",
        "resp_rate": lambda: f"Resp rate {v:.0f}",
        "spo2": lambda: f"Oxygen {v:.0f}%",
        "temp_c": lambda: f"Temp {v:.1f} °C",
        "on_oxygen": lambda: "On supplemental oxygen" if v == 1 else "On room air",
        "esi": lambda: f"ESI {v:.0f}",
    }[feat]()


def predict_admission(features: dict, stage: str) -> dict:
    """Contract A6. stage 'triage' without an ESI falls back to the ambulance model (stage says which ran)."""
    import xgboost as xgb

    if stage not in ("ambulance", "triage"):
        raise ValueError("stage must be 'ambulance' or 'triage'")
    _load()
    if not _MODELS:
        raise RuntimeError("Yale models not trained yet: run `python -m ml.admission train ...`")
    if stage == "triage" and features.get("esi") is None:
        stage = "ambulance"
    row = features_to_row(features, stage)
    dm = xgb.DMatrix(row, feature_names=None, missing=np.nan)
    b = _MODELS[stage]
    margin = float(b.predict(dm, output_margin=True)[0])
    raw = 1 / (1 + math.exp(-margin))
    iso = _META[f"isotonic_{stage}"]
    prob = float(np.interp(raw, iso["x"], iso["y"]))

    contribs = b.predict(dm, pred_contribs=True)[0][:-1]  # last value is the bias term
    feats = FEATURES[stage]
    cc = features.get("complaint_category") or "other"
    merged: dict[str, tuple[float, float]] = {}
    for name, c, v in zip(feats, contribs, row[0]):
        if np.isnan(v):
            continue  # never explain with a value nobody entered
        key = "cc" if name.startswith("cc_") else name
        prev = merged.get(key, (0.0, v))
        merged[key] = (prev[0] + float(c), v if not name.startswith("cc_") else 1.0)
    ranked = sorted(merged.items(), key=lambda kv: -abs(kv[1][0]))
    top = [(k, c, v) for k, (c, v) in ranked if abs(c) >= 0.05][:3]
    top.sort(key=lambda t: (t[1] < 0, -abs(t[1])))  # 'up' reasons first
    reasons = [{"label": _label("cc_" if k == "cc" else k, v, cc), "direction": "up" if c > 0 else "down"}
               for k, c, v in top]
    return {"probability": round(prob, 3), "stage": stage, "model": MODEL_NAMES[stage], "top_reasons": reasons}


_load()  # load once at import (silently skipped until trained)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("path", type=Path)
    t.add_argument("--frac", type=float, default=0.4)
    t.add_argument("--col", action="append", default=[], help="override a detected column, e.g. --col esi=acuity")
    t.add_argument("--site-holdout", action="store_true")
    d = sub.add_parser("demo", help="run predict_admission on two example patients")
    args = ap.parse_args()
    if args.cmd == "train":
        overrides = dict(kv.split("=", 1) for kv in args.col)
        train(args.path, args.frac, overrides, args.site_holdout)
    else:
        ex = {"age": 67, "sex": "M", "arrival_mode": "ambulance", "complaint_category": "chest_pain",
              "heart_rate": 112, "sbp": 105, "dbp": 70, "resp_rate": 22, "spo2": 94, "temp_c": 37.2,
              "on_oxygen": False, "esi": 2}
        for st in ("ambulance", "triage"):
            t0 = time.perf_counter()
            r = predict_admission(ex, st)
            print(f"{st}: {r}  ({(time.perf_counter() - t0) * 1000:.1f} ms)")


if __name__ == "__main__":
    main()
