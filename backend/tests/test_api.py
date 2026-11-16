"""API smoke tests: every A6 endpoint answers with the contract shape."""
from fastapi.testclient import TestClient
import app as A

c = TestClient(A.app)
VIEW_KEYS = {"patient", "scores", "bed_type", "alerts", "pending", "handoff"}
SCORE_KEYS = {"admission", "news2", "findings", "parts", "priority", "wait_minutes", "queue_rank_score"}


def check(v):
    assert VIEW_KEYS <= v.keys() and SCORE_KEYS <= v["scores"].keys()
    assert {"A", "B", "C"} == set(v["scores"]["parts"])
    assert v["handoff"]["mist"] and v["handoff"]["sbar"]


def setup_function():
    c.post("/demo/reset")


def test_board_and_seed_story():
    b = c.get("/board").json()
    assert len(b) == 6
    for v in b: check(v)
    by = {v["patient"]["id"]: v for v in b}
    assert b[-1]["patient"]["status"] == "en_route" and b[-1]["scores"]["queue_rank_score"] is None
    assert any(a["kind"] == "protocol" for a in by["P-001"]["alerts"])                 # ECG countdown
    assert any(a["kind"] == "deterioration" for a in by["P-002"]["alerts"])            # NEWS2 3 -> 6
    assert by["P-003"]["bed_type"]["suggested"] == "isolation"                         # pneumonia + fever
    assert by["P-004"]["scores"]["parts"]["C"] == 7 and by["P-004"]["bed_type"]["suggested"] == "floor"
    assert by["P-005"]["scores"]["queue_rank_score"] >= by["P-005"]["scores"]["priority"] + 12  # long wait
    assert any("mimic stroke" in a["message"] for a in by["P-006"]["alerts"])


def test_full_flow():
    v = c.post("/patients", json={"name": "Test (fictional)", "age": 60, "sex": "F", "complaint_category": "chest_pain",
                                  "vitals": {"resp_rate": 18, "spo2": 97, "on_oxygen": False, "sbp": 130, "dbp": 80,
                                             "heart_rate": 88, "temp_c": 36.9, "avpu": "A"},
                                  "treatments": [{"what": "Aspirin 324 mg PO"}]}).json()
    check(v); pid = v["patient"]["id"]
    assert v["patient"]["status"] == "en_route" and v["patient"]["vitals"][0]["source"] == "ambulance"
    assert c.post(f"/patients/{pid}/bed-request", json={"bed_type": "floor", "confirmed_by": "RN"}).status_code == 409
    check(c.post(f"/patients/{pid}/arrive").json())
    assert c.post(f"/patients/{pid}/arrive").status_code == 409
    before = c.get(f"/patients/{pid}").json()["scores"]["priority"]
    check(c.post(f"/patients/{pid}/vitals", json={"heart_rate": 92, "resp_rate": 18}).json())
    check(c.post(f"/patients/{pid}/triage", json={"esi": 2}).json())
    v = c.post(f"/patients/{pid}/ecg", json={"record_id": "ptbxl_14912"}).json()
    assert v["scores"]["parts"]["C"] == 10 and v["bed_type"]["suggested"] == "telemetry"
    v = c.post(f"/patients/{pid}/review", json={"type": "ecg", "normal": True, "by": "MD Demo"}).json()
    assert v["scores"]["parts"]["C"] == 0
    v = c.post(f"/patients/{pid}/xray", json={"image_id": "00000842_000.png"}).json(); check(v)
    v = c.post(f"/patients/{pid}/bed-request", json={"bed_type": "floor", "confirmed_by": "Charge RN Demo"}).json()
    assert v["patient"]["status"] == "bed_requested"
    assert isinstance(before, int)


def test_errors_are_clear():
    assert c.get("/patients/P-999").status_code == 404
    assert c.post("/patients/P-001/review", json={"type": "ecg", "normal": True, "by": "x"}).status_code == 409
    assert c.post("/patients", json={"name": "x", "age": 50, "sex": "M", "complaint_category": "headache"}).status_code == 422


def test_static_endpoints():
    r = c.get("/rules").json(); assert "Bed priority" in r["text"]
    assert c.get("/metrics").status_code == 200
    a = c.get("/demo/assets").json(); assert a["ecg"] and a["xray"]


def test_ml_failure_falls_back_to_labelled_stub(monkeypatch):
    import ml_bridge as ML

    def boom(*a, **k):
        raise RuntimeError("model not trained")
    monkeypatch.setattr(ML, "_try", lambda name, fb: (boom, "real"))
    f = ML._guard("flag_ecg", ML._stub_flag_ecg)
    out = f("ptbxl_14912")
    assert out["model"] == "stub" and "unavailable" in out["note"] and ML.STATUS["flag_ecg"].startswith("stub fallback")
