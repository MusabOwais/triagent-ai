"""Stage-1 model (leakage-checked): predict admission for ambulance arrivals from pre-hospital-available Yale features."""
import json, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.model_selection import train_test_split
from sklearn.isotonic import IsotonicRegression
from sklearn.calibration import calibration_curve
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

df = pd.read_pickle("data/yale/yale.pkl")
df = df[df.arrivalmode == "ambulance"].copy()
y = (df.disposition == "Admit").astype(int).values

cols = list(df.columns)
vit = [c for c in cols if c.startswith("triage_vital")]
cc = [c for c in cols if c.startswith("cc_")]
meds = [c for c in cols if c.startswith("meds_")]
util = ["n_edvisits", "n_admissions", "n_surgeries"]
demo = ["age", "gender"]
excl = set(["esi", "disposition", "dep_name", "arrivalmode", "race", "ethnicity", "lang", "religion",
            "maritalstatus", "employstatus", "insurance_status"] + vit + cc + meds + util + demo
           + ["arrivalmonth", "arrivalday", "arrivalhour_bin", "previousdispo"])
# remaining columns after the named groups are the diagnosis-history flags (and any in-visit leak columns we drop)
hist_sfx = ("_min", "_max", "_median", "_last", "_npos", "_count")  # prior-visit labs/vitals/imaging: not available to EMTs
pmh = [c for c in cols if c not in excl and not c.endswith(hist_sfx)]
# meds_* EXCLUDED: 90% of discharged pts (81% of discharged 65+ first-visit pts) have zero recorded meds vs 33% of
# admitted pts -> counts look populated by admission medication reconciliation, i.e. outcome leakage. See yale_ablation.json.
feat = demo + vit + cc + util + pmh + ["previousdispo", "arrivalhour_bin"]

X = df[feat].copy()
for c in X.columns:
    if str(X[c].dtype) == "category" or X[c].dtype == object:
        X[c] = X[c].astype("category")
    else:
        X[c] = pd.to_numeric(X[c], errors="coerce").astype("float32")
import re
X.columns = [re.sub(r"[^0-9a-zA-Z_]", "_", c) for c in X.columns]
X = X.copy()
X["vitals_missing"] = df[vit].isna().all(axis=1).astype(int).values

idx = np.arange(len(X))
tr, te = train_test_split(idx, test_size=0.2, random_state=0, stratify=y)
tr, va = train_test_split(tr, test_size=0.15, random_state=0, stratify=y[tr])

m = lgb.LGBMClassifier(n_estimators=600, learning_rate=0.05, num_leaves=63, subsample=0.8,
                       subsample_freq=1, colsample_bytree=0.5, verbose=-1)
m.fit(X.iloc[tr], y[tr], eval_set=[(X.iloc[va], y[va])], callbacks=[lgb.early_stopping(40, verbose=False)])
pv, pt = m.predict_proba(X.iloc[va])[:, 1], m.predict_proba(X.iloc[te])[:, 1]
iso = IsotonicRegression(out_of_bounds="clip").fit(pv, y[va])
pc = iso.predict(pt)

res = {"n_ambulance": int(len(X)), "n_features": int(X.shape[1]), "admit_rate": float(y.mean()),
       "auroc": roc_auc_score(y[te], pt), "auprc": average_precision_score(y[te], pt),
       "brier_raw": brier_score_loss(y[te], pt), "brier_calibrated": brier_score_loss(y[te], pc),
       "best_iter": int(m.best_iteration_ or 0)}
has_v = (X["vitals_missing"].values[te] == 0)
res["auroc_vitals_present"] = roc_auc_score(y[te][has_v], pt[has_v])
res["auroc_vitals_missing"] = roc_auc_score(y[te][~has_v], pt[~has_v])
sub = {}
for g in ["gender", "race"]:
    for k, ix in df.iloc[te].groupby(g, observed=True).indices.items():
        if len(ix) > 500 and len(set(y[te][ix])) > 1:
            sub[f"{g}={k}"] = round(roc_auc_score(y[te][ix], pt[ix]), 3)
res["subgroup_auroc"] = sub
age = df.age.values[te]
for lo, hi in [(18, 40), (40, 65), (65, 200)]:
    mk = (age >= lo) & (age < hi)
    if len(set(y[te][mk])) > 1:
        sub[f"age {lo}-{hi}"] = round(roc_auc_score(y[te][mk], pt[mk]), 3)
imp = pd.Series(m.booster_.feature_importance("gain"), index=X.columns).sort_values(ascending=False)
res["top_features"] = {k: round(float(v / imp.sum()), 4) for k, v in imp.head(15).items()}
json.dump(res, open("outputs/yale_baseline.json", "w"), indent=2, default=float)

fp, mp = calibration_curve(y[te], pc, n_bins=10)
plt.figure(figsize=(4, 4)); plt.plot([0, 1], [0, 1], "--", c="gray"); plt.plot(mp, fp, "o-")
plt.xlabel("Predicted risk"); plt.ylabel("Observed admit rate"); plt.title("Calibration (test)")
plt.tight_layout(); plt.savefig("outputs/yale_calibration.png", dpi=120)
m.booster_.save_model("outputs/yale_lgbm.txt")
print(json.dumps(res, indent=2, default=float))
