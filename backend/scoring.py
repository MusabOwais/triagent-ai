"""Bed-priority score, docs/CONTRACT.md A5.
priority = min(100, round((A + B) / 2 + C));  queue rank = priority + floor(minutes waited / 15)."""
import math
import config

INJURY_POINTS = {"minor_wound": 2, "suspected_fracture": 5, "open_fracture": 10, "minor_burn": 5,
                 "major_burn": 15, "heavy_bleeding": 15, "frostbite": 5}
INJURY_LABEL = {"minor_wound": "Minor wound", "suspected_fracture": "Suspected fracture", "open_fracture": "Open fracture",
                "minor_burn": "Minor burn", "major_burn": "Major burn", "heavy_bleeding": "Heavy bleeding",
                "frostbite": "Frostbite"}
AI_FINDING_POINTS = 10


def latest_review(patient, kind):
    """The newest clinician review of this test type made at or after the current result, else None."""
    res = patient.get(kind)
    if not res:
        return None
    revs = [r for r in patient.get("reviews", []) if r["type"] == kind and r["time"] >= res["time"]]
    return revs[-1] if revs else None


def ai_flag_state(patient, kind):
    """'none' (no result or AI says normal), 'unreviewed', 'confirmed' (clinician says abnormal), 'cleared' (clinician says normal)."""
    res = patient.get(kind)
    if not res:
        return "none"
    r = res["result"]
    flagged = r.get("abnormal") if kind == "ecg" else bool(r.get("flagged"))
    if not flagged:
        return "none"
    rev = latest_review(patient, kind)
    if rev is None:
        return "unreviewed"
    return "cleared" if rev["normal"] else "confirmed"


def findings(patient):
    items = []
    st = ai_flag_state(patient, "ecg")
    if st in ("unreviewed", "confirmed"):
        items.append({"source": "ecg", "points": AI_FINDING_POINTS,
                      "label": "Abnormal ECG (AI, unreviewed)" if st == "unreviewed" else "Abnormal ECG (AI, confirmed by clinician)"})
    st = ai_flag_state(patient, "xray")
    if st in ("unreviewed", "confirmed"):
        f = ", ".join(patient["xray"]["result"]["flagged"])
        items.append({"source": "xray", "points": AI_FINDING_POINTS,
                      "label": f"X-ray flags {f} (AI, {'unreviewed' if st == 'unreviewed' else 'confirmed by clinician'})"})
    for inj in patient.get("injuries", []):
        items.append({"source": "injury", "points": INJURY_POINTS[inj],
                      "label": f"{INJURY_LABEL[inj]} (draft — clinician review needed)"})
    return {"points": sum(i["points"] for i in items), "items": items}


def priority(A, B, C, news=None):
    p = min(100, round((A + B) / 2 + C))
    if config.NEWS2_PRIORITY_FLOOR and news and news["present"]:
        if news["value"] >= 7:
            p = max(p, config.FLOOR_HIGH)
        elif news["value"] >= 5:
            p = max(p, config.FLOOR_MEDIUM)
        elif 3 in news["parts"].values():
            p = max(p, config.FLOOR_SINGLE_3)
    return p


def queue_rank(prio, wait_minutes):
    if wait_minutes is None:
        return None  # en route: shown under "Incoming", unranked
    return prio + math.floor(wait_minutes / config.QUEUE_POINT_EVERY_MIN)
