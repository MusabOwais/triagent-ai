"""Proof-of-concept server: ambulance intake -> handoff -> risk-ordered ECG / X-ray queues -> re-score -> bed waitlists.
Run from the project root:  python -m uvicorn app.server:app --port 8000"""
import io, json, time, uuid, numpy as np, torch, torch.nn as nn, torchvision
from pathlib import Path
from PIL import Image
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from app import scoring as S

ROOT = Path(__file__).resolve().parents[1]
APP = Path(__file__).resolve().parent
torch.set_grad_enabled(False)

# ---------------- models (inference only, CPU) ----------------
class Block(nn.Module):
    def __init__(s, ci, co, st):
        super().__init__()
        s.c = nn.Sequential(nn.Conv1d(ci, co, 7, st, 3, bias=False), nn.BatchNorm1d(co), nn.ReLU(),
                            nn.Conv1d(co, co, 7, 1, 3, bias=False), nn.BatchNorm1d(co))
        s.sk = nn.Sequential() if ci == co and st == 1 else nn.Sequential(nn.Conv1d(ci, co, 1, st, bias=False), nn.BatchNorm1d(co))
    def forward(s, x): return torch.relu(s.c(x) + s.sk(x))

class ResNet1d(nn.Module):
    def __init__(s, n=5):
        super().__init__()
        s.f = nn.Sequential(nn.Conv1d(12, 64, 15, 2, 7, bias=False), nn.BatchNorm1d(64), nn.ReLU(),
                            Block(64, 64, 1), Block(64, 128, 2), Block(128, 128, 1), Block(128, 256, 2),
                            Block(256, 256, 1), Block(256, 256, 2), nn.AdaptiveAvgPool1d(1), nn.Flatten(), nn.Dropout(0.3))
        s.h = nn.Linear(256, n)
    def forward(s, x): return s.h(s.f(x))

ecg_ck = torch.load(ROOT / "outputs/ecg_resnet1d.pt", map_location="cpu", weights_only=False)
ECG_CLASSES = ecg_ck["classes"]
ecg_model = ResNet1d(); ecg_model.load_state_dict(ecg_ck["state"]); ecg_model.eval()
cxr_ck = torch.load(ROOT / "outputs/cxr_densenet121.pt", map_location="cpu", weights_only=False)
CXR_CLASSES = cxr_ck["classes"]
cxr_model = torchvision.models.densenet121(); cxr_model.classifier = nn.Linear(1024, len(CXR_CLASSES))
cxr_model.load_state_dict(cxr_ck["state"]); cxr_model.eval()
MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1); STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)

MANIFEST = json.loads((APP / "samples/manifest.json").read_text())
ECG_BANK = np.load(APP / "samples/ecg.npz")
ECG_BY_ID = {f"ecg-{int(i)}": ECG_BANK["x"][k] for k, i in enumerate(ECG_BANK["ids"])}
METRICS = {k: json.loads((ROOT / f"outputs/{f}").read_text()) for k, f in
           [("ecg", "ecg_results.json"), ("cxr", "cxr_results.json"), ("scorecard", "vitals_scorecard.json")]}

@torch.no_grad()
def run_ecg(sig):  # sig (1000, 12) raw mV
    x = (sig.T[None].astype(np.float32) - ecg_ck["mu"]) / ecg_ck["sd"]
    p = torch.sigmoid(ecg_model(torch.tensor(x, dtype=torch.float32)))[0].numpy()
    return dict(zip(ECG_CLASSES, map(float, p)))

@torch.no_grad()
def run_cxr(img: Image.Image):
    a = np.asarray(img.convert("L").resize((256, 256), Image.BILINEAR), dtype=np.float32) / 255
    x = torch.tensor(a[16:240, 16:240])[None, None].expand(1, 3, -1, -1)
    p = torch.sigmoid(cxr_model((x - MEAN) / STD))[0].numpy()
    return dict(zip(CXR_CLASSES, map(float, p)))

# ---------------- state ----------------
PAT: dict = {}
now = lambda: time.time()
mins = lambda t: (now() - t) / 60 if t else 0.0

class Intake(BaseModel):
    name: str = ""; age: int = Field(ge=18, le=110); sex: str = "F"; dob: str = ""
    complaint: Optional[str] = None  # cc_* name, "" for not listed, None for unknown (Model A)
    complaint_detail: str = ""; onset: str = ""; mechanism: str = ""
    history: str = ""; medications: str = ""; allergies: str = ""; treatments: str = ""
    hr: float; sbp: float; dbp: float; rr: float; spo2: float; temp_f: float; o2: bool = False
    gcs: int = Field(15, ge=3, le=15); pain: int = Field(0, ge=0, le=10); rhythm: str = "sinus"
    injuries: List[str] = []; order_ecg: bool = True; order_xray: bool = True
    minutes_ago: float = 0  # used only to seed example patients

