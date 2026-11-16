"""MIST (ambulance -> ER) and SBAR (ER -> floor nurse) handoffs, built only from the record with fixed templates.
Missing fields say 'not recorded'. No diagnoses are added."""
from datetime import datetime
from rules import BED_LABEL
from scoring import ai_flag_state

NR = "not recorded"
COMPLAINT = {"chest_pain": "chest pain", "shortness_of_breath": "shortness of breath", "stroke_signs": "stroke signs",
             "abdominal_pain": "abdominal pain", "trauma": "trauma", "altered_mental_status": "altered mental status",
             "fever_infection": "fever / infection", "other": "other"}


def _t(iso):
    """ISO time -> local HH:MM."""
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%H:%M")
    except (TypeError, ValueError):
        return NR


def _vitals_line(v):
    if not v:
        return NR
    f = lambda k, unit="": f"{v[k]:g}{unit}" if v.get(k) is not None else NR
    bp = f"{v['sbp']:g}/{v['dbp']:g}" if v.get("sbp") is not None and v.get("dbp") is not None else (f("sbp") if v.get("sbp") is not None else NR)
    o2 = NR if v.get("on_oxygen") is None else ("on oxygen" if v["on_oxygen"] else "room air")
    cons = v.get("avpu") or (f"GCS {v['gcs']}" if v.get("gcs") is not None else NR)
    return (f"HR {f('heart_rate')}, BP {bp}, RR {f('resp_rate')}, SpO2 {f('spo2', '%')} ({o2}), "
            f"temp {f('temp_c', ' °C')}, consciousness {cons}, pain {f('pain', '/10')}"
            + (f", rhythm {v['rhythm']}" if v.get("rhythm") else "")
            + (f", glucose {v['glucose_mg_dl']:g} mg/dL" if v.get("glucose_mg_dl") is not None else ""))


def _ai_line(patient, kind, name):
    res = patient.get(kind)
    if not res:
        return f"{name}: not yet done"
    r, st = res["result"], ai_flag_state(patient, kind)
    if kind == "ecg":
        what = f"AI flag abnormal (p={r['abnormal_prob']:.2f})" if r.get("abnormal") else "no AI flag"
    else:
        what = f"AI flags {', '.join(r['flagged'])}" if r.get("flagged") else "no AI flag"
    review = {"none": "", "unreviewed": ", not yet reviewed by a clinician", "confirmed": ", confirmed by clinician",
              "cleared": ", reviewed by clinician as normal"}[st]
    return f"{name}: {what}{review} (model {r.get('model', NR)}; AI flag, not a diagnosis)"


def mist(patient, news):
    amb = [v for v in patient.get("vitals", []) if v.get("source") == "ambulance"]
    inj = ", ".join(i.replace("_", " ") for i in patient.get("injuries", [])) or "none recorded"
    tx = "; ".join(f"{_t(t.get('time'))} {t['what']}" for t in patient.get("treatments", [])) or NR
    return (f"M — Mechanism/complaint: {COMPLAINT[patient['complaint_category']]}"
            f"{': ' + patient['complaint_text'] if patient.get('complaint_text') else ''}. Onset {_t(patient.get('onset_time'))}.\n"
            f"I — Injuries: {inj}.\n"
            f"S — Signs (latest ambulance set): {_vitals_line(amb[-1] if amb else None)}. "
            f"NEWS2 {news['value']}" + ("" if news["complete"] else f" (incomplete, {news['present']}/7)") + ".\n"
            f"T — Treatment: {tx}.")


def sbar(patient, news, trend, admission, bed, alerts, pend):
    vit = patient.get("vitals", [])
    tr = f", trend {trend['trend']} from {trend['previous']}" if trend.get("trend") else ""
    rec = [a["message"] for a in alerts] + pend
    return (f"S — {patient['age']}-year-old {'man' if patient['sex'] == 'M' else 'woman'}, "
            f"{COMPLAINT[patient['complaint_category']]}. Suggested bed: {BED_LABEL[bed['suggested']]} ({bed['reason']}).\n"
            f"B — History: {patient.get('history') or NR}. Medications: {patient.get('medications') or NR}. "
            f"Allergies: {patient.get('allergies') or NR}. ESI: {patient.get('esi') or NR}.\n"
            f"A — Latest vitals: {_vitals_line(vit[-1] if vit else None)}. NEWS2 {news['value']} ({news['band']}"
            + ("" if news["complete"] else f", incomplete {news['present']}/7") + f"){tr}. "
            f"Admission likelihood {round(admission['probability'] * 100)}% (model {admission.get('model', NR)}). "
            f"{_ai_line(patient, 'ecg', 'ECG')}. {_ai_line(patient, 'xray', 'X-ray')}.\n"
            f"R — Items to check: " + ("; ".join(rec) if rec else "none outstanding") + ".")
