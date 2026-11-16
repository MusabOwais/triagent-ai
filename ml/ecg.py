"""PTB-XL ECG flag: training CLI + flag_ecg() for the backend.

Train (from the repo root):
    python -m ml.ecg prepare --ptbxl-dir PATH_TO_PTBXL      # read 100 Hz records once -> ml/data/ptbxl_100hz.npz
    python -m ml.ecg train                                  # 1D CNN (default)
    python -m ml.ecg train --model gbm                      # fallback: per-lead summary features + XGBoost

PATH_TO_PTBXL contains ptbxl_database.csv, scp_statements.csv and records100/.

Label: normal = diagnostic superclass NORM only; abnormal = any of MI, STTC, CD, HYP (also when NORM is
listed alongside). Records with no diagnostic statement are dropped.
Split: official folds — 1-8 train, 9 validation (epoch + threshold), 10 test (reported once).
PTB-XL folds already keep each patient in one fold.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import time
from pathlib import Path

import numpy as np

try:
    from . import common
except ImportError:
    import common

CACHE = common.ML_DIR / "data" / "ptbxl_100hz.npz"
CONFIG_PATH = common.ARTIFACTS / "ecg_config.json"
ABNORMAL_CLASSES = {"MI", "STTC", "CD", "HYP"}
MODEL_NAMES = {"cnn": "ptbxl_cnn_v1", "gbm": "ptbxl_gbm_v1"}


# --------------------------------------------------------------------------- data
def prepare(ptbxl_dir: Path):
    import pandas as pd
    import wfdb

    db = pd.read_csv(ptbxl_dir / "ptbxl_database.csv", index_col="ecg_id")
    scp = pd.read_csv(ptbxl_dir / "scp_statements.csv", index_col=0)
    diag = scp[scp["diagnostic"] == 1]["diagnostic_class"].to_dict()

    def superclasses(codes):
        return sorted({diag[c] for c in ast.literal_eval(codes) if c in diag})

    db["superclasses"] = db["scp_codes"].apply(superclasses)
    db = db[db["superclasses"].str.len() > 0]
    db["abnormal"] = db["superclasses"].apply(lambda s: int(bool(set(s) & ABNORMAL_CLASSES)))
    print(f"records with a diagnostic label: {len(db):,}  abnormal share: {db['abnormal'].mean():.1%}")

    sigs = np.zeros((len(db), 12, 1000), dtype=np.float16)
    t0 = time.time()
    for i, fn in enumerate(db["filename_lr"]):
        x, _ = wfdb.rdsamp(str(ptbxl_dir / fn))
        sigs[i] = np.nan_to_num(x.T[:, :1000]).astype(np.float16)
        if (i + 1) % 2000 == 0:
            print(f"  read {i + 1:,}/{len(db):,}  {time.time() - t0:.0f}s")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, sigs=sigs, ids=db.index.to_numpy(), y=db["abnormal"].to_numpy(),
             fold=db["strat_fold"].to_numpy(), patient=db["patient_id"].to_numpy(),
             superclasses=np.array(["|".join(s) for s in db["superclasses"]]),
             filename=db["filename_lr"].to_numpy())
    print(f"saved {CACHE} ({sigs.nbytes / 1e9:.2f} GB in memory)")


def _load_cache():
    if not CACHE.exists():
        raise SystemExit("run `python -m ml.ecg prepare --ptbxl-dir ...` first")
    d = np.load(CACHE, allow_pickle=True)
    return {k: d[k] for k in d.files}


# --------------------------------------------------------------------------- CNN
def _make_cnn():
    import torch.nn as nn

    def block(i, o, k):
        return nn.Sequential(nn.Conv1d(i, o, k, stride=2, padding=k // 2), nn.BatchNorm1d(o), nn.ReLU())

    class SmallECGNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.body = nn.Sequential(block(12, 32, 7), block(32, 64, 7), block(64, 128, 5),
                                      block(128, 128, 5), block(128, 128, 3))
            self.head = nn.Sequential(nn.Dropout(0.3), nn.Linear(256, 1))

        def forward(self, x):
            h = self.body(x)
            h = __import__("torch").cat([h.mean(-1), h.amax(-1)], dim=1)
            return self.head(h).squeeze(-1)

    return SmallECGNet()


def _predict_cnn(model, X, bs=512):
    import torch
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(X), bs):
            out.append(torch.sigmoid(model(torch.from_numpy(X[i:i + bs]))).numpy())
    return np.concatenate(out) if out else np.zeros(0)


def train_cnn(Xtr, ytr, Xva, yva, epochs, seed=42):
    import torch
    from sklearn.metrics import roc_auc_score

    torch.manual_seed(seed)
    torch.set_num_threads(os.cpu_count() or 4)
    model = _make_cnn()
    opt = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-3)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=2e-3, total_steps=epochs * int(np.ceil(len(Xtr) / 64)))
    lossf = torch.nn.BCEWithLogitsLoss()
    Xt, yt = torch.from_numpy(Xtr), torch.from_numpy(ytr.astype(np.float32))
    best, best_state, rng = -1.0, None, np.random.default_rng(seed)
    for ep in range(epochs):
        model.train()
        t0, perm, tot = time.time(), rng.permutation(len(Xt)), 0.0
        for i in range(0, len(perm), 64):
            idx = perm[i:i + 64]
            xb = Xt[idx]
            shift = int(rng.integers(-50, 51))  # small random time shift as augmentation
            xb = torch.roll(xb, shift, dims=-1)
            loss = lossf(model(xb), yt[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
            tot += loss.item() * len(idx)
        auc = roc_auc_score(yva, _predict_cnn(model, Xva))
        flag = ""
        if auc > best:
            best, flag = auc, "  <- best so far"
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        print(f"  epoch {ep + 1}/{epochs}  loss {tot / len(perm):.4f}  val AUC {auc:.4f}  {time.time() - t0:.0f}s{flag}")
    model.load_state_dict(best_state)
    return model


# --------------------------------------------------------------------------- GBM fallback
def summary_features(X: np.ndarray) -> np.ndarray:
    """Per-lead summary statistics + a crude heart-rate estimate from lead II autocorrelation."""
    X = X.astype(np.float32)
    d = np.diff(X, axis=-1)
    feats = [X.std(-1), np.ptp(X, -1), np.percentile(X, 5, -1), np.percentile(X, 95, -1),
             X.mean(-1), np.abs(d).mean(-1), d.std(-1),
             ((X[..., 1:] * X[..., :-1]) < 0).mean(-1)]
    lead2 = X[:, 1, :] - X[:, 1, :].mean(-1, keepdims=True)
    ac = np.stack([np.correlate(s, s, "full")[999:] for s in lead2])
    lag = ac[:, 30:200].argmax(-1) + 30  # 0.3-2.0 s at 100 Hz -> 30-200 bpm
    hr = 6000.0 / lag
    return np.concatenate(feats + [hr[:, None]], axis=1)


def train_gbm(Xtr, ytr, Xva, yva, seed=42):
    import xgboost as xgb
    m = xgb.XGBClassifier(n_estimators=1500, learning_rate=0.05, max_depth=5, subsample=0.8,
                          colsample_bytree=0.8, eval_metric="auc", early_stopping_rounds=50,
                          tree_method="hist", random_state=seed, n_jobs=-1)
    m.fit(summary_features(Xtr), ytr, eval_set=[(summary_features(Xva), yva)], verbose=False)
    print(f"  trees used: {m.best_iteration + 1}")
    return m


# --------------------------------------------------------------------------- train + evaluate
def train(kind: str, epochs: int):
    import pandas as pd

    d = _load_cache()
    X, y, fold = d["sigs"].astype(np.float32), d["y"].astype(int), d["fold"]
    tr, va, te = fold <= 8, fold == 9, fold == 10
    mean = X[tr].mean(axis=(0, 2), keepdims=True)
    std = X[tr].std(axis=(0, 2), keepdims=True) + 1e-6
    Xn = ((X - mean) / std).astype(np.float32)
    print(f"train {tr.sum():,} / val {va.sum():,} / test {te.sum():,} records; abnormal share {y.mean():.1%}")

    common.ARTIFACTS.mkdir(exist_ok=True)
    if kind == "cnn":
        import torch
        model = train_cnn(Xn[tr], y[tr], Xn[va], y[va], epochs)
        p_va, p_te = _predict_cnn(model, Xn[va]), _predict_cnn(model, Xn[te])
        torch.save(model.state_dict(), common.ARTIFACTS / "ecg_cnn.pt")
    else:
        model = train_gbm(Xn[tr], y[tr], Xn[va], y[va])
        p_va = model.predict_proba(summary_features(Xn[va]))[:, 1]
        p_te = model.predict_proba(summary_features(Xn[te]))[:, 1]
        model.get_booster().save_model(str(common.ARTIFACTS / "ecg_gbm.ubj"))

    thr = common.youden_threshold(y[va], p_va)
    res = common.auc_with_ci(y[te], p_te)
    rep = common.binary_report(y[te], p_te, thr)
    val_auc = common.auc_with_ci(y[va], p_va, n_boot=0)["auc"]
    print(f"\nvalidation (fold 9) AUC {val_auc:.3f}; threshold chosen there (Youden): {thr:.3f}")
    print(f"TEST (fold 10, reported once): AUC {res['auc']:.3f} (95% CI {res['ci95'][0]:.3f}-{res['ci95'][1]:.3f}), "
          f"sens {rep['sensitivity']:.2f}, spec {rep['specificity']:.2f}, ppv {rep['ppv']:.2f}, n={res['n']:,}")

    sc = d["superclasses"][te]
    by_class = {}
    for c in sorted(ABNORMAL_CLASSES):
        m = np.array([c in s.split("|") for s in sc])
        by_class[c] = {"n": int(m.sum()), "share_flagged": float((p_te[m] >= thr).mean()) if m.any() else None}

    common.update_metrics("ptbxl_ecg", {
        "auc": res["auc"], "ci95": res["ci95"], "n_test": res["n"], "n_pos": res["n_pos"],
        "prevalence": float(y[te].mean()), "test_fold": 10, "threshold": thr, "threshold_rule": "Youden on fold 9",
        "sensitivity": rep["sensitivity"], "specificity": rep["specificity"], "ppv": rep["ppv"],
        "flagged_fraction": rep["flagged_fraction"], "val_auc": val_auc,
        "share_flagged_by_true_class": by_class,
        "model": "1D CNN" if kind == "cnn" else "GBM", "model_name": MODEL_NAMES[kind],
        "label": "normal = NORM only; abnormal = any of MI, STTC, CD, HYP",
        "split": "PTB-XL official folds: 1-8 train, 9 validation, 10 test (patient-separated)",
    }, notes=["ECG 'abnormal' includes chronic findings (old MI, bundle branch block, LVH); it is not an acute/STEMI detector."])

    CONFIG_PATH.write_text(json.dumps(common._clean({
        "kind": kind, "threshold": thr, "mean": mean.ravel().tolist(), "std": std.ravel().tolist(),
        "model": MODEL_NAMES[kind]})))
    pd.DataFrame({"ecg_id": d["ids"][te], "filename": d["filename"][te], "superclasses": sc,
                  "true_abnormal": y[te], "abnormal_prob": p_te}).to_csv(
        common.ML_DIR / "data" / "ecg_test_scores.csv", index=False)
    print(f"saved {CONFIG_PATH.name} and data/ecg_test_scores.csv (fold 10, for demo picks)")


# --------------------------------------------------------------------------- inference
_STATE: dict = {}


def _load():
    if _STATE or not CONFIG_PATH.exists():
        return
    cfg = json.loads(CONFIG_PATH.read_text())
    _STATE["cfg"] = cfg
    try:
        if cfg["kind"] == "cnn":
            import torch
            torch.set_num_threads(2)
            m = _make_cnn()
            m.load_state_dict(torch.load(common.ARTIFACTS / "ecg_cnn.pt", map_location="cpu"))
            m.eval()
        else:
            import xgboost as xgb
            m = xgb.Booster()
            m.load_model(str(common.ARTIFACTS / "ecg_gbm.ubj"))
        _STATE["model"] = m
    except Exception as e:
        _STATE["model"] = None
        _STATE["load_error"] = repr(e)
        print(f"[ml.ecg] live model unavailable ({e!r}); will serve precomputed demo results")


def _normalize_id(record_id: str) -> str:
    rid = str(record_id)
    return rid if rid.startswith("ptbxl_") else f"ptbxl_{int(rid)}"


def _demo_entry(record_id: str) -> dict:
    rid = _normalize_id(record_id)
    if not common.DEMO_JSON.exists():
        raise KeyError(f"{rid}: ml/demo_assets.json not built yet")
    for item in json.loads(common.DEMO_JSON.read_text()).get("ecg", []):
        if item["record_id"] == rid:
            return item
    raise KeyError(f"{rid} is not a demo ECG (see ml/demo_assets.json)")


def score_signal(sig_12x1000: np.ndarray) -> float:
    cfg, m = _STATE["cfg"], _STATE["model"]
    x = (sig_12x1000.astype(np.float32) - np.array(cfg["mean"])[:, None]) / np.array(cfg["std"])[:, None]
    x = x[None].astype(np.float32)
    if cfg["kind"] == "cnn":
        return float(_predict_cnn(m, x)[0])
    import xgboost as xgb
    return float(m.predict(xgb.DMatrix(summary_features(x)))[0])


def flag_ecg(record_id: str) -> dict:
    """Contract A6. Accepts 'ptbxl_12345' or '12345'; only demo records (KeyError otherwise)."""
    _load()
    if not _STATE:
        raise RuntimeError("ECG model not trained yet: run `python -m ml.ecg train`")
    cfg = _STATE["cfg"]
    item = _demo_entry(record_id)
    note = common.AI_NOTE
    if _STATE.get("model") is not None:
        import wfdb
        sig, _ = wfdb.rdsamp(str(common.ML_DIR / item["path"]))
        prob = score_signal(np.nan_to_num(sig.T[:, :1000]))
    elif item.get("cached_result"):
        prob = item["cached_result"]["abnormal_prob"]
        note = common.AI_NOTE + " (precomputed by the same model)"
    else:
        raise RuntimeError(f"ECG model unavailable: {_STATE.get('load_error')}")
    thr = cfg["threshold"]
    return {"abnormal_prob": round(prob, 3), "abnormal": bool(prob >= thr), "threshold": round(thr, 3),
            "model": cfg["model"], "note": note}


_load()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--ptbxl-dir", type=Path, required=True)
    t = sub.add_parser("train")
    t.add_argument("--model", choices=["cnn", "gbm"], default="cnn")
    t.add_argument("--epochs", type=int, default=12)
    args = ap.parse_args()
    if args.cmd == "prepare":
        prepare(args.ptbxl_dir)
    else:
        train(args.model, args.epochs)


if __name__ == "__main__":
    main()
