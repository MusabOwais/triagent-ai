"""NIH chest X-ray flag: outside test of a CheXpert-trained model + flag_xray() for the backend.

Evaluate (from the repo root):
    python -m ml.xray evaluate --nih-dir PATH_TO_NIH_SAMPLE --limit 10   # quick check on 10 images
    python -m ml.xray evaluate --nih-dir PATH_TO_NIH_SAMPLE              # full run (~5,600 images)
    python -m ml.xray evaluate --nih-dir ... --ship probe                # ship the NIH-adapted version

PATH_TO_NIH_SAMPLE is the Kaggle "Random Sample of NIH Chest X-ray Dataset" folder: it must contain
sample_labels.csv and the PNGs somewhere below it.

What it does:
* Model: torchxrayvision densenet121-res224-chex (trained on CheXpert, never on NIH).
* Splits the NIH sample 50/50 BY PATIENT into half A (tuning) and half B (reporting).
* "pretrained" variant: thresholds chosen on A (Youden), AUC/sens/spec reported on B.
* "probe" variant: a logistic regression per finding on the frozen image features, fitted on A,
  reported on B. This is the "we used NIH" version if organizers require training on it.
* Also reports the combined "any of 5 flagged" rate on B, because the bed score adds +10 for ANY flag.
* One pass over the images; outputs + features are cached in ml/data/xray_cache.npz.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

try:
    from . import common
except ImportError:
    import common

FINDINGS = ["Pneumonia", "Effusion", "Edema", "Cardiomegaly", "Pneumothorax"]
MODEL_NAME = "xrv_chex_densenet"
WEIGHTS = "densenet121-res224-chex"
WEIGHTS_DIR = common.ARTIFACTS / "xrv_weights"
CONFIG_PATH = common.ARTIFACTS / "xray_config.json"
CACHE_PATH = common.ML_DIR / "data" / "xray_cache.npz"


# --------------------------------------------------------------------------- model + preprocessing
def _build_model():
    import torchxrayvision as xrv
    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    m = xrv.models.DenseNet(weights=WEIGHTS, cache_dir=str(WEIGHTS_DIR))
    m.eval()
    return m


def preprocess(path) -> np.ndarray:
    """PNG/JPG -> (1, 224, 224) float32 in torchxrayvision's [-1024, 1024] range."""
    import skimage.io
    import torchxrayvision as xrv

    img = skimage.io.imread(str(path))
    if img.ndim == 3:
        img = img[..., :3].mean(axis=2)  # RGB/RGBA -> gray
    maxval = 65535 if img.dtype == np.uint16 else 255
    img = xrv.datasets.normalize(img.astype(np.float32), maxval)[None, ...]
    img = xrv.datasets.XRayCenterCrop()(img)
    img = xrv.datasets.XRayResizer(224)(img)
    return img.astype(np.float32)


def run_model(model, batch: np.ndarray):
    """Returns (outputs for our 5 findings, 1024-d pooled features)."""
    import torch
    with torch.no_grad():
        x = torch.from_numpy(batch)
        feats = model.features2(x)
        out = model.classifier(feats)
        if getattr(model, "op_threshs", None) is not None:
            import torchxrayvision as xrv
            out = xrv.models.op_norm(torch.sigmoid(out), model.op_threshs)
        else:
            out = torch.sigmoid(out)
    labels = list(getattr(model, "targets", None) or model.pathologies)
    idx = [labels.index(f) for f in FINDINGS]
    return out[:, idx].numpy(), feats.numpy()


# --------------------------------------------------------------------------- evaluation
def _load_labels(nih_dir: Path):
    import pandas as pd
    csvs = list(nih_dir.rglob("sample_labels.csv")) or list(nih_dir.rglob("Data_Entry*.csv"))
    if not csvs:
        raise SystemExit(f"no sample_labels.csv under {nih_dir}")
    lab = pd.read_csv(csvs[0])
    files = {p.name: p for p in nih_dir.rglob("*.png")}
    lab = lab[lab["Image Index"].isin(files)].reset_index(drop=True)
    lab["path"] = lab["Image Index"].map(lambda n: str(files[n]))
    for f in FINDINGS:
        lab[f] = lab["Finding Labels"].str.split("|").apply(lambda xs, f=f: int(f in xs))
    print(f"labels: {csvs[0]}  images found: {len(lab):,}  patients: {lab['Patient ID'].nunique():,}")
    print("positives in full sample: " + ", ".join(f"{f}={lab[f].sum()}" for f in FINDINGS))
    return lab


def _extract(lab, model, batch_size=16):
    ids = lab["Image Index"].tolist()
    if CACHE_PATH.exists():
        c = np.load(CACHE_PATH, allow_pickle=True)
        if list(c["ids"]) == ids:
            print(f"using cached model outputs: {CACHE_PATH}")
            return c["out"], c["feats"]
    outs, feats = [], []
    t0 = time.time()
    for i in range(0, len(ids), batch_size):
        batch = np.stack([preprocess(p) for p in lab["path"].iloc[i:i + batch_size]])
        o, f = run_model(model, batch)
        outs.append(o)
        feats.append(f)
        done = i + len(batch)
        if done % (batch_size * 20) == 0 or done == len(ids):
            el = time.time() - t0
            print(f"  {done:,}/{len(ids):,} images  {el:.0f}s  (~{el / done * (len(ids) - done):.0f}s left)")
    out, feat = np.concatenate(outs), np.concatenate(feats)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE_PATH, ids=np.array(ids, dtype=object), out=out, feats=feat.astype(np.float16))
    return out, feat


