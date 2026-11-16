"""Imports Role 1's real ML functions from ml/ if they exist; otherwise uses stubs with the exact A6 signatures.
Stubs return fixed plausible values and set "model": "stub" so it is visible on screen. Swapping in the real
functions needs no code change here: Role 1 exposes them from ml/__init__.py (or ml/predict.py)."""
import json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# ---------------- stubs ----------------
_STUB_ECG = {  # PTB-XL fold-10 (held-out) records; abnormal flags are fixed stub values
    "ptbxl_19669": 0.08, "ptbxl_11884": 0.12, "ptbxl_14912": 0.86, "ptbxl_19187": 0.61,
    "ptbxl_10743": 0.92, "ptbxl_17920": 0.78, "ptbxl_17404": 0.94, "ptbxl_3603": 0.35}
_STUB_XRAY = {  # NIH images; fixed stub probabilities for the 5 contract findings
    "00000842_000.png": {}, "00001039_003.png": {}, "00000591_018.png": {"Effusion": 0.71},
    "00000459_034.png": {"Edema": 0.66}, "00000468_016.png": {"Pneumothorax": 0.58},
    "00000579_001.png": {"Cardiomegaly": 0.69}, "00000773_001.png": {"Pneumonia": 0.74},
    "00001158_002.png": {"Effusion": 0.22}}
XRAY_FINDINGS = ["Pneumonia", "Effusion", "Edema", "Cardiomegaly", "Pneumothorax"]


def _stub_predict_admission(features: dict, stage: str) -> dict:
    """Fixed, plausible, NOT trained. Rough age/oxygen/complaint heuristic so the demo board isn't flat."""
    p = 0.20 + 0.006 * max(0, features.get("age", 40) - 30)
    if features.get("spo2") is not None and features["spo2"] < 94: p += 0.15
    if features.get("complaint_category") in ("shortness_of_breath", "altered_mental_status", "fever_infection", "stroke_signs"): p += 0.15
    if features.get("complaint_category") == "trauma": p -= 0.10
    if stage == "triage" and features.get("esi") is not None: p += {1: 0.3, 2: 0.15, 3: 0.0, 4: -0.15, 5: -0.2}[features["esi"]]
    p = min(0.95, max(0.03, p))
    reasons = [{"label": f"Age {features.get('age')}", "direction": "up" if features.get("age", 0) >= 50 else "down"}]
    if features.get("spo2") is not None and features["spo2"] < 94: reasons.append({"label": f"SpO2 {features['spo2']:g}%", "direction": "up"})
    return {"probability": round(p, 2), "stage": stage, "model": "stub", "top_reasons": reasons[:3]}


def _stub_flag_ecg(record_id: str) -> dict:
    p = _STUB_ECG.get(record_id, 0.2)
    return {"abnormal_prob": p, "abnormal": p >= 0.5, "threshold": 0.5, "model": "stub", "note": "AI flag, not a diagnosis"}


def _stub_flag_xray(image_id: str) -> dict:
    base = {f: 0.05 for f in XRAY_FINDINGS}
    base.update(_STUB_XRAY.get(image_id, {}))
    th = {f: 0.5 for f in XRAY_FINDINGS}
    return {"findings": base, "flagged": [f for f in XRAY_FINDINGS if base[f] >= th[f]], "thresholds": th,
            "model": "stub", "note": "AI flag, not a diagnosis"}


def _stub_assets() -> dict:
    return {"ecg": [{"record_id": k, "label": f"PTB-XL record {k.split('_')[1]}"} for k in _STUB_ECG],
            "xray": [{"image_id": k, "label": f"NIH {k}"} for k in _STUB_XRAY], "source": "stub"}


# ---------------- real functions if Role 1 has shipped them ----------------
def _try(name, fallback):
    for mod in ("ml", "ml.predict"):
        try:
            m = __import__(mod, fromlist=[name])
            if hasattr(m, name):
                return getattr(m, name), "real"
        except Exception:
            pass
    return fallback, "stub"


predict_admission, ADMISSION_SOURCE = _try("predict_admission", _stub_predict_admission)
flag_ecg, ECG_SOURCE = _try("flag_ecg", _stub_flag_ecg)
flag_xray, XRAY_SOURCE = _try("flag_xray", _stub_flag_xray)


def metrics() -> dict:
    f = REPO / "ml" / "metrics.json"
    return json.loads(f.read_text()) if f.exists() else {"status": "stub", "note": "ml/metrics.json not yet provided by Role 1"}


def demo_assets() -> dict:
    f = REPO / "ml" / "demo_assets.json"
    return json.loads(f.read_text()) if f.exists() else _stub_assets()


def sources() -> dict:
    return {"admission": ADMISSION_SOURCE, "ecg": ECG_SOURCE, "xray": XRAY_SOURCE}