def vitals_of(d):
    return {"age": d["age"], "male": d["sex"] == "M", "hr": d["hr"], "sbp": d["sbp"], "dbp": d["dbp"], "rr": d["rr"],
            "spo2": d["spo2"], "temp_f": d["temp_f"], "o2": d["o2"], "gcs": d["gcs"], "pain": d["pain"],
            "rhythm": d["rhythm"], "injuries": d["injuries"]}

def stage1(d):
    r = S.ambulance_score(vitals_of(d), d["complaint"])
    bed, why = S.provisional_bed(r["news2"], d["complaint"])
    r["bed"], r["bed_reason"] = bed, why
    return r

def ecg_override(p):
    return p["intake"]["complaint"] == "cc_chestpain" or p["intake"]["rhythm"] in ("stemi", "vt", "vf")

def view(p):
    """Patient as the frontend sees it, with live priorities."""
    L = p["L"]
    q = {}
    for svc in ("ecg", "xray"):
        if p["queue"].get(svc):
            q[svc] = {"since": p["queue"][svc], "minutes": round(mins(p["queue"][svc]), 1),
                      "priority": round(S.priority(L, mins(p["queue"][svc])), 3),
                      "override": svc == "ecg" and ecg_override(p)}
    bed = p["bed"]
    bedv = {**bed, "minutes": round(mins(bed["since"]), 1), "priority": round(S.priority(L, mins(bed["since"])), 3)}
    return {**{k: v for k, v in p.items() if k not in ("queue", "bed")}, "queues": q, "bed": bedv,
            "minutes_since_handoff": round(mins(p["arrived_at"]), 1) if p["arrived_at"] else None}

def log(p, kind, text, dL=0.0):
    p["events"].append({"t": now(), "kind": kind, "text": text, "dL": round(dL, 3), "score": p["score"],
                        "L": round(p["L"], 3)})

# ---------------- API ----------------
app = FastAPI(title="Triage PoC")

@app.get("/api/meta")
def meta():
    return {"complaints": [{"id": c, "label": S.pretty_cc(c)} for c in S.COMPLAINTS],
            "rhythms": [{"id": k, "label": v} for k, v in S.RHYTHM_LABEL.items()],
            "injuries": list(S.OVERLAY["injury"].keys()), "beds": S.BEDS, "samples": MANIFEST,
            "metrics": {"model_b_auroc": METRICS["scorecard"]["B_vitals_plus_complaint"]["test_auroc"],
                        "model_a_auroc": METRICS["scorecard"]["A_vitals_only"]["test_auroc"],
                        "ecg_auroc": round(METRICS["ecg"]["test_macro_auroc"], 3),
                        "cxr_auroc": round(METRICS["cxr"]["test_macro_auroc"], 3),
                        "n_yale": METRICS["scorecard"]["n"]}}

@app.post("/api/preview")
def preview(i: Intake):
    return stage1(i.model_dump())

@app.post("/api/patients")
def create(i: Intake):
    d = i.model_dump(); pid = uuid.uuid4().hex[:6]
    r = stage1(d); t0 = now() - d.pop("minutes_ago") * 60
    p = {"id": pid, "intake": d, "status": "incoming", "created_at": t0, "arrived_at": None, "stage1": r,
         "L": r["L1"], "floor": r["floor"], "score": r["score"], "ecg": None, "xray": None, "events": [],
         "queue": {}, "bed": {"type": r["bed"], "status": "provisional", "reason": r["bed_reason"], "since": t0}}
    PAT[pid] = p
    log(p, "ambulance", f"Ambulance score {r['score']} (Model {r['model']}"
        + (f", NEWS2 floor {r['floor']} applied" if r["floor"] > r["score_raw"] else "") + f"). Provisional bed: {r['bed']}.")
    return view(p)

@app.post("/api/patients/{pid}/arrive")
def arrive(pid: str, minutes_ago: float = 0):
    p = get(pid)
    if p["status"] != "incoming": raise HTTPException(400, "Patient has already arrived.")
    t = now() - minutes_ago * 60
    p["status"], p["arrived_at"] = "in ER", t
    if p["intake"]["order_ecg"]: p["queue"]["ecg"] = t
    if p["intake"]["order_xray"]: p["queue"]["xray"] = t
    log(p, "handoff", "Handoff 1: ambulance crew to ER. Joined " +
        (", ".join(k.upper() for k in p["queue"]) or "no") + " queue(s).")
    return view(p)

