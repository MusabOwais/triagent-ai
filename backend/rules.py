"""Bed-type suggestion, protocol alerts, deterioration alerts and the pending list (docs/CONTRACT.md A5)."""
from datetime import datetime, timedelta
import config
import news2 as N
from scoring import ai_flag_state

BED_LABEL = {"icu_review": "ICU review", "telemetry": "Telemetry (heart-monitored)",
             "isolation": "Possible isolation", "floor": "Regular floor"}


def parse(t):
    return datetime.fromisoformat(t)


def latest(vitals, key):
    for v in reversed(vitals):
        if v.get(key) is not None:
            return v[key]
    return None


def bed_type(patient, news):
    """Draft rules, first match wins. Returns {suggested, reason}."""
    vit = patient.get("vitals", [])
    gcs = latest(vit, "gcs")
    if news["value"] >= 7:  # a partial sum of 7+ is already a lower bound, so it counts even if incomplete
        return {"suggested": "icu_review", "reason": f"NEWS2 {news['value']} (7 or more)"
                + ("" if news["complete"] else f", from {news['present']}/7 parameters")}
    if gcs is not None and gcs <= 8:
        return {"suggested": "icu_review", "reason": f"GCS {gcs} (8 or less)"}
    if ai_flag_state(patient, "ecg") in ("unreviewed", "confirmed"):
        return {"suggested": "telemetry", "reason": "Abnormal ECG (AI flag" + (", unreviewed)" if ai_flag_state(patient, "ecg") == "unreviewed" else ", confirmed)")}
    temp = latest(vit, "temp_c")
    if (ai_flag_state(patient, "xray") in ("unreviewed", "confirmed")
            and "Pneumonia" in patient["xray"]["result"].get("flagged", []) and temp is not None and temp >= 38.1):
        return {"suggested": "isolation", "reason": f"X-ray flags pneumonia (AI) and temperature {temp} °C"}
    return {"suggested": "floor", "reason": "No other rule matched"}


def protocol_alerts(patient, now):
    alerts = []
    c = patient["complaint_category"]
    if c == "chest_pain" and not patient.get("ecg"):
        if patient.get("arrival_time"):
            due = parse(patient["arrival_time"]) + timedelta(minutes=config.ECG_DUE_MIN)
            overdue = now > due
            alerts.append({"kind": "protocol", "level": "critical" if overdue else "warning",
                           "message": "ECG overdue (due within 10 min of arrival)" if overdue else "ECG due within 10 min of arrival",
                           "due_at": due.isoformat()})
        else:
            alerts.append({"kind": "protocol", "level": "warning",
                           "message": "Chest pain: ECG due within 10 min of arrival", "due_at": None})
    if c == "stroke_signs":
        alerts.append({"kind": "protocol", "level": "critical", "message": "Stroke alert", "due_at": None})
        g = latest(patient.get("vitals", []), "glucose_mg_dl")
        if g is not None and g < 70:
            alerts.append({"kind": "protocol", "level": "warning",
                           "message": "Low blood sugar can mimic stroke — check glucose", "due_at": None})
    return alerts


def deterioration_alerts(vitals):
    """Fire only when NEWS2 rises between the two latest COMPLETE sets by >= 2, or crosses into a higher band."""
    sets = [N.compute(v) for v in vitals]
    complete = [s for s in sets if s["complete"]]
    out = []
    if len(complete) >= 2:
        prev, cur = complete[-2], complete[-1]
        order = {"low": 0, "medium": 1, "high": 2}
        rise = cur["value"] - prev["value"]
        if rise >= 2 or order[cur["band"]] > order[prev["band"]]:
            out.append({"kind": "deterioration", "level": "critical" if cur["band"] == "high" else "warning",
                        "message": f"NEWS2 rose from {prev['value']} to {cur['value']}"
                                   + (f" (now {cur['band']} band)" if cur["band"] != prev["band"] else ""),
                        "due_at": None})
    if config.NEWS2_STATUS_ALERTS and complete:
        cur = complete[-1]
        if cur["value"] >= 7:
            out.append({"kind": "deterioration", "level": "critical",
                        "message": f"NEWS2 {cur['value']}: emergency review (NEWS2 guidance)", "due_at": None})
        elif 3 in cur["parts"].values():
            out.append({"kind": "deterioration", "level": "warning",
                        "message": "A single NEWS2 parameter scores 3: urgent review", "due_at": None})
    return out


def pending(patient, news):
    p = []
    if patient["status"] == "en_route":
        p.append("Patient en route")
    if not news["complete"]:
        p.append(f"Vitals incomplete ({news['present']}/7 NEWS2 parameters)")
    if patient["status"] != "en_route" and patient.get("esi") is None:
        p.append("ESI not yet assigned")
    if not patient.get("ecg"):
        p.append("ECG not yet recorded")
    if not patient.get("xray"):
        p.append("X-ray read pending")
    for kind, name in (("ecg", "ECG"), ("xray", "X-ray")):
        if ai_flag_state(patient, kind) == "unreviewed":
            p.append(f"{name} AI flag awaiting clinician review")
    if not patient.get("bed_request") and patient["status"] != "en_route":
        p.append("Bed request not sent")
    return p
