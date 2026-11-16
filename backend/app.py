"""HackRx backend (Role 2). Run from backend/:  uvicorn app:app --port 8000
Every route matches docs/CONTRACT.md A6 and returns the computed view."""
import copy, json, math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import config, ml_bridge as ML, news2 as N, rules as R, scoring as S, summaries as SUM
from models import PatientCreate, Vitals, TriageIn, EcgIn, XrayIn, ReviewIn, BedRequestIn

HERE = Path(__file__).resolve().parent
app = FastAPI(title="HackRx backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])  # dev: Vite may use 5173 or 5174

STORE: dict = {}
_next = [1]


def utcnow():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def norm_time(t, now):
    """Normalise any ISO input to UTC ISO so string comparison of times is safe; missing -> now."""
    if not t:
        return iso(now)
    try:
        dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(422, f"'{t}' is not an ISO-8601 time, e.g. 2026-11-15T14:05:00-08:00.")
    if dt.tzinfo is None:
        dt = dt.astimezone()  # naive -> server local time
    return iso(dt)


# ---------------- computed view ----------------
def features(p):
    v = p.get("vitals", [])
    L = lambda k: R.latest(v, k)
    f = {"age": p["age"], "sex": p["sex"], "arrival_mode": "ambulance", "complaint_category": p["complaint_category"],
         "heart_rate": L("heart_rate"), "sbp": L("sbp"), "dbp": L("dbp"), "resp_rate": L("resp_rate"), "spo2": L("spo2"),
         "temp_c": L("temp_c"), "on_oxygen": L("on_oxygen")}
    if p.get("esi") is not None:
        f["esi"] = p["esi"]
    return f


def latest_complete_or_last(vitals):
    for v in reversed(vitals):
        if N.compute(v)["complete"]:
            return v
    return vitals[-1] if vitals else {}


def view(p, now=None):
    now = now or utcnow()
    stage = "triage" if p.get("esi") is not None else "ambulance"
    adm = ML.predict_admission(features(p), stage)
    vit = p.get("vitals", [])
    news = N.compute(latest_complete_or_last(vit))
    tr = N.trend(vit)
    fnd = S.findings(p)
    A, B, C = round(adm["probability"] * 100), news["value"] * 5, fnd["points"]
    prio = S.priority(A, B, C, news)
    wait = None if p["status"] == "en_route" or not p.get("arrival_time") else \
        max(0, math.floor((now - datetime.fromisoformat(p["arrival_time"])).total_seconds() / 60))
    bed = R.bed_type(p, news)
    alerts = R.protocol_alerts(p, now) + R.deterioration_alerts(vit)
    pend = R.pending(p, news)
    news_out = {"value": news["value"], "band": news["band"], "complete": news["complete"], "present": news["present"],
                "parts": news["parts"], "trend": tr["trend"], "previous": tr["previous"]}
    return {
        "patient": copy.deepcopy(p),
        "scores": {"admission": adm, "news2": news_out, "findings": fnd, "parts": {"A": A, "B": B, "C": C},
                   "priority": prio, "wait_minutes": wait, "queue_rank_score": S.queue_rank(prio, wait)},
        "bed_type": bed,
        "alerts": alerts,
        "pending": pend,
        "handoff": {"mist": SUM.mist(p, news), "sbar": SUM.sbar(p, news_out, tr, adm, bed, alerts, pend)},
    }


def get(pid):
    if pid not in STORE:
        raise HTTPException(404, f"No patient with id {pid}.")
    return STORE[pid]


def new_id():
    while f"P-{_next[0]:03d}" in STORE:
        _next[0] += 1
    return f"P-{_next[0]:03d}"


def add_vitals(p, v: dict, now):
    v = {**v, "time": norm_time(v.get("time"), now)}
    p.setdefault("vitals", []).append(v)
    p["vitals"].sort(key=lambda x: x["time"])


def record_ecg(p, record_id, t):
    res = ML.flag_ecg(record_id)
    old = p.get("ecg")
    # Raise-only on repeats: a normal AI re-read does not clear an earlier abnormal flag; only a clinician review does.
    if old and S.ai_flag_state(p, "ecg") == "unreviewed" and not res.get("abnormal"):
        p.setdefault("notes", []).append(f"{t}: repeat ECG {record_id} read normal by AI; earlier abnormal flag stands until clinician review.")
        return
    p["ecg"] = {"record_id": record_id, "result": res, "time": t}


def record_xray(p, image_id, t):
    res = ML.flag_xray(image_id)
    if p.get("xray") and S.ai_flag_state(p, "xray") == "unreviewed" and not res.get("flagged"):
        p.setdefault("notes", []).append(f"{t}: repeat X-ray {image_id} has no AI flag; earlier flag stands until clinician review.")
        return
    p["xray"] = {"image_id": image_id, "result": res, "time": t}


# ---------------- routes (A6) ----------------
@app.post("/patients")
def create(body: PatientCreate):
    now = utcnow()
    d = body.model_dump()
    v = d.pop("vitals")
    pid = new_id()
    p = {"id": pid, "demo": d.pop("demo"), **d, "vitals": [], "esi": None, "arrival_time": None, "status": "en_route",
         "ecg": None, "xray": None, "reviews": [], "bed_request": None, "created_time": iso(now)}
    p["onset_time"] = norm_time(p["onset_time"], now) if p["onset_time"] else None
    p["treatments"] = [{"time": norm_time(t.get("time"), now), "what": t["what"]} for t in p["treatments"]]
    if v:
        add_vitals(p, {**v, "source": "ambulance"}, now)
    STORE[pid] = p
    return view(p, now)


@app.post("/patients/{pid}/arrive")
def arrive(pid: str):
    p = get(pid)
    if p["status"] != "en_route":
        raise HTTPException(409, f"{pid} has already arrived.")
    now = utcnow()
    p["arrival_time"], p["status"] = iso(now), "waiting"
    return view(p, now)


@app.post("/patients/{pid}/vitals")
def vitals(pid: str, body: Vitals):
    p, now = get(pid), utcnow()
    add_vitals(p, body.model_dump(), now)
    return view(p, now)


@app.post("/patients/{pid}/triage")
def triage(pid: str, body: TriageIn):
    p, now = get(pid), utcnow()
    p["esi"] = body.esi
    if body.vitals:
        add_vitals(p, {**body.vitals.model_dump(), "source": "triage"}, now)
    return view(p, now)


@app.post("/patients/{pid}/ecg")
def ecg(pid: str, body: EcgIn):
    p, now = get(pid), utcnow()
    record_ecg(p, body.record_id, iso(now))
    return view(p, now)


@app.post("/patients/{pid}/xray")
def xray(pid: str, body: XrayIn):
    p, now = get(pid), utcnow()
    record_xray(p, body.image_id, iso(now))
    return view(p, now)


@app.post("/patients/{pid}/review")
def review(pid: str, body: ReviewIn):
    p, now = get(pid), utcnow()
    if not p.get(body.type):
        raise HTTPException(409, f"There is no {body.type.upper()} result to review for {pid}.")
    p["reviews"].append({"type": body.type, "normal": body.normal, "by": body.by, "time": iso(now)})
    return view(p, now)


@app.post("/patients/{pid}/bed-request")
def bed_request(pid: str, body: BedRequestIn):
    p, now = get(pid), utcnow()
    if p["status"] == "en_route":
        raise HTTPException(409, f"{pid} is still en route. Mark them arrived before requesting a bed.")
    p["bed_request"] = {"bed_type": body.bed_type, "confirmed_by": body.confirmed_by, "time": iso(now)}
    p["status"] = "bed_requested"
    return view(p, now)


@app.get("/patients/{pid}")
def one(pid: str):
    return view(get(pid))


@app.get("/board")
def board():
    now = utcnow()
    vs = [view(p, now) for p in STORE.values()]
    return sorted(vs, key=lambda v: (v["scores"]["queue_rank_score"] is None, -(v["scores"]["queue_rank_score"] or 0)))


RULES_TEXT = (HERE / "rules.txt").read_text(encoding="utf-8")


@app.get("/rules")
def rules_text():
    flags = []
    if config.NEWS2_PRIORITY_FLOOR: flags.append("NEWS2 priority floor ON (proposed change 1).")
    if config.NEWS2_STATUS_ALERTS: flags.append("NEWS2 status alerts ON (proposed change 2).")
    return {"text": RULES_TEXT, "active_changes": flags, "ml_sources": ML.sources()}


@app.get("/metrics")
def metrics():
    return ML.metrics()


@app.get("/demo/assets")
def demo_assets():
    return ML.demo_assets()


@app.post("/demo/reset")
def demo_reset():
    STORE.clear(); _next[0] = 1
    now = utcnow()
    ago = lambda m: iso(now - timedelta(minutes=m))
    for s in json.loads((HERE / "seed_patients.json").read_text(encoding="utf-8")):
        s = copy.deepcopy(s)
        p = {"id": s["id"], "demo": True, "name": s["name"], "age": s["age"], "sex": s["sex"],
             "complaint_category": s["complaint_category"], "complaint_text": s.get("complaint_text", ""),
             "onset_time": ago(s["onset_min_ago"]) if s.get("onset_min_ago") is not None else None,
             "history": s.get("history", ""), "medications": s.get("medications", ""), "allergies": s.get("allergies", ""),
             "injuries": s.get("injuries", []),
             "treatments": [{"time": ago(t["min_ago"]), "what": t["what"]} for t in s.get("treatments", [])],
             "vitals": [], "esi": s.get("esi"), "status": s["status"],
             "arrival_time": ago(s["arrival_min_ago"]) if s.get("arrival_min_ago") is not None else None,
             "ecg": None, "xray": None, "reviews": [], "bed_request": None, "created_time": iso(now)}
        for v in s.get("vitals", []):
            m = v.pop("min_ago"); add_vitals(p, {**v, "time": ago(m)}, now)
        if s.get("ecg"): record_ecg(p, s["ecg"]["record_id"], ago(s["ecg"]["min_ago"]))
        if s.get("xray"): record_xray(p, s["xray"]["image_id"], ago(s["xray"]["min_ago"]))
        STORE[p["id"]] = p
    return board()


demo_reset()
