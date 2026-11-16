"""NEWS2 (Royal College of Physicians, 2017), SpO2 Scale 1 only, exactly as docs/CONTRACT.md A5.
Scale 2 (patients with chronic CO2 retention, target SpO2 88-92%) is NOT implemented."""

PARAMS = ["resp_rate", "spo2", "on_oxygen", "sbp", "heart_rate", "consciousness", "temp_c"]


def _rr(x):   return 3 if x <= 8 else 1 if x <= 11 else 0 if x <= 20 else 2 if x <= 24 else 3
def _spo2(x): return 3 if x <= 91 else 2 if x <= 93 else 1 if x <= 95 else 0
def _o2(on):  return 2 if on else 0
def _sbp(x):  return 3 if x <= 90 else 2 if x <= 100 else 1 if x <= 110 else 0 if x <= 219 else 3
def _hr(x):   return 3 if x <= 40 else 1 if x <= 50 else 0 if x <= 90 else 1 if x <= 110 else 2 if x <= 130 else 3
def _temp(x): return 3 if x <= 35.0 else 1 if x <= 36.0 else 0 if x <= 38.0 else 1 if x <= 39.0 else 2


def _consciousness(v):
    """AVPU first ('A' = 0, anything else = 3); else GCS (15 = alert = 0, below 15 = 3); else missing."""
    if v.get("avpu") is not None:
        return 0 if v["avpu"] == "A" else 3
    if v.get("gcs") is not None:
        return 0 if v["gcs"] >= 15 else 3
    return None


def band(value):
    return "high" if value >= 7 else "medium" if value >= 5 else "low"


def compute(v: dict) -> dict:
    """Returns {value, band, complete, present, parts}. value sums only the parameters present."""
    fns = {"resp_rate": _rr, "spo2": _spo2, "on_oxygen": _o2, "sbp": _sbp, "heart_rate": _hr, "temp_c": _temp}
    parts = {}
    for k, f in fns.items():
        if v.get(k) is not None:
            parts[k] = f(v[k])
    c = _consciousness(v)
    if c is not None:
        parts["consciousness"] = c
    value = sum(parts.values())
    return {"value": value, "band": band(value), "complete": len(parts) == 7, "present": len(parts), "parts": parts}


def trend(vitals_list: list) -> dict:
    """Latest complete set vs the previous complete set."""
    complete = [compute(v) for v in vitals_list if compute(v)["complete"]]
    if len(complete) < 2:
        return {"trend": None, "previous": None}
    cur, prev = complete[-1]["value"], complete[-2]["value"]
    return {"trend": "up" if cur > prev else "down" if cur < prev else "flat", "previous": prev}