class Diag(BaseModel):
    sample_id: str

def apply_ecg(p, probs, source):
    pc = S.calibrate("ecg", probs); d = S.ecg_delta(pc)
    p["L"] += d["delta"]; raw = S.to_score(p["L"]); p["score"] = max(raw, p["floor"])
    old_bed = p["bed"]["type"]; nb, why = S.bed_after_ecg(old_bed, pc)
    p["ecg"] = {"source": source, "probs": pc, **d}
    p["queue"].pop("ecg", None)
    log(p, "ecg", f"ECG read. Change {d['delta']:+.2f} log-odds" + (f" ({d['note']})" if d["note"] else "")
        + f". Score now {p['score']}.", d["delta"])
    if nb != old_bed:
        p["bed"].update(type=nb, status="provisional", reason=why)  # waiting time carries over
        log(p, "bed", f"Bed waitlist changed: {old_bed} to {nb} ({why}). Waiting time kept.")

def apply_cxr(p, probs, source):
    pc = S.calibrate("cxr", probs); d = S.cxr_delta(pc)
    p["L"] += d["delta"]; raw = S.to_score(p["L"]); p["score"] = max(raw, p["floor"])
    p["xray"] = {"source": source, "probs": pc, **d}
    p["queue"].pop("xray", None)
    log(p, "xray", f"Chest X-ray read. Change {d['delta']:+.2f} log-odds" + (f" ({d['note']})" if d["note"] else "")
        + f". Score now {p['score']}.", d["delta"])

@app.post("/api/patients/{pid}/ecg")
def ecg(pid: str, body: Diag):
    p = get(pid)
    if body.sample_id not in ECG_BY_ID: raise HTTPException(404, "Unknown ECG sample.")
    apply_ecg(p, run_ecg(ECG_BY_ID[body.sample_id]), body.sample_id)
    return view(p)

@app.post("/api/patients/{pid}/xray")
def xray(pid: str, body: Diag):
    p = get(pid)
    s = next((c for c in MANIFEST["cxr"] if c["id"] == body.sample_id), None)
    if not s: raise HTTPException(404, "Unknown X-ray sample.")
    apply_cxr(p, run_cxr(Image.open(APP / "samples/cxr" / s["file"])), body.sample_id)
    return view(p)

@app.post("/api/patients/{pid}/xray-upload")
async def xray_upload(pid: str, file: UploadFile = File(...)):
    p = get(pid)
    try: img = Image.open(io.BytesIO(await file.read()))
    except Exception: raise HTTPException(400, "That file is not an image. Upload a PNG or JPG chest X-ray.")
    apply_cxr(p, run_cxr(img), f"upload: {file.filename}")
    return view(p)

class BedReq(BaseModel):
    type: str

@app.post("/api/patients/{pid}/bed/confirm")
def confirm_bed(pid: str, body: BedReq):
    p = get(pid)
    if body.type not in S.BEDS: raise HTTPException(400, "Unknown bed type.")
    old = p["bed"]["type"]
    p["bed"].update(type=body.type, status="confirmed", reason="Confirmed by ER clinician")
    log(p, "bed", f"ER clinician confirmed {body.type} bed" + (f" (changed from {old})" if old != body.type else "") + ".")
    return view(p)

@app.post("/api/beds/{bed}/assign")
def assign(bed: str):
    cands = [p for p in PAT.values() if p["bed"]["type"] == bed and p["bed"]["status"] == "confirmed"]
    if not cands: raise HTTPException(404, f"No confirmed patients are waiting for a {bed} bed.")
    p = max(cands, key=lambda p: S.priority(p["L"], mins(p["bed"]["since"])))
    p["bed"]["status"] = "assigned"; p["status"] = "bed assigned"
    log(p, "handoff", f"{bed} bed assigned. Handoff 2: ER to admitting team.")
    return view(p)

@app.get("/api/board")
def board():
    V = [view(p) for p in PAT.values()]
    def queue(svc):
        rows = [v for v in V if svc in v["queues"]]
        return sorted(rows, key=lambda v: (not v["queues"][svc]["override"], -v["queues"][svc]["priority"]))
    beds = {b: sorted([v for v in V if v["bed"]["type"] == b and v["bed"]["status"] != "assigned" and v["status"] != "incoming"],
                      key=lambda v: -v["bed"]["priority"]) for b in S.BEDS}
    return {"patients": sorted(V, key=lambda v: -v["score"]), "ecg": queue("ecg"), "xray": queue("xray"), "beds": beds,
            "incoming": [v for v in V if v["status"] == "incoming"]}

