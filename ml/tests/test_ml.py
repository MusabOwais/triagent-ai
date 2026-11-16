"""Contract tests for the three ML functions. Run from the repo root:  python -m pytest ml/tests -q
Tests for a model are skipped until that model has been trained/evaluated."""
import json
import time

import pytest

from ml import common

COMPLAINTS = ["chest_pain", "shortness_of_breath", "stroke_signs", "abdominal_pain", "trauma",
              "altered_mental_status", "fever_infection", "other"]
EX = {"age": 67, "sex": "M", "arrival_mode": "ambulance", "complaint_category": "chest_pain",
      "heart_rate": 112, "sbp": 105, "dbp": 70, "resp_rate": 22, "spo2": 94, "temp_c": 37.2,
      "on_oxygen": False, "esi": 2}

yale = pytest.mark.skipif(not (common.ARTIFACTS / "yale_meta.json").exists(), reason="Yale not trained")
ecg_ready = pytest.mark.skipif(not ((common.ARTIFACTS / "ecg_config.json").exists() and common.DEMO_JSON.exists()),
                               reason="ECG / demo assets not built")
xray_ready = pytest.mark.skipif(not ((common.ARTIFACTS / "xray_config.json").exists() and common.DEMO_JSON.exists()),
                                reason="X-ray / demo assets not built")


@yale
@pytest.mark.parametrize("stage", ["ambulance", "triage"])
def test_admission_contract(stage):
    from ml import predict_admission
    r = predict_admission(EX, stage)
    assert set(r) == {"probability", "stage", "model", "top_reasons"}
    assert 0.0 <= r["probability"] <= 1.0 and r["stage"] == stage
    assert r["model"] == f"yale_xgb_{stage}_v1"
    assert len(r["top_reasons"]) <= 3
    assert all(set(x) == {"label", "direction"} and x["direction"] in ("up", "down") for x in r["top_reasons"])
    dirs = [x["direction"] for x in r["top_reasons"]]
    assert dirs == sorted(dirs, key=lambda d: d == "down"), "'up' reasons must come first"


@yale
def test_admission_triage_without_esi_falls_back():
    from ml import predict_admission
    r = predict_admission({**EX, "esi": None}, "triage")
    assert r["stage"] == "ambulance" and r["model"] == "yale_xgb_ambulance_v1"


@yale
def test_admission_all_complaints_and_missing_values():
    from ml import predict_admission
    for c in COMPLAINTS:
        assert 0 <= predict_admission({**EX, "complaint_category": c}, "triage")["probability"] <= 1
    sparse = {"age": 50, "sex": None, "arrival_mode": "ambulance", "complaint_category": "other"}
    r = predict_admission(sparse, "ambulance")
    assert all("not" not in x["label"] for x in r["top_reasons"])  # never explains with unentered values


@yale
@pytest.mark.parametrize("bad", [{"complaint_category": "headache"}, {"age": 12}, {"sex": "X"},
                                 {"arrival_mode": "helicopter"}])
def test_admission_rejects_bad_input(bad):
    from ml import predict_admission
    with pytest.raises(ValueError):
        predict_admission({**EX, **bad}, "triage")


@yale
def test_admission_latency():
    from ml import predict_admission
    t = time.perf_counter()
    for _ in range(20):
        predict_admission(EX, "triage")
    assert (time.perf_counter() - t) / 20 < 1.0


@ecg_ready
def test_ecg_contract_and_latency():
    from ml import flag_ecg
    rid = json.loads(common.DEMO_JSON.read_text())["ecg"][0]["record_id"]
    t = time.perf_counter()
    r = flag_ecg(rid)
    assert time.perf_counter() - t < 1.0
    assert set(r) == {"abnormal_prob", "abnormal", "threshold", "model", "note"}
    assert r["abnormal"] == (r["abnormal_prob"] >= r["threshold"])
    assert r["note"].startswith("AI flag, not a diagnosis")
    assert flag_ecg(rid.replace("ptbxl_", ""))["abnormal_prob"] == r["abnormal_prob"]  # both id forms
    with pytest.raises(KeyError):
        flag_ecg("ptbxl_99999999")


@xray_ready
def test_xray_contract_and_latency():
    from ml import flag_xray
    iid = json.loads(common.DEMO_JSON.read_text())["xray"][0]["image_id"]
    t = time.perf_counter()
    r = flag_xray(iid)
    assert time.perf_counter() - t < 1.0
    assert set(r) == {"findings", "flagged", "thresholds", "model", "note"}
    assert set(r["findings"]) == {"Pneumonia", "Effusion", "Edema", "Cardiomegaly", "Pneumothorax"}
    assert r["flagged"] == [f for f in r["findings"] if r["findings"][f] >= r["thresholds"][f]]
    with pytest.raises(KeyError):
        flag_xray("not_a_demo_image.png")


def test_demo_assets_are_held_out():
    if not common.DEMO_JSON.exists():
        pytest.skip("demo assets not built")
    d = json.loads(common.DEMO_JSON.read_text())
    xcfg = common.ARTIFACTS / "xray_config.json"
    if xcfg.exists():
        half_b = set(json.loads(xcfg.read_text())["eval_half_b_ids"])
        assert all(x["image_id"] in half_b for x in d["xray"]), "demo X-ray not from evaluation half B"
    assert not d.get("consistency_problems"), d.get("consistency_problems")
