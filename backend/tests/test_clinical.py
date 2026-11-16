"""Clinical logic tests (B6). Run from backend/:  python -m pytest -q"""
from datetime import datetime, timedelta, timezone
import pytest
import config, news2 as N, rules as R, scoring as S

NORMAL = dict(resp_rate=16, spo2=98, on_oxygen=False, sbp=120, heart_rate=75, avpu="A", temp_c=37.0)


# ---------- NEWS2 band edges, one parameter at a time ----------
@pytest.mark.parametrize("key,value,points", [
    ("resp_rate", 8, 3), ("resp_rate", 9, 1), ("resp_rate", 11, 1), ("resp_rate", 12, 0), ("resp_rate", 20, 0),
    ("resp_rate", 21, 2), ("resp_rate", 24, 2), ("resp_rate", 25, 3),
    ("spo2", 91, 3), ("spo2", 92, 2), ("spo2", 93, 2), ("spo2", 94, 1), ("spo2", 95, 1), ("spo2", 96, 0),
    ("on_oxygen", True, 2), ("on_oxygen", False, 0),
    ("sbp", 90, 3), ("sbp", 91, 2), ("sbp", 100, 2), ("sbp", 101, 1), ("sbp", 110, 1), ("sbp", 111, 0),
    ("sbp", 219, 0), ("sbp", 220, 3),
    ("heart_rate", 40, 3), ("heart_rate", 41, 1), ("heart_rate", 50, 1), ("heart_rate", 51, 0), ("heart_rate", 90, 0),
    ("heart_rate", 91, 1), ("heart_rate", 110, 1), ("heart_rate", 111, 2), ("heart_rate", 130, 2), ("heart_rate", 131, 3),
    ("temp_c", 35.0, 3), ("temp_c", 35.1, 1), ("temp_c", 36.0, 1), ("temp_c", 36.1, 0), ("temp_c", 38.0, 0),
    ("temp_c", 38.1, 1), ("temp_c", 39.0, 1), ("temp_c", 39.1, 2),
])
def test_news2_edges(key, value, points):
    r = N.compute({**NORMAL, key: value})
    assert r["value"] == points and r["complete"]


@pytest.mark.parametrize("avpu,gcs,points", [("A", None, 0), ("C", None, 3), ("V", None, 3), ("P", None, 3), ("U", None, 3),
                                             (None, 15, 0), (None, 14, 3), (None, 3, 3), ("A", 9, 0)])
def test_consciousness_avpu_then_gcs(avpu, gcs, points):
    v = {**NORMAL, "avpu": avpu, "gcs": gcs}
    assert N.compute(v)["value"] == points


def test_full_patients_known_totals():
    assert N.compute(NORMAL)["value"] == 0
    sick = dict(resp_rate=26, spo2=90, on_oxygen=True, sbp=88, heart_rate=135, avpu="V", temp_c=39.5)
    assert N.compute(sick)["value"] == 3 + 3 + 2 + 3 + 3 + 3 + 2
    mid = dict(resp_rate=22, spo2=94, on_oxygen=False, sbp=105, heart_rate=95, avpu="A", temp_c=38.2)
    r = N.compute(mid)
    assert r["value"] == 2 + 1 + 0 + 1 + 1 + 0 + 1 and r["band"] == "medium"


def test_bands():
    assert [N.band(x) for x in (0, 4, 5, 6, 7, 20)] == ["low", "low", "medium", "medium", "high", "high"]


def test_incomplete_vitals():
    v = {k: NORMAL[k] for k in ("resp_rate", "spo2", "sbp")}
    r = N.compute(v)
    assert not r["complete"] and r["present"] == 3


def test_incomplete_sets_never_trigger_deterioration():
    low = {**NORMAL}
    high_incomplete = {"resp_rate": 30, "spo2": 85, "heart_rate": 140}
    assert R.deterioration_alerts([low, high_incomplete]) == []


# ---------- deterioration ----------
def test_deterioration_fires_on_rise_of_two():
    a, b = {**NORMAL, "heart_rate": 95}, {**NORMAL, "heart_rate": 95, "resp_rate": 22}  # 1 -> 3
    assert len(R.deterioration_alerts([a, b])) == 1


def test_deterioration_fires_on_band_crossing_by_one():
    a = {**NORMAL, "resp_rate": 22, "heart_rate": 95, "spo2": 95}           # 2+1+1 = 4 (low)
    b = {**NORMAL, "resp_rate": 22, "heart_rate": 95, "spo2": 95, "temp_c": 38.5}  # 5 (medium)
    assert len(R.deterioration_alerts([a, b])) == 1


def test_no_alert_on_steady_high():
    high = dict(resp_rate=26, spo2=90, on_oxygen=True, sbp=88, heart_rate=135, avpu="V", temp_c=39.5)
    assert R.deterioration_alerts([high]) == []
    assert R.deterioration_alerts([high, high]) == []


def test_no_alert_on_fall():
    high = dict(resp_rate=26, spo2=90, on_oxygen=True, sbp=88, heart_rate=135, avpu="V", temp_c=39.5)
    assert R.deterioration_alerts([high, NORMAL]) == []


# ---------- priority, cap, queue ----------
def test_priority_formula_and_cap():
    assert S.priority(72, 30, 15) == 66   # contract example
    assert S.priority(100, 100, 30) == 100
    assert S.priority(0, 0, 0) == 0


def test_queue_rank_points():
    assert S.queue_rank(40, 14) == 40
    assert S.queue_rank(40, 15) == 41
    assert S.queue_rank(40, 190) == 52
    assert S.queue_rank(40, None) is None