@app.get("/api/patients/{pid}")
def one(pid: str):
    return view(get(pid))

@app.get("/api/samples/ecg/{sid}")
def ecg_trace(sid: str):
    if sid not in ECG_BY_ID: raise HTTPException(404, "Unknown ECG sample.")
    x = ECG_BY_ID[sid]
    return {"leads": ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"],
            "hz": 100, "data": np.round(x.T, 3).tolist()}

@app.get("/samples/cxr/{name}")
def cxr_img(name: str):
    f = APP / "samples/cxr" / Path(name).name
    if not f.exists(): raise HTTPException(404, "Unknown image.")
    return FileResponse(f)

def get(pid):
    if pid not in PAT: raise HTTPException(404, "Patient not found.")
    return PAT[pid]

EXAMPLES = [
    dict(name="Example patient: R. Alvarez", age=68, sex="M", complaint="cc_chestpain", complaint_detail="Crushing central chest pain radiating to left arm",
         onset="35 min before call", history="Hypertension, type 2 diabetes", medications="Metformin, lisinopril", allergies="None known",
         treatments="Aspirin 324 mg PO 14:02; nitroglycerin 0.4 mg SL 14:06", hr=104, sbp=148, dbp=92, rr=20, spo2=95, temp_f=98.2,
         o2=False, gcs=15, pain=8, rhythm="sinus", minutes_ago=22, arrive=18, ecg="mi"),
    dict(name="Example patient: M. Chen", age=79, sex="F", complaint="cc_shortnessofbreath", complaint_detail="Worsening breathlessness over 2 days, productive cough",
         onset="2 days", history="COPD, heart failure", medications="Furosemide, tiotropium", allergies="Penicillin (rash)",
         treatments="O2 4 L nasal cannula 13:40; albuterol neb 13:45", hr=118, sbp=96, dbp=58, rr=26, spo2=89, temp_f=101.3,
         o2=True, gcs=14, pain=3, rhythm="af_rvr", minutes_ago=40, arrive=34),
    dict(name="Example patient: D. Okafor", age=24, sex="M", complaint="cc_motorvehiclecrash", complaint_detail="Restrained driver, side impact, right forearm deformity",
         onset="20 min", mechanism="Car vs car, ~30 mph, side impact", history="None", medications="None", allergies="None known",
         treatments="Splint right forearm 14:10; fentanyl 50 mcg IV 14:12", hr=96, sbp=128, dbp=80, rr=18, spo2=98, temp_f=98.4,
         o2=False, gcs=15, pain=7, rhythm="sinus", injuries=["closed_fracture"], order_ecg=False, minutes_ago=15, arrive=10),
    dict(name="Example patient: S. Patel", age=45, sex="F", complaint="cc_syncope", complaint_detail="Fainted at work, brief loss of consciousness",
         onset="1 hour", history="None", medications="Oral contraceptive", allergies="Sulfa drugs",
         treatments="IV access 14:20", hr=58, sbp=104, dbp=66, rr=16, spo2=99, temp_f=98.0, o2=False, gcs=15, pain=0,
         rhythm="sinus", order_xray=False, minutes_ago=30, arrive=25),
    dict(name="Example patient: J. Brooks", age=33, sex="M", complaint="cc_suicidal", complaint_detail="Expressed suicidal thoughts to family, no ingestion reported",
         onset="Today", history="Depression", medications="Sertraline", allergies="None known", treatments="None",
         hr=88, sbp=126, dbp=82, rr=16, spo2=99, temp_f=98.6, o2=False, gcs=15, pain=0, rhythm="sinus",
         order_ecg=False, order_xray=False, minutes_ago=50, arrive=45),
    dict(name="Example patient: L. Novak", age=82, sex="F", complaint="cc_weakness", complaint_detail="Generalized weakness, confused per daughter",
         onset="This morning", history="Atrial fibrillation, CKD", medications="Apixaban, metoprolol", allergies="None known",
         treatments="Glucose check 112 mg/dL 14:25", hr=92, sbp=112, dbp=64, rr=22, spo2=94, temp_f=100.8, o2=False, gcs=14,
         pain=2, rhythm="other", minutes_ago=8),
]

@app.post("/api/reset")
def reset():
    PAT.clear()
    for e in EXAMPLES:
        e = dict(e); arr = e.pop("arrive", None); ecg_kind = e.pop("ecg", None)
        v = create(Intake(**e));
        if arr is not None: arrive(v["id"], minutes_ago=arr)
    return board()

reset()
app.mount("/", StaticFiles(directory=APP / "static", html=True), name="static")
