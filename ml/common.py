"""Small helpers shared by the three model modules (paths, metrics.json, metric maths)."""
import json
from pathlib import Path

import numpy as np

ML_DIR = Path(__file__).resolve().parent
ARTIFACTS = ML_DIR / "artifacts"
DEMO_DIR = ML_DIR / "demo_assets"
METRICS_PATH = ML_DIR / "metrics.json"
DEMO_JSON = ML_DIR / "demo_assets.json"

AI_NOTE = "AI flag, not a diagnosis"

BASE_NOTES = [
    "Datasets are from different patients; no combined model. Scores are joined by written rules shown on screen.",
    "All numbers are measured on held-out data by the scripts in ml/; none are copied from papers.",
]


def _clean(o):
    """Make numpy types JSON-safe and round floats for readability."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else round(float(o), 4)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def update_metrics(key: str, value: dict, notes: list[str] | None = None) -> None:
    """Merge one model's measured results into ml/metrics.json (other keys are kept)."""
    data = json.loads(METRICS_PATH.read_text()) if METRICS_PATH.exists() else {}
    data[key] = _clean(value)
    all_notes = data.get("notes", [])
    for n in BASE_NOTES + (notes or []):
        if n not in all_notes:
            all_notes.append(n)
    data["notes"] = all_notes
    METRICS_PATH.write_text(json.dumps(data, indent=2) + "\n")
    print(f"metrics.json updated: {key}")


def binary_report(y_true, prob, threshold: float) -> dict:
    """Sensitivity / specificity / PPV at one threshold, plus what share of patients get flagged."""
    y = np.asarray(y_true).astype(int)
    p = np.asarray(prob) >= threshold
    tp = int((p & (y == 1)).sum())
    fp = int((p & (y == 0)).sum())
    fn = int((~p & (y == 1)).sum())
    tn = int((~p & (y == 0)).sum())
    return {
        "threshold": threshold,
        "sensitivity": tp / (tp + fn) if tp + fn else None,
        "specificity": tn / (tn + fp) if tn + fp else None,
        "ppv": tp / (tp + fp) if tp + fp else None,
        "flagged_fraction": (tp + fp) / len(y) if len(y) else None,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def auc_with_ci(y_true, score, n_boot: int = 200, seed: int = 0) -> dict:
    """ROC AUC with a percentile bootstrap 95% CI. Returns n and number of positives too."""
    from sklearn.metrics import roc_auc_score

    y = np.asarray(y_true).astype(int)
    s = np.asarray(score, dtype=float)
    ok = np.isfinite(s)
    y, s = y[ok], s[ok]
    out = {"n": int(len(y)), "n_pos": int(y.sum())}
    if y.min() == y.max():
        out.update(auc=None, ci95=None)
        return out
    out["auc"] = roc_auc_score(y, s)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].min() != y[idx].max():
            boots.append(roc_auc_score(y[idx], s[idx]))
    out["ci95"] = ([float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
                   if boots else None)
    return out


def youden_threshold(y_true, prob) -> float:
    """Threshold that maximises sensitivity + specificity - 1 (chosen on a tuning set only)."""
    from sklearn.metrics import roc_curve

    fpr, tpr, thr = roc_curve(np.asarray(y_true).astype(int), np.asarray(prob))
    i = int(np.argmax(tpr - fpr))
    return float(min(thr[i], 1.0))