def _report_variant(name, yA, sA, yB, sB):
    """Per-finding thresholds on A, metrics on B, plus the combined any-flag result on B."""
    res, thr = {}, {}
    for j, f in enumerate(FINDINGS):
        if yA[:, j].sum() == 0 or yB[:, j].sum() == 0:
            res[f] = {"auc": None, "note": "no positives in one half"}
            continue
        t = common.youden_threshold(yA[:, j], sA[:, j])
        thr[f] = t
        r = common.auc_with_ci(yB[:, j], sB[:, j])
        b = common.binary_report(yB[:, j], sB[:, j], t)
        r.update(threshold=t, sensitivity=b["sensitivity"], specificity=b["specificity"], ppv=b["ppv"],
                 n_pos_tuning_half=int(yA[:, j].sum()))
        res[f] = r
        print(f"  {name:10} {f:13} AUC {r['auc']:.3f} (95% CI {r['ci95'][0]:.3f}-{r['ci95'][1]:.3f})  "
              f"pos {r['n_pos']:>3}/{r['n']:,}  thr {t:.3f}  sens {b['sensitivity']:.2f} spec {b['specificity']:.2f}")
    flagged = np.zeros(len(yB), bool)
    for j, f in enumerate(FINDINGS):
        if f in thr:
            flagged |= sB[:, j] >= thr[f]
    any_true = yB.max(axis=1)
    rep = common.binary_report(any_true, flagged.astype(float), 0.5)
    rep["meaning"] = "+10 bed points fire if ANY finding is flagged; truth = image has any of the 5 labels"
    res["any_flag"] = rep
    print(f"  {name:10} ANY-of-5 flag: flags {rep['flagged_fraction']:.0%} of images, "
          f"sens {rep['sensitivity']:.2f}, spec {rep['specificity']:.2f}, ppv {rep['ppv']:.2f}")
    return res, thr


def evaluate(nih_dir: Path, limit: int | None, ship: str, seed=42):
    from sklearn.linear_model import LogisticRegressionCV
    from sklearn.model_selection import GroupShuffleSplit, cross_val_predict
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    lab = _load_labels(nih_dir)
    model = _build_model()
    if limit:
        lab = lab.head(limit)
        t0 = time.time()
        out, _ = run_model(model, np.stack([preprocess(p) for p in lab["path"]]))
        print(f"\n{limit} images in {time.time() - t0:.1f}s. Outputs (rows=images):")
        print("  " + "  ".join(f"{f[:8]:>8}" for f in FINDINGS) + "   true labels")
        for o, fl in zip(out, lab["Finding Labels"]):
            print("  " + "  ".join(f"{v:8.2f}" for v in o) + f"   {fl}")
        return

    out, feats = _extract(lab, model)
    feats = feats.astype(np.float32)
    y = lab[FINDINGS].to_numpy()
    groups = lab["Patient ID"].to_numpy()
    a, b = next(GroupShuffleSplit(1, test_size=0.5, random_state=seed).split(lab, groups=groups))
    assert not set(groups[a]) & set(groups[b]), "patient overlap between halves"
    print(f"\nsplit by patient: half A {len(a):,} images / half B {len(b):,} images, no shared patients")

    print("\n== pretrained CheXpert model, outside test on NIH half B")
    pre, pre_thr = _report_variant("pretrained", y[a], out[a], y[b], out[b])

    print("\n== linear probe: logistic regression on frozen features, fitted on half A")
    sA_cv, sB, probes = np.zeros((len(a), 5)), np.zeros((len(b), 5)), {}
    for j, f in enumerate(FINDINGS):
        clf = make_pipeline(StandardScaler(), LogisticRegressionCV(Cs=[0.001, 0.01, 0.1], cv=5, max_iter=2000,
                                                                   scoring="roc_auc"))
        sA_cv[:, j] = cross_val_predict(clf, feats[a], y[a, j], cv=5, method="predict_proba")[:, 1]
        clf.fit(feats[a], y[a, j])
        sB[:, j] = clf.predict_proba(feats[b])[:, 1]
        sc, lr = clf.named_steps["standardscaler"], clf.named_steps["logisticregressioncv"]
        probes[f] = {"mean": sc.mean_.tolist(), "scale": sc.scale_.tolist(),
                     "coef": lr.coef_[0].tolist(), "intercept": float(lr.intercept_[0])}
    probe, probe_thr = _report_variant("probe", y[a], sA_cv, y[b], sB)

    common.update_metrics("nih_xray", {
        **{f: pre[f] for f in FINDINGS},
        "any_flag": pre["any_flag"],
        "n_eval": int(len(b)), "n_tuning": int(len(a)),
        "model": "xrv densenet121-res224-chex (CheXpert-trained), outside test",
        "threshold_rule": "Youden index on half A",
        "split": "Kaggle NIH random sample, 50/50 by Patient ID",
        "shipped_variant": ship,
        "nih_adapted_probe": {**{f: probe[f] for f in FINDINGS}, "any_flag": probe["any_flag"],
                              "model": "logistic regression on frozen DenseNet features, fitted on half A"},
    }, notes=["NIH labels were extracted automatically from radiology reports and contain errors.",
              "X-ray output is an AI flag, not a diagnosis. Few positives per finding: read the 95% CIs."])

    cfg = {"variant": ship, "findings": FINDINGS,
           "thresholds": pre_thr if ship == "pretrained" else probe_thr,
           "probes": probes if ship == "probe" else None,
           "model": MODEL_NAME if ship == "pretrained" else MODEL_NAME + "_nih_probe",
           "eval_half_b_ids": lab["Image Index"].iloc[b].tolist()}
    CONFIG_PATH.write_text(json.dumps(common._clean(cfg)))
    # per-image scores on half B, for choosing demo images (truth recorded alongside)
    import pandas as pd
    s = out[b] if ship == "pretrained" else sB
    table = pd.DataFrame(s, columns=FINDINGS)
    table.insert(0, "image_id", lab["Image Index"].iloc[b].to_numpy())
    table.insert(1, "path", lab["path"].iloc[b].to_numpy())
    table.insert(2, "true_labels", lab["Finding Labels"].iloc[b].to_numpy())
    table.to_csv(common.ML_DIR / "data" / "xray_half_b_scores.csv", index=False)
    print(f"\nsaved {CONFIG_PATH.name} (shipping '{ship}') and data/xray_half_b_scores.csv for demo picks")


