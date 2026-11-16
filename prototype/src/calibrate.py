"""Platt-scale each ECG and CXR class on its VALIDATION set; report test calibration error before/after."""
import json, numpy as np
from sklearn.linear_model import LogisticRegression

ECG = ["NORM", "MI", "STTC", "CD", "HYP"]
CXR = ["Atelectasis", "Cardiomegaly", "Effusion", "Infiltration", "Mass", "Nodule", "Pneumonia", "Pneumothorax",
       "Consolidation", "Edema", "Emphysema", "Fibrosis", "Pleural_Thickening", "Hernia"]
logit = lambda p: np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))

def ece(y, p, bins=10):
    e, edges = 0.0, np.linspace(0, 1, bins + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi) if hi < 1 else (p >= lo)
        if m.any(): e += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(e)

out = {}
for name, classes in [("ecg", ECG), ("cxr", CXR)]:
    pv, yv = np.load(f"outputs/{name}_val_probs.npy"), np.load(f"outputs/{name}_val_labels.npy")
    pt, yt = np.load(f"outputs/{name}_test_probs.npy"), np.load(f"outputs/{name}_test_labels.npy")
    out[name] = {}
    for i, c in enumerate(classes):
        if yv[:, i].sum() < 3:  # too few positives to fit (e.g. Hernia): identity mapping
            out[name][c] = {"a": 1.0, "b": 0.0, "fitted": False}
            continue
        lr = LogisticRegression(C=1e4).fit(logit(pv[:, i])[:, None], yv[:, i])
        a, b = float(lr.coef_[0, 0]), float(lr.intercept_[0])
        pc = 1 / (1 + np.exp(-(a * logit(pt[:, i]) + b)))
        out[name][c] = {"a": round(a, 4), "b": round(b, 4), "fitted": True,
                        "test_ece_before": round(ece(yt[:, i], pt[:, i]), 4), "test_ece_after": round(ece(yt[:, i], pc), 4)}
json.dump(out, open("outputs/calibration.json", "w"), indent=2)
for n in out:
    for c, v in out[n].items():
        if v["fitted"]: print(n, c, "ECE", v["test_ece_before"], "->", v["test_ece_after"])
