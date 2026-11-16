"""Ambulance Vitals Scorecard: an explicit, portable formula trained on Yale ambulance arrivals.

Uses ONLY inputs an ambulance crew records: age, sex, HR, SBP, DBP, RR, SpO2, supplemental O2, temperature
(Model A), plus the chief complaint (Model B). Vitals are binned (clinical cut-points, NEWS2-style) and fit with
L2-regularised logistic regression, so the trained model IS a formula:

    logit(p) = intercept + sum(coefficient of each bin the patient falls in)
    score    = 1 + round(99 * p)

Benchmarks on the same held-out test set: LightGBM on the same raw inputs (upper bound for these inputs) and NEWS2
computed from the same vitals (published clinical standard; consciousness unavailable in Yale so scored as alert)."""
import json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.model_selection import train_test_split
from sklearn.calibration import calibration_curve

df = pd.read_pickle("data/yale/yale.pkl")
df = df[(df.arrivalmode == "ambulance") & (df.age >= 18)].reset_index(drop=True)
num = lambda c: pd.to_numeric(df[c], errors="coerce")
V = pd.DataFrame({"age": num("age"), "male": (df.gender == "Male").astype(int), "hr": num("triage_vital_hr"),
                  "sbp": num("triage_vital_sbp"), "dbp": num("triage_vital_dbp"), "rr": num("triage_vital_rr"),
                  "spo2": num("triage_vital_o2"), "o2": num("triage_vital_o2_device"), "temp_f": num("triage_vital_temp")})
keep = V[["hr", "sbp", "rr"]].notna().all(axis=1).values  # core vitals measured (an ambulance always has these)
V, df = V[keep].reset_index(drop=True), df[keep].reset_index(drop=True)
y = (df.disposition == "Admit").astype(int).values

# Bins: (label, lo, hi) inclusive; the reference (normal) bin gets no column -> coefficient 0.
BINS = {
    "age":    [("40-54", 40, 54), ("55-64", 55, 64), ("65-74", 65, 74), ("75-84", 75, 84), ("85+", 85, 200)],  # ref 18-39
    "hr":     [("<=50", 0, 50), ("91-110", 91, 110), ("111-130", 111, 130), (">=131", 131, 400)],               # ref 51-90
    "sbp":    [("<=90", 0, 90), ("91-100", 91, 100), ("101-110", 101, 110), ("160-199", 160, 199), (">=200", 200, 400)],  # ref 111-159
    "dbp":    [("<=50", 0, 50), (">=110", 110, 300)],                                                           # ref 51-109
    "rr":     [("<=11", 0, 11), ("21-24", 21, 24), (">=25", 25, 100)],                                          # ref 12-20
    "spo2":   [("<=91", 0, 91), ("92-93", 92, 93), ("94-95", 94, 95)],                                          # ref >=96
    "temp_f": [("<=95.0", 0, 95.0), ("95.1-96.8", 95.1, 96.8), ("100.5-102.2", 100.5, 102.2), (">=102.3", 102.3, 120)],  # ref 96.9-100.4
}
REF = {"age": "18-39", "hr": "51-90", "sbp": "111-159", "dbp": "51-109", "rr": "12-20", "spo2": ">=96", "temp_f": "96.9-100.4"}

def design(V, cc=None):
    X = {"male": V.male.values, "supplemental_o2": V.o2.fillna(0).values}
    for v, bins in BINS.items():
        x = V[v].values
        for lab, lo, hi in bins:
            X[f"{v} {lab}"] = ((x >= lo) & (x <= hi)).astype(int)
    for v in ["spo2", "temp_f"]:  # missing in Yale only; in the field these are always measured
        X[f"{v} not recorded"] = np.isnan(V[v].values).astype(int)
    X = pd.DataFrame(X)
    return X if cc is None else pd.concat([X, cc], axis=1)

# Chief complaint: the 25 most common ambulance complaints in TRAIN become indicators; everything else is reference.
idx = np.arange(len(V))
tr, te = train_test_split(idx, test_size=0.2, random_state=0, stratify=y)
tr, va = train_test_split(tr, test_size=0.15, random_state=0, stratify=y[tr])
ccols = [c for c in df.columns if c.startswith("cc_")]
C = df[ccols].apply(pd.to_numeric, errors="coerce").fillna(0).clip(0, 1).astype(int)
top_cc = C.iloc[tr].sum().sort_values(ascending=False).head(25).index.tolist()
CC = C[top_cc].rename(columns=lambda c: "complaint: " + c[3:])