# --------------------------------------------------------------------------- inference
_STATE: dict = {}


def _load():
    if _STATE or not CONFIG_PATH.exists():
        return
    cfg = json.loads(CONFIG_PATH.read_text())
    _STATE["cfg"] = cfg
    try:
        import torch
        torch.set_num_threads(2)
        _STATE["model"] = _build_model()
    except Exception as e:  # torch missing / weights missing: fall back to cached demo results
        _STATE["model"] = None
        _STATE["load_error"] = repr(e)
        print(f"[ml.xray] live model unavailable ({e!r}); will serve precomputed demo results")


def _demo_entry(image_id: str) -> dict:
    if not common.DEMO_JSON.exists():
        raise KeyError(f"{image_id}: ml/demo_assets.json not built yet")
    for item in json.loads(common.DEMO_JSON.read_text()).get("xray", []):
        if item["image_id"] == image_id:
            return item
    raise KeyError(f"{image_id} is not a demo X-ray (see ml/demo_assets.json)")


def _score(image_path) -> dict:
    cfg = _STATE["cfg"]
    out, feats = run_model(_STATE["model"], preprocess(image_path)[None])
    if cfg["variant"] == "probe":
        scores = {}
        for f in FINDINGS:
            p = cfg["probes"][f]
            z = (feats[0] - np.array(p["mean"])) / np.array(p["scale"])
            scores[f] = float(1 / (1 + np.exp(-(z @ np.array(p["coef"]) + p["intercept"]))))
        return scores
    return {f: float(v) for f, v in zip(FINDINGS, out[0])}


def flag_xray(image_id: str) -> dict:
    """Contract A6. Only demo images listed in ml/demo_assets.json are accepted (KeyError otherwise)."""
    _load()
    if not _STATE:
        raise RuntimeError("X-ray model not evaluated yet: run `python -m ml.xray evaluate ...`")
    cfg = _STATE["cfg"]
    item = _demo_entry(image_id)
    note = common.AI_NOTE
    if _STATE.get("model") is not None:
        scores = _score(common.ML_DIR / item["path"])
    elif item.get("cached_result"):
        scores = item["cached_result"]["findings"]
        note = common.AI_NOTE + " (precomputed by the same model)"
    else:
        raise RuntimeError(f"X-ray model unavailable: {_STATE.get('load_error')}")
    thr = cfg["thresholds"]
    flagged = [f for f in FINDINGS if f in thr and scores[f] >= thr[f]]
    return {"findings": {f: round(scores[f], 3) for f in FINDINGS}, "flagged": flagged,
            "thresholds": {f: round(t, 3) for f, t in thr.items()}, "model": cfg["model"], "note": note}


_load()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("evaluate")
    e.add_argument("--nih-dir", type=Path, required=True)
    e.add_argument("--limit", type=int)
    e.add_argument("--ship", choices=["pretrained", "probe"], default="pretrained")
    sub.add_parser("download-weights", help="cache the CheXpert weights in ml/artifacts (do this before the venue)")
    args = ap.parse_args()
    if args.cmd == "evaluate":
        evaluate(args.nih_dir, args.limit, args.ship)
    else:
        _build_model()
        print(f"weights cached in {WEIGHTS_DIR}")


if __name__ == "__main__":
    main()
