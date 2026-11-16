"""Single source of truth for every formula on the formulas page. Pure functions, no web code.
Model A/B coefficients are read from outputs/vitals_scorecard.json (trained on Yale); nothing is retyped by hand."""
import json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SC = json.loads((ROOT / "outputs/vitals_scorecard.json").read_text())
CAL = json.loads((ROOT / "outputs/calibration.json").read_text())

# Same bins as src/vitals_scorecard.py (label, lo, hi), inclusive. Reference bin = 0.
BINS = {
    "age": [("40-54", 40, 54), ("55-64", 55, 64), ("65-74", 65, 74), ("75-84", 75, 84), ("85+", 85, 200)],
    "hr": [("<=50", 0, 50), ("91-110", 91, 110), ("111-130", 111, 130), (">=131", 131, 400)],
    "sbp": [("<=90", 0, 90), ("91-100", 91, 100), ("101-110", 101, 110), ("160-199", 160, 199), (">=200", 200, 400)],
    "dbp": [("<=50", 0, 50), (">=110", 110, 300)],
    "rr": [("<=11", 0, 11), ("21-24", 21, 24), (">=25", 25, 100)],
    "spo2": [("<=91", 0, 91), ("92-93", 92, 93), ("94-95", 94, 95)],
    "temp_f": [("<=95.0", 0, 95.0), ("95.1-96.8", 95.1, 96.8), ("100.5-102.2", 100.5, 102.2), (">=102.3", 102.3, 120)],
}
LABEL = {"age": "Age", "hr": "Heart rate", "sbp": "Systolic BP", "dbp": "Diastolic BP", "rr": "Resp rate",
         "spo2": "SpO2", "temp_f": "Temp"}
COMPLAINTS = [c for c in SC["top_complaints"]]  # cc_* names from Yale, ordered by frequency

sigmoid = lambda x: 1 / (1 + math.exp(-x))
to_score = lambda L: 1 + round(99 * sigmoid(L))


def news2(v):
    """NEWS2 points. v: dict with rr, spo2, o2 (bool), sbp, hr, gcs, temp_f. Returns (total, parts)."""
    rr, sp, sbp, hr, gcs = v["rr"], v["spo2"], v["sbp"], v["hr"], v.get("gcs", 15)
    t = (v["temp_f"] - 32) * 5 / 9
    p = {
        "RR": 3 if rr <= 8 else 1 if rr <= 11 else 0 if rr <= 20 else 2 if rr <= 24 else 3,
        "SpO2": 3 if sp <= 91 else 2 if sp <= 93 else 1 if sp <= 95 else 0,
        "O2": 2 if v.get("o2") else 0,
        "SBP": 3 if sbp <= 90 else 2 if sbp <= 100 else 1 if sbp <= 110 else 0 if sbp <= 219 else 3,
        "HR": 3 if hr <= 40 else 1 if hr <= 50 else 0 if hr <= 90 else 1 if hr <= 110 else 2 if hr <= 130 else 3,
        "GCS": 0 if gcs >= 15 else 3,
        "Temp": 3 if t <= 35.0 else 1 if t <= 36.0 else 0 if t <= 38.0 else 1 if t <= 39.0 else 2,
    }
    return sum(p.values()), p


def news2_floor(total, parts):
    if total >= 7: return 80
    if total >= 5: return 60
    if max(parts.values()) == 3: return 45
    return 0


def model_logit(v, complaint):
    """Model B if a listed complaint is given (or 'other'), Model A if complaint is None. Returns (L, contributions)."""
    m = SC["B_vitals_plus_complaint"] if complaint is not None else SC["A_vitals_only"]
    co = m["coefficients"]
    L, parts = m["intercept"], [("Intercept", m["intercept"])]
    for var, bins in BINS.items():
        for lab, lo, hi in bins:
            if lo <= v[var] <= hi:
                L += co[f"{var} {lab}"]; parts.append((f"{LABEL[var]} {lab}", co[f"{var} {lab}"]))
    if v.get("o2"): L += co["supplemental_o2"]; parts.append(("Supplemental O2", co["supplemental_o2"]))
    if v.get("male"): L += co["male"]; parts.append(("Male", co["male"]))
    if complaint:
        k = f"complaint: {complaint[3:]}"
        if k in co: L += co[k]; parts.append((f"Complaint: {pretty_cc(complaint)}", co[k]))
    return L, parts, ("B" if complaint is not None else "A")


OVERLAY = {
    "gcs": lambda g: 2.0 if g <= 8 else 1.0 if g <= 12 else 0.5 if g <= 14 else 0.0,
    "rhythm": {"sinus": 0.0, "other": 0.0, "af_rvr": 1.0, "svt": 1.0, "vf": 2.5, "vt": 2.5, "stemi": 2.5, "chb": 2.5},
    "injury": {"open_fracture": 1.5, "amputation": 1.5, "uncontrolled_bleeding": 1.5,
               "closed_fracture": 0.7, "frostbite": 0.7, "burn": 0.7},
}
RHYTHM_LABEL = {"sinus": "Sinus rhythm", "other": "Other", "af_rvr": "AF with rapid response", "svt": "SVT",
                "vf": "VF", "vt": "VT", "stemi": "ST-elevation", "chb": "Complete heart block"}


def overlay(v):
    parts = []
    g = OVERLAY["gcs"](v.get("gcs", 15))
    if g: parts.append((f"GCS {v.get('gcs')}", g))
    r = OVERLAY["rhythm"].get(v.get("rhythm", "sinus"), 0)
    if r: parts.append((f"Rhythm: {RHYTHM_LABEL[v['rhythm']]}", r))
    for inj in v.get("injuries", []):
        parts.append((f"Injury: {inj.replace('_', ' ')}", OVERLAY["injury"][inj]))
    if v.get("pain", 0) >= 8: parts.append((f"Pain {v['pain']}/10", 0.3))
    return sum(p[1] for p in parts), parts