def test_priority_floor_is_off_by_default():
    news = N.compute(dict(resp_rate=26, spo2=90, on_oxygen=True, sbp=120, heart_rate=75, avpu="A", temp_c=37))  # 8
    assert not config.NEWS2_PRIORITY_FLOOR
    assert S.priority(10, 40, 0, news) == 25


def test_priority_floor_when_enabled(monkeypatch):
    monkeypatch.setattr(config, "NEWS2_PRIORITY_FLOOR", True)
    news = N.compute(dict(resp_rate=26, spo2=90, on_oxygen=True, sbp=120, heart_rate=75, avpu="A", temp_c=37))
    assert S.priority(10, 40, 0, news) == config.FLOOR_HIGH


# ---------- raise-only ----------
T0, T1, T2 = "2026-11-15T20:00:00+00:00", "2026-11-15T20:05:00+00:00", "2026-11-15T20:10:00+00:00"


def pt(**kw):
    base = {"complaint_category": "other", "injuries": [], "reviews": [], "ecg": None, "xray": None, "vitals": [], "status": "waiting"}
    return {**base, **kw}


def ecg(abnormal, t=T0):
    return {"record_id": "x", "time": t, "result": {"abnormal": abnormal, "abnormal_prob": 0.9 if abnormal else 0.1}}


def test_normal_ai_result_adds_nothing():
    assert S.findings(pt())["points"] == S.findings(pt(ecg=ecg(False)))["points"] == 0


def test_abnormal_ai_adds_ten_and_clinician_review_removes_it():
    p = pt(ecg=ecg(True))
    assert S.findings(p)["points"] == 10
    p["reviews"].append({"type": "ecg", "normal": True, "by": "RN", "time": T1})
    assert S.findings(p)["points"] == 0


def test_clinician_confirming_abnormal_keeps_points():
    p = pt(ecg=ecg(True), reviews=[{"type": "ecg", "normal": False, "by": "MD", "time": T1}])
    assert S.findings(p)["points"] == 10 and "confirmed" in S.findings(p)["items"][0]["label"]


def test_old_review_does_not_clear_a_newer_abnormal_result():
    p = pt(ecg=ecg(True, T2), reviews=[{"type": "ecg", "normal": True, "by": "RN", "time": T1}])
    assert S.findings(p)["points"] == 10


def test_repeat_normal_ai_read_does_not_clear_flag():
    import app
    p = pt(ecg=ecg(True))
    app.record_ecg(p, "ptbxl_19669", T1)  # stub says normal
    assert S.findings(p)["points"] == 10 and p["notes"]


def test_injury_points_are_labelled_draft():
    f = S.findings(pt(injuries=["suspected_fracture", "minor_wound"]))
    assert f["points"] == 7 and all("draft" in i["label"] for i in f["items"])


# ---------- bed type order ----------
def test_bed_rule_order():
    sick = N.compute(dict(resp_rate=26, spo2=90, on_oxygen=True, sbp=120, heart_rate=75, avpu="A", temp_c=37))
    ok = N.compute(NORMAL)
    pneu = {"image_id": "i", "time": T0, "result": {"flagged": ["Pneumonia"]}}
    feverish = [{**NORMAL, "temp_c": 38.5}]
    assert R.bed_type(pt(ecg=ecg(True)), sick)["suggested"] == "icu_review"            # rule 1 beats rule 2
    assert R.bed_type(pt(vitals=[{**NORMAL, "gcs": 8}]), ok)["suggested"] == "icu_review"
    assert R.bed_type(pt(ecg=ecg(True), xray=pneu, vitals=feverish), ok)["suggested"] == "telemetry"  # 2 beats 3
    assert R.bed_type(pt(xray=pneu, vitals=feverish), ok)["suggested"] == "isolation"
    assert R.bed_type(pt(xray=pneu, vitals=[{**NORMAL, "temp_c": 38.0}]), ok)["suggested"] == "floor"
    assert R.bed_type(pt(), ok)["suggested"] == "floor"


def test_reviewed_normal_ecg_no_longer_suggests_telemetry():
    p = pt(ecg=ecg(True), reviews=[{"type": "ecg", "normal": True, "by": "RN", "time": T1}])
    assert R.bed_type(p, N.compute(NORMAL))["suggested"] == "floor"


# ---------- protocol alerts ----------
def test_ecg_countdown_turns_critical_after_ten_minutes():
    arr = datetime(2026, 11, 15, 20, 0, tzinfo=timezone.utc)
    p = pt(complaint_category="chest_pain", arrival_time=arr.isoformat())
    assert R.protocol_alerts(p, arr + timedelta(minutes=9, seconds=59))[0]["level"] == "warning"
    assert R.protocol_alerts(p, arr + timedelta(minutes=10, seconds=1))[0]["level"] == "critical"
    p["ecg"] = ecg(False)
    assert R.protocol_alerts(p, arr + timedelta(minutes=30)) == []


def test_stroke_alert_and_low_glucose():
    p = pt(complaint_category="stroke_signs", vitals=[{**NORMAL, "glucose_mg_dl": 62}])
    msgs = [a["message"] for a in R.protocol_alerts(p, datetime.now(timezone.utc))]
    assert "Stroke alert" in msgs and any("mimic stroke" in m for m in msgs)
    p["vitals"] = [{**NORMAL, "glucose_mg_dl": 110}]
    assert len(R.protocol_alerts(p, datetime.now(timezone.utc))) == 1
