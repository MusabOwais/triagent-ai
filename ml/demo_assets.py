"""Pick demo ECGs and X-rays from HELD-OUT data only, copy them into ml/demo_assets/, write demo_assets.json.

    python -m ml.demo_assets build --ptbxl-dir PATH_TO_PTBXL

Needs: `python -m ml.ecg train` (writes data/ecg_test_scores.csv, fold 10 only) and
       `python -m ml.xray evaluate` (writes data/xray_half_b_scores.csv, half B only).

Each asset records its TRUE label for the team, the reason it was picked, and the model's output
(`cached_result`, used only if the live model cannot load on the presenting laptop).
One deliberate AI miss per modality is included so the demo can show the clinician-review path.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

try:
    from . import common
except ImportError:
    import common


def _pick_ecg(thr: float) -> list[dict]:
    df = pd.read_csv(common.ML_DIR / "data" / "ecg_test_scores.csv")
    sc = df["superclasses"].fillna("")
    picks = []

    def take(sub, n, role):
        for _, r in sub.head(n).iterrows():
            if r["ecg_id"] not in {p["ecg_id"] for p in picks}:
                picks.append({**r.to_dict(), "role": role})

    take(df[sc.str.contains("MI") & (df.abnormal_prob >= thr)].sort_values("abnormal_prob", ascending=False), 2,
         "abnormal, flagged (MI in true labels) - chest-pain demo patient")
    take(df[sc.str.contains("STTC") & ~sc.str.contains("MI") & (df.abnormal_prob >= thr)]
         .sort_values("abnormal_prob", ascending=False), 1, "abnormal, flagged (ST/T change)")
    take(df[(sc == "NORM") & (df.abnormal_prob < thr)].sort_values("abnormal_prob"), 2, "normal, not flagged")
    take(df[(df.true_abnormal == 1) & (df.abnormal_prob < thr)].sort_values("abnormal_prob", ascending=False), 1,
         "AI MISS: truly abnormal but not flagged - shows why a normal AI result adds 0 and never lowers priority")
    return picks


def _pick_xray(thresholds: dict) -> list[dict]:
    df = pd.read_csv(common.ML_DIR / "data" / "xray_half_b_scores.csv")
    labels = df["true_labels"].fillna("")
    flagged_any = pd.Series(False, index=df.index)
    for f, t in thresholds.items():
        flagged_any |= df[f] >= t
    picks = []

    def take(sub, n, role):
        for _, r in sub.head(n).iterrows():
            if r["image_id"] not in {p["image_id"] for p in picks}:
                picks.append({**r.to_dict(), "role": role})

    pn_t = thresholds.get("Pneumonia", 1.0)
    take(df[labels.str.contains("Pneumonia") & (df["Pneumonia"] >= pn_t)].sort_values("Pneumonia", ascending=False),
         2, "Pneumonia in true labels, flagged")
    for f in ("Effusion", "Cardiomegaly"):
        take(df[labels.str.contains(f) & (df[f] >= thresholds.get(f, 1.0))].sort_values(f, ascending=False), 1,
             f"{f} in true labels, flagged")
    take(df[(labels == "No Finding") & ~flagged_any].sort_values("Pneumonia"), 2, "No Finding, not flagged")
    findings = "|".join(thresholds)
    take(df[labels.str.contains(findings) & ~flagged_any], 1,
         "AI MISS: has a target finding but not flagged - clinician review path")
    return picks


def build(ptbxl_dir: Path):
    from . import ecg, xray

    out = {"ecg": [], "xray": [], "notes": [
        "All demo assets come from held-out data only (PTB-XL fold 10, NIH half B), never from training data.",
        "true_label fields are for the team; the screen shows only the AI flag and clinician review.",
        "Demo patients are fictional composites: Yale-like vitals + one PTB-XL ECG + one NIH X-ray.",
    ]}
    (common.DEMO_DIR / "ecg").mkdir(parents=True, exist_ok=True)
    (common.DEMO_DIR / "xray").mkdir(parents=True, exist_ok=True)

    ecg_cfg = json.loads(ecg.CONFIG_PATH.read_text())
    for p in _pick_ecg(ecg_cfg["threshold"]):
        src = ptbxl_dir / p["filename"]
        dst = common.DEMO_DIR / "ecg" / src.name
        for ext in (".hea", ".dat"):
            shutil.copy(src.with_suffix(ext), dst.with_suffix(ext))
        out["ecg"].append({"record_id": f"ptbxl_{int(p['ecg_id'])}", "path": str(dst.relative_to(common.ML_DIR)),
                           "true_label": "abnormal" if p["true_abnormal"] else "normal",
                           "true_superclasses": p["superclasses"], "picked_because": p["role"]})

    xr_cfg = json.loads(xray.CONFIG_PATH.read_text())
    for p in _pick_xray(xr_cfg["thresholds"]):
        dst = common.DEMO_DIR / "xray" / p["image_id"]
        shutil.copy(p["path"], dst)
        out["xray"].append({"image_id": p["image_id"], "path": str(dst.relative_to(common.ML_DIR)),
                            "true_labels": p["true_labels"], "picked_because": p["role"]})

    common.DEMO_JSON.write_text(json.dumps(out, indent=2))
    # second pass: run the live models on the copied files and store the outputs as a fallback
    for item in out["ecg"]:
        item["cached_result"] = ecg.flag_ecg(item["record_id"])
    for item in out["xray"]:
        item["cached_result"] = xray.flag_xray(item["image_id"])
    # guard: the live result must agree with why the asset was picked
    problems = []
    for i in out["ecg"]:
        want_flag = "not flagged" not in i["picked_because"] and "MISS" not in i["picked_because"]
        if i["cached_result"]["abnormal"] != want_flag:
            problems.append(f"ECG {i['record_id']}: live flag {i['cached_result']['abnormal']} vs '{i['picked_because']}'")
    for i in out["xray"]:
        want_flag = "not flagged" not in i["picked_because"] and "MISS" not in i["picked_because"]
        if bool(i["cached_result"]["flagged"]) != want_flag:
            problems.append(f"XRAY {i['image_id']}: live flags {i['cached_result']['flagged']} vs '{i['picked_because']}'")
    out["consistency_problems"] = problems
    common.DEMO_JSON.write_text(json.dumps(common._clean(out), indent=2))

    print(f"wrote {common.DEMO_JSON} with {len(out['ecg'])} ECGs and {len(out['xray'])} X-rays:")
    for i in out["ecg"]:
        r = i["cached_result"]
        print(f"  ECG  {i['record_id']:12} true={i['true_superclasses']:12} AI prob {r['abnormal_prob']:.2f} "
              f"flag={r['abnormal']!s:5} | {i['picked_because']}")
    for i in out["xray"]:
        r = i["cached_result"]
        print(f"  XRAY {i['image_id']:18} true={i['true_labels'][:28]:28} flagged={r['flagged']} | {i['picked_because']}")
    for p in problems:
        print(f"  WARNING (do not demo until fixed): {p}")
    if not problems:
        print("  consistency check passed: every live result matches why it was picked")
    if len(out["ecg"]) < 6 or len(out["xray"]) < 6:
        print("note: fewer than 6 of a kind found for the requested story; that is fine, the list says what exists")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--ptbxl-dir", type=Path, required=True)
    args = ap.parse_args()
    build(args.ptbxl_dir)


if __name__ == "__main__":
    main()
