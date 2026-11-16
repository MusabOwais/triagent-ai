"""Feature-group ablation for the Stage-1 Yale model (ambulance arrivals).
Answers: how much does each info source contribute, and does the score survive without medication lists?"""
import json, re, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

df = pd.read_pickle("data/yale/yale.pkl")
df = df[df.arrivalmode == "ambulance"].reset_index(drop=True)
y = (df.disposition == "Admit").astype(int).values
cols = list(df.columns)
G = {
    "demo": ["age", "gender"],
    "vitals": [c for c in cols if c.startswith("triage_vital")],
    "complaint": [c for c in cols if c.startswith("cc_")],
    "meds": [c for c in cols if c.startswith("meds_")],
    "util": ["n_edvisits", "n_admissions", "n_surgeries", "previousdispo"],
}
named = set(sum(G.values(), [])) | {"esi", "disposition", "dep_name", "arrivalmode", "race", "ethnicity", "lang",
        "religion", "maritalstatus", "employstatus", "insurance_status", "arrivalmonth", "arrivalday", "arrivalhour_bin"}
G["pmh"] = [c for c in cols if c not in named and not c.endswith(("_min", "_max", "_median", "_last", "_npos", "_count"))]

def mat(feats):
    X = df[feats].copy()
    for c in X.columns:
        X[c] = X[c].astype("category") if (X[c].dtype == object or str(X[c].dtype) == "category") \
            else pd.to_numeric(X[c], errors="coerce").astype("float32")
    X.columns = [re.sub(r"[^0-9a-zA-Z_]", "_", c) for c in X.columns]
    return X

idx = np.arange(len(df))
tr, te = train_test_split(idx, test_size=0.2, random_state=0, stratify=y)
tr, va = train_test_split(tr, test_size=0.15, random_state=0, stratify=y[tr])

def run(groups):
    X = mat(sum((G[g] for g in groups), []))
    m = lgb.LGBMClassifier(n_estimators=800, learning_rate=0.05, num_leaves=63, subsample=0.8, subsample_freq=1,
                           colsample_bytree=0.5, verbose=-1)
    m.fit(X.iloc[tr], y[tr], eval_set=[(X.iloc[va], y[va])], callbacks=[lgb.early_stopping(40, verbose=False)])
    p = m.predict_proba(X.iloc[te])[:, 1]
    hv = df.loc[te, G["vitals"]].notna().any(axis=1).values
    return {"auroc": round(roc_auc_score(y[te], p), 3), "auroc_vitals_present": round(roc_auc_score(y[te][hv], p[hv]), 3)}

configs = {
    "vitals_only": ["vitals"],
    "demo+vitals": ["demo", "vitals"],
    "demo+vitals+complaint (what EMT sees, no records)": ["demo", "vitals", "complaint"],
    "+pmh": ["demo", "vitals", "complaint", "pmh"],
    "+pmh+util (no meds)": ["demo", "vitals", "complaint", "pmh", "util"],
    "meds_only": ["meds"],
    "full": ["demo", "vitals", "complaint", "pmh", "util", "meds"],
}
res = {k: run(v) for k, v in configs.items()}
# ESI reference: what a triage nurse's ESI alone achieves (not a model input, just a benchmark)
esi = pd.to_numeric(df.esi, errors="coerce").values[te]
ok = ~np.isnan(esi)
res["reference: ESI alone (nurse triage)"] = {"auroc": round(roc_auc_score(y[te][ok], -esi[ok]), 3)}
json.dump(res, open("outputs/yale_ablation.json", "w"), indent=2)
print(json.dumps(res, indent=2))
