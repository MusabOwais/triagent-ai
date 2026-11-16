"""Safety and correctness tests for app/scoring.py. Run from the project root: python -m pytest -q"""
import math
from app import scoring as S

NORMAL = dict(age=30, male=False, hr=75, sbp=120, dbp=78, rr=16, spo2=98, temp_f=98.6, o2=False, gcs=15, pain=0,
              rhythm="sinus", injuries=[])


def test_news2_normal_is_zero():
    total, parts = S.news2(NORMAL)
    assert total == 0 and S.news2_floor(total, parts) == 0


def test_news2_textbook_case():
    # RR 26 (3) + SpO2 90 (3) + O2 (2) + SBP 95 (2) + HR 120 (2) + GCS 14 (3) + 38.5 C (1) = 16
    v = {**NORMAL, "rr": 26, "spo2": 90, "o2": True, "sbp": 95, "hr": 120, "gcs": 14, "temp_f": 101.3}
    total, parts = S.news2(v)
    assert total == 16 and S.news2_floor(total, parts) == 80


def test_single_red_parameter_floor():
    total, parts = S.news2({**NORMAL, "rr": 7})
    assert parts["RR"] == 3 and S.news2_floor(total, parts) == 45


def test_floor_overrides_low_model_score():
    v = {**NORMAL, "rr": 26, "spo2": 90, "o2": True, "sbp": 88}
    r = S.ambulance_score(v, "cc_alcoholintoxication")
    assert r["score"] >= 80 and r["score"] >= r["score_raw"]


def test_model_a_worked_example_from_formulas_page():
    # 70 y, HR 118, SBP 95, RR 24, SpO2 92 on O2, temp 101 F -> logit 4.018 -> score 98
    v = {**NORMAL, "age": 70, "hr": 118, "sbp": 95, "rr": 24, "spo2": 92, "o2": True, "temp_f": 101.0}
    L, _, which = S.model_logit(v, None)
    assert which == "A" and abs(L - 4.018) < 0.01 and S.to_score(L) == 98


def test_score_always_in_range():
    for L in (-50, -5, 0, 5, 50):
        assert 1 <= S.to_score(L) <= 100


def test_ecg_drop_is_capped():
    d = S.ecg_delta({"NORM": 1.0, "MI": 0.0, "STTC": 0.0, "CD": 0.0, "HYP": 0.0})
    assert d["delta"] >= -S.MAX_DROP


def test_ecg_unsure_model_cannot_lower():
    d = S.ecg_delta({"NORM": 0.65, "MI": 0.01, "STTC": 0.01, "CD": 0.01, "HYP": 0.01})
    assert d["delta_raw"] < 0 and d["delta"] == 0


def test_ecg_mi_raises_score():
    assert S.ecg_delta({"NORM": 0.05, "MI": 0.9, "STTC": 0.1, "CD": 0.0, "HYP": 0.0})["delta"] > 2


def test_xray_never_lowers_in_poc():
    clean = {c: 0.01 for c in S.CXR_W}
    d = S.cxr_delta(clean)
    assert d["delta_raw"] < 0 and d["delta"] == 0


def test_bed_rules():
    assert S.provisional_bed(7, "cc_fall")[0] == "ICU"
    assert S.provisional_bed(2, "cc_chestpain")[0] == "Telemetry"
    assert S.provisional_bed(2, "cc_suicidal")[0] == "Psychiatric"
    assert S.provisional_bed(6, "cc_suicidal")[0] == "General ward"
    assert S.provisional_bed(0, "cc_backpain")[0] == "General ward"
    mi = {"NORM": 0.1, "MI": 0.8, "STTC": 0.1, "CD": 0.1, "HYP": 0.0}
    assert S.bed_after_ecg("Telemetry", mi)[0] == "CCU"
    assert S.bed_after_ecg("ICU", mi)[0] == "ICU"


def test_waiting_time_raises_priority():
    assert S.priority(0.0, 60) > S.priority(0.0, 0)
    assert math.isclose(S.priority(0.0, 60) - S.priority(0.0, 0), 0.6)