def ambulance_score(v, complaint):
    """Stage 1. Returns dict with L1, score1, floor, breakdown."""
    Lm, mparts, which = model_logit(v, complaint)
    Lo, oparts = overlay(v)
    n, nparts = news2(v)
    fl = news2_floor(n, nparts)
    L1 = Lm + Lo
    raw = to_score(L1)
    return {"model": which, "L_model": Lm, "L1": L1, "score_raw": raw, "news2": n, "news2_parts": nparts,
            "floor": fl, "score": max(raw, fl), "model_parts": mparts, "overlay_parts": oparts,
            "p_admit_model": sigmoid(Lm)}


# ---------- Stage 2 ----------
ECG_W = {"MI": 2.5, "STTC": 1.2, "CD": 0.8, "HYP": 0.3}
ECG_NORM_W = 0.4
CXR_W = {"Pneumothorax": 2.0, "Edema": 1.2, "Pneumonia": 1.0, "Consolidation": 1.0, "Effusion": 0.8,
         "Cardiomegaly": 0.5, "Mass": 0.5, "Atelectasis": 0.3, "Infiltration": 0.3,
         "Nodule": 0.1, "Emphysema": 0.1, "Fibrosis": 0.1, "Pleural_Thickening": 0.1, "Hernia": 0.1}
CXR_NORM_W = 0.4
MAX_DROP = 0.5
CXR_ALLOW_DOWN = False  # X-ray model AUROC 0.708 on a small subset: not reliable enough to lower a score


def calibrate(kind, probs):
    out = {}
    for c, p in probs.items():
        k = CAL[kind][c]; p = min(max(p, 1e-6), 1 - 1e-6)
        out[c] = sigmoid(k["a"] * math.log(p / (1 - p)) + k["b"])
    return out


def ecg_delta(pc):
    up = sum(ECG_W[c] * pc[c] for c in ECG_W)
    d = up - ECG_NORM_W * pc["NORM"]
    top = max(pc.values())
    unsure = 0.3 <= top <= 0.7
    if d < 0 and unsure: d_used, note = 0.0, "Model unsure: no downward move"
    else: d_used, note = max(d, -MAX_DROP), ("Capped at -0.5" if d < -MAX_DROP else "")
    return {"delta_raw": d, "delta": d_used, "note": note}


def cxr_delta(pc):
    p_norm = 1 - max(pc.values())
    d = sum(CXR_W[c] * pc[c] for c in CXR_W) - CXR_NORM_W * p_norm
    top = max(pc.values())
    if d < 0 and not CXR_ALLOW_DOWN: d_used, note = 0.0, "X-ray model may only raise scores (proof-of-concept limit)"
    elif d < 0 and 0.3 <= top <= 0.7: d_used, note = 0.0, "Model unsure: no downward move"
    else: d_used, note = max(d, -MAX_DROP), ("Capped at -0.5" if d < -MAX_DROP else "")
    return {"delta_raw": d, "delta": d_used, "note": note, "p_normal": p_norm}


# ---------- Bed type rules (5 types) ----------
BEDS = ["ICU", "CCU", "Telemetry", "Psychiatric", "General ward"]


def provisional_bed(news2_total, complaint):
    if news2_total >= 7: return "ICU", "NEWS2 >= 7"
    if complaint in ("cc_chestpain", "cc_syncope"): return "Telemetry", f"Complaint: {pretty_cc(complaint)}"
    if complaint in ("cc_suicidal", "cc_psychiatricevaluation") and news2_total < 5:
        return "Psychiatric", f"Complaint: {pretty_cc(complaint)}, NEWS2 < 5"
    return "General ward", "No specific rule matched"


def bed_after_ecg(current, pc):
    if current == "ICU": return "ICU", "Stays ICU"
    if pc["MI"] >= 0.5: return "CCU", f"ECG p(MI) = {pc['MI']:.2f}"
    if current in ("ICU", "CCU"): return current, "No change"
    if pc["STTC"] >= 0.5 or pc["CD"] >= 0.5:
        return "Telemetry", f"ECG p(ST/T) = {pc['STTC']:.2f}, p(CD) = {pc['CD']:.2f}"
    return current, "No change"


def priority(L, minutes_waiting):
    return L + 0.01 * minutes_waiting


CC_PRETTY = {"cc_alcoholintoxication": "Alcohol intoxication", "cc_abdominalpain": "Abdominal pain",
             "cc_chestpain": "Chest pain", "cc_other": "Other", "cc_motorvehiclecrash": "Motor vehicle crash",
             "cc_fall": "Fall", "cc_shortnessofbreath": "Shortness of breath", "cc_suicidal": "Suicidal",
             "cc_psychiatricevaluation": "Psychiatric evaluation", "cc_alteredmentalstatus": "Altered mental status",
             "cc_dizziness": "Dizziness", "cc_backpain": "Back pain", "cc_weakness": "Weakness",
             "cc_fall>65": "Fall, age over 65", "cc_syncope": "Syncope (fainting)", "cc_emesis": "Vomiting",
             "cc_drugproblem": "Drug problem", "cc_seizure-priorhxof": "Seizure (known history)",
             "cc_medicalproblem": "Medical problem", "cc_legpain": "Leg pain", "cc_assaultvictim": "Assault",
             "cc_cough": "Cough", "cc_alcoholproblem": "Alcohol problem",
             "cc_headache-newonsetornewsymptoms": "Headache, new", "cc_anxiety": "Anxiety"}


def pretty_cc(c):
    return CC_PRETTY.get(c, c[3:] if c else "Unknown")