def news2(V):
    s = np.zeros(len(V))
    rr, sp, sbp, hr, t = V.rr.values, V.spo2.values, V.sbp.values, V.hr.values, (V.temp_f.values - 32) * 5 / 9
    s += np.select([rr <= 8, rr <= 11, rr <= 20, rr <= 24], [3, 1, 0, 2], 3)
    s += np.select([np.isnan(sp), sp <= 91, sp <= 93, sp <= 95], [0, 3, 2, 1], 0)
    s += 2 * V.o2.fillna(0).values
    s += np.select([sbp <= 90, sbp <= 100, sbp <= 110, sbp <= 219], [3, 2, 1, 0], 3)
    s += np.select([hr <= 40, hr <= 50, hr <= 90, hr <= 110, hr <= 130], [3, 1, 0, 1, 2], 3)
    s += np.select([np.isnan(t), t <= 35.0, t <= 36.0, t <= 38.0, t <= 39.0], [0, 3, 1, 0, 1], 2)
    return s

def boot_ci(yt, p, n=300, seed=0):
    r = np.random.default_rng(seed); a = []
    for _ in range(n):
        i = r.integers(0, len(yt), len(yt)); a.append(roc_auc_score(yt[i], p[i]))
    return [round(float(np.percentile(a, 2.5)), 3), round(float(np.percentile(a, 97.5)), 3)]

out = {"population": "Yale ED visits, ambulance arrival, age>=18, HR/SBP/RR recorded", "n": int(len(V)),
       "n_train": len(tr), "n_val": len(va), "n_test": len(te), "admit_rate": round(float(y.mean()), 3)}
for name, X in {"A_vitals_only": design(V), "B_vitals_plus_complaint": design(V, CC)}.items():
    best = None
    for Cr in [0.01, 0.1, 1.0]:  # regularisation picked on validation only
        lr = LogisticRegression(C=Cr, max_iter=3000).fit(X.iloc[tr], y[tr])
        a = roc_auc_score(y[va], lr.predict_proba(X.iloc[va])[:, 1])
        if best is None or a > best[0]: best = (a, Cr, lr)
    _, Cr, lr = best
    p = lr.predict_proba(X.iloc[te])[:, 1]
    fp, mp = calibration_curve(y[te], p, n_bins=10)
    coef = dict(zip(X.columns, np.round(lr.coef_[0], 3).tolist()))
    out[name] = {"C": Cr, "test_auroc": round(roc_auc_score(y[te], p), 3), "test_auroc_95ci": boot_ci(y[te], p),
                 "test_brier": round(brier_score_loss(y[te], p), 4),
                 "max_calibration_gap": round(float(np.max(np.abs(fp - mp))), 3),
                 "intercept": round(float(lr.intercept_[0]), 3), "coefficients": coef,
                 "points_x10": {k: int(round(v * 10)) for k, v in coef.items()}}
    # benchmark: same raw inputs, flexible model
    raw = pd.concat([V, CC], axis=1) if name.startswith("B") else V.copy()
    raw.columns = [c.replace(": ", "_").replace(" ", "_") for c in raw.columns]
    g = lgb.LGBMClassifier(n_estimators=800, learning_rate=0.05, num_leaves=31, verbose=-1)
    g.fit(raw.iloc[tr], y[tr], eval_set=[(raw.iloc[va], y[va])], callbacks=[lgb.early_stopping(40, verbose=False)])
    out[name]["benchmark_lightgbm_same_inputs_auroc"] = round(roc_auc_score(y[te], g.predict_proba(raw.iloc[te])[:, 1]), 3)
    # subgroup check
    sub = {}
    for k, ix in df.iloc[te].groupby("race", observed=True).indices.items():
        if len(ix) > 500: sub[f"race={k}"] = round(roc_auc_score(y[te][ix], p[ix]), 3)
    for k, ix in df.iloc[te].groupby("gender", observed=True).indices.items():
        sub[f"sex={k}"] = round(roc_auc_score(y[te][ix], p[ix]), 3)
    out[name]["subgroup_auroc"] = sub
n2 = news2(V.iloc[te])
out["benchmark_NEWS2_same_vitals_auroc"] = round(roc_auc_score(y[te], n2), 3)
out["reference_bins"] = REF
out["bins"] = {k: [b[0] for b in v] for k, v in BINS.items()}
out["top_complaints"] = top_cc
json.dump(out, open("outputs/vitals_scorecard.json", "w"), indent=2)
print(json.dumps({k: v for k, v in out.items() if k not in ("bins", "top_complaints")}, indent=2))
