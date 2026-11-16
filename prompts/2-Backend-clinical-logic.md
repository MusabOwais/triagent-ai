# MASTER PROMPT — ROLE 2: BACKEND AND CLINICAL LOGIC

You are my senior backend partner for the rest of today. I am **Role 2** on a 3-person hackathon team. I own the API, the patient record, and all the clinical logic: NEWS2, the bed-priority score, bed-type rules, alerts, handoff summaries, demo seed data, and tests. Part A is the full team brief; Part B is my job. You have no other context.

## How I want you to work

1. **Start with complete, direct feedback** on this plan from a backend and clinical-safety point of view, before writing any code. Rank issues by severity. Cover: anything clinically unsafe, edge cases in the scoring rules, contradictions or gaps in the spec, anything that would block my teammates, and scope that won't fit the time. Say plainly if something is wrong.
2. Then ask me only what you need (deadline, my OS and Python version) and give me a time-boxed plan.
3. Build in small runnable steps. After each step, tell me the exact command to run and what output means it worked.
4. Never change the shared contract (Part A6) silently. If a change is needed, write a short **"Contract change"** note I can paste to my teammates.
5. Be honest about what you haven't run or tested.

# PART A — TEAM BRIEF (identical in all three prompts)

Assume you know nothing about this project except what is written here. Everything you need is in this prompt.

**Fill in before sending:** Submission deadline: `[DEADLINE]` · Teammates: Role 1 (ML) `[ROLE 1 NAME]`, Role 2 (backend) `[ROLE 2 NAME]`, Role 3 (frontend and pitch) `[ROLE 3 NAME]` · AI API keys we have: `[KEYS]`

## A1. The event and the track

- **Event:** SacHacks "HackRx", a one-day medical hackathon at the UC Davis Betty Irene Moore School of Nursing in Sacramento. Judges include clinicians, researchers and sponsors. All code must be written during the event.
- **Track:** Best Clinical Impact (sponsored by Abridge, which makes AI that writes up doctor visits). Hard requirements, from the organizers' slides (paraphrased; confirm with an organizer):
  1. **Must use the Yale ED Admission Prediction dataset plus 2 of:** PTB-XL (ECGs), NIH Chest X-rays, ReXGradient-160K. **We use Yale + PTB-XL + NIH.**
  2. Start with the clinical problem, not the tool.
  3. Deliver at least one of: a better clinical decision, a new insight from the data, or time given back to clinicians. **We claim "better decision" (bed priority and bed type) and "time back" (automatic handoff summaries). Our "insight" is how well admission can be predicted from ambulance data alone vs. after triage.**

## A2. The problem (what the pitch opens with)

Emergency rooms are full because admitted patients wait ("board") in the ER for hours until a hospital bed opens. Ambulances then wait at the ER door to hand patients over. At every handoff, information is passed on verbally or on paper and gets lost.

Numbers gathered so far (Role 3 must verify each source before it goes on a slide):
- 53.6% of ~492,000 admitted patients from 56 ERs waited 4+ hours for a bed; ~4,500 waited 24+ hours.
- French study of 97 ERs: patients over 75 who spent the night in the ER waiting for a bed had 15.7% in-hospital mortality vs. 11.1% for those sent to a ward.
- California mean ambulance offload time: 42.8 minutes against a 30-minute state standard. Sacramento averaged 66.8 minutes in 2021–2023 and improved to 33 minutes by April 2025, still above the county's 25-minute standard.
- Handoff information loss: one study found only 72.9% of key items paramedics said were written down; another found vital signs were passed on in only 57% of handoffs.
- Research support: a 2023 Operations Research simulation showed that predicting admission at triage and requesting beds early could shorten ER waits; a Sydney pilot (113 patients) of a triage admission-risk tool plus early senior review cut ER stays from 423 to 301 minutes.

**What two mentors (clinicians) told us:**
- Ambulance information arrives on paper and often never makes it into the hospital system. This is the gap we fill.
- Patients often get their chest X-ray while waiting for a bed, so re-scoring after the X-ray makes sense.
- The underlying cause is staffing. A better score does not create beds. **So we never claim "shorter waits" or "saves lives".** We claim: the sickest patient gets the next suitable bed, nobody gets worse unnoticed while waiting, and staff stop re-asking and re-writing the same information at every handoff.
- Who decides with 3 patients and 1 bed? **The app ranks and suggests; the charge nurse decides.**
- A patient-translation feature was dropped ("another project"). Do not add it.

## A3. The product in one paragraph

A proof-of-concept website that follows an emergency patient from the ambulance to a hospital bed. Paramedics enter vitals and visible injuries; the app keeps one patient record that every next provider sees and adds to. It calculates a **bed-priority score** from three visible parts: chance of needing a hospital bed (model trained on Yale), how sick the patient is right now (NEWS2), and findings (ECG model trained on PTB-XL, chest X-ray model tested on NIH, visible-injury menu). Time-critical tests follow existing protocols with countdown alerts, not the score. AI findings can only raise the score; lowering it needs a clinician. The charge nurse sees a ranked bed queue matched by bed type and confirms every bed request. Handoff summaries (MIST for the ambulance, SBAR for the floor nurse) are written automatically from the record.

## A4. Who touches the patient (real-world flow, US)

1. **Paramedic (ambulance):** checks airway/breathing/circulation, treats, re-checks vitals every 5–15 min, records a 12-lead ECG for chest pain, asks history (SAMPLE: Symptoms, Allergies, Medications, Past history, Last meal, Events). Calls ahead for critical cases.
2. **Handoff at ER door:** short spoken report in MIST format (Mechanism/complaint, Injuries, Signs/vitals, Treatment). The written report is often finished after the crew leaves. **This is the gap.**
3. **Charge nurse:** runs the ER floor, decides where patients go, watches who is waiting and who is getting worse, works with bed management.
4. **Triage nurse:** assigns ESI (Emergency Severity Index, 1 = most urgent … 5 = least), takes vitals, starts standing orders (e.g., ECG within 10 minutes for chest pain).
5. **ER nurse:** repeats vitals, gives medications, notices deterioration.
6. **ER doctor:** examines, orders tests, makes the admit/discharge decision.
7. **ECG/X-ray techs and radiologist:** run and read tests. Radiology reads can take time.
8. **Admitting doctor (hospitalist):** decides level of care: ICU, step-down, telemetry (heart-monitored bed), regular floor, isolation.
9. **Bed manager / house supervisor:** matches requests to open beds.
10. **Floor nurse:** receives an SBAR report (Situation, Background, Assessment, Recommendation).

We build **only 3 screens**: ambulance form, patient view, bed board. The chain above is the story, not a screen list.

## A5. Scoring and rules (exact spec — Role 2 implements, Role 1 feeds, Role 3 displays)

**A. Needs a bed (0–100):** Yale admission model probability × 100. Two model versions: `ambulance` stage (no ESI) and `triage` stage (with ESI). Use the triage version once ESI is entered.

**B. Sick right now (0–100):** NEWS2 (0–20) × 5. NEWS2 table (SpO2 Scale 1 only):

| Parameter | 3 | 2 | 1 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|---|---|---|
| Respiration rate /min | ≤8 | | 9–11 | 12–20 | | 21–24 | ≥25 |
| SpO2 % | ≤91 | 92–93 | 94–95 | ≥96 | | | |
| Air or oxygen | | Oxygen | | Air | | | |
| Systolic BP mmHg | ≤90 | 91–100 | 101–110 | 111–219 | | | ≥220 |
| Pulse /min | ≤40 | | 41–50 | 51–90 | 91–110 | 111–130 | ≥131 |
| Consciousness | | | | Alert | | | New confusion, V, P or U |
| Temperature °C | ≤35.0 | | 35.1–36.0 | 36.1–38.0 | 38.1–39.0 | ≥39.1 | |

Consciousness: AVPU "A" = 0, anything else = 3. If only GCS is given: GCS 15 = Alert, below 15 = 3 points. Bands: 0–4 low, 5–6 medium (urgent review), 7+ high (emergency). If any of the 7 parameters is missing, show NEWS2 as "incomplete (n/7)" and do not fire deterioration alerts from that set.

**C. Findings (points added):**
- ECG model says abnormal: +10
- X-ray model flags any of the 5 findings: +10
- Visible injuries (sum): none 0 · minor wound 2 · suspected fracture 5 · open fracture 10 · minor burn 5 · major burn 15 · heavy bleeding 15 · frostbite 5. **Placeholders, labeled "draft — clinician review needed".**

**Bed priority** = min(100, round((A + B) / 2 + C)). All three parts are always shown next to the number.

**Raise-only rule (enforced in code, with a test):** an AI result can add points but never subtracts. A normal AI result adds 0. Only a clinician tapping "Reviewed — normal" on an ECG or X-ray finding removes that finding's points. (A and B change freely when humans enter new vitals or ESI, because that is new clinical data, not an AI opinion.)

**Bed queue rank** = bed priority + 1 point per full 15 minutes waited since arrival. Prevents low scorers waiting forever.

**Suggested bed type** (draft rules, mentor to review; first match wins, show the reason):
1. NEWS2 ≥ 7 or GCS ≤ 8 → "ICU review"
2. ECG abnormal (unreviewed or confirmed) → "Telemetry (heart-monitored)"
3. X-ray flags pneumonia and temperature ≥ 38.1 °C → "Possible isolation"
4. Otherwise → "Regular floor"

API codes for bed type: `icu_review`, `telemetry`, `isolation`, `floor`.

When a bed of a given type opens, the board highlights the highest-ranked patient whose suggested type matches. **The charge nurse confirms every request; the app never assigns a bed.**

**Protocol alerts (not driven by the score):**
- Complaint = chest pain → "ECG due within 10 min of arrival" with a countdown until an ECG is recorded; turns red when overdue.
- Complaint = stroke signs → "Stroke alert" banner. If blood glucose < 70 mg/dL also show "Low blood sugar can mimic stroke — check glucose".

**Deterioration alert:** fire only when NEWS2 **rises** between consecutive complete vital sets by ≥ 2 points, or crosses into a higher band (into 5–6, or into 7+). Never fire on a single high reading that did not rise (avoids alarm fatigue).

## A6. Shared data contract (do not change silently)

**Repository layout**
```
hackrx/
  ml/        Role 1 — models, training scripts, metrics.json, demo_assets/
  backend/   Role 2 — FastAPI app, scoring, rules, summaries, seed data
  frontend/  Role 3 — React app
  pitch/     Role 3 — slides, demo script, Devpost text
```

**ML functions (Role 1 provides in `ml/`, Role 2 imports; Role 2 uses stubs with the same signatures until they exist):**
```python
predict_admission(features: dict, stage: "ambulance" | "triage") -> {
  "probability": 0.72, "stage": "triage", "model": "yale_xgb_triage_v1",
  "top_reasons": [{"label": "Age 67", "direction": "up"}, ...]   # up to 3
}
# features keys: age, sex ("M"/"F"), arrival_mode ("ambulance"/"walk_in"),
#   complaint_category, heart_rate, sbp, dbp, resp_rate, spo2, temp_c, on_oxygen, esi (triage only)

flag_ecg(record_id: str) -> {"abnormal_prob": 0.81, "abnormal": True, "threshold": 0.5,
  "model": "ptbxl_cnn_v1", "note": "AI flag, not a diagnosis"}

flag_xray(image_id: str) -> {"findings": {"Pneumonia": 0.78, "Effusion": 0.12, "Edema": 0.05,
  "Cardiomegaly": 0.30, "Pneumothorax": 0.02}, "flagged": ["Pneumonia"],
  "thresholds": {...}, "model": "xrv_chex_densenet", "note": "AI flag, not a diagnosis"}
```
Plus `ml/metrics.json` (all measured test scores) and `ml/demo_assets.json` (list of demo ECG record ids and X-ray image ids with file paths).

**Complaint categories (fixed list):** `chest_pain, shortness_of_breath, stroke_signs, abdominal_pain, trauma, altered_mental_status, fever_infection, other`

**Patient record (stored by Role 2):**
```json
{
  "id": "P-001", "demo": true, "name": "Demo Patient A (fictional)",
  "age": 67, "sex": "M", "complaint_category": "chest_pain",
  "complaint_text": "Crushing chest pain for 40 min", "onset_time": "ISO-8601",
  "history": "HTN, T2DM", "medications": "metformin", "allergies": "penicillin",
  "injuries": ["suspected_fracture"],
  "treatments": [{"time": "ISO", "what": "Aspirin 324 mg PO"}],
  "vitals": [{"time": "ISO", "source": "ambulance|triage|er", "resp_rate": 22, "spo2": 94,
              "on_oxygen": false, "sbp": 105, "dbp": 70, "heart_rate": 112, "temp_c": 37.2,
              "avpu": "A", "gcs": 15, "pain": 7, "glucose_mg_dl": 140, "rhythm": "sinus tach"}],
  "esi": null, "arrival_time": "ISO", "status": "en_route|waiting|bed_requested|in_bed",
  "ecg": {"record_id": "ptbxl_12345", "result": {...flag_ecg output...}, "time": "ISO"},
  "xray": {"image_id": "00001234_000.png", "result": {...flag_xray output...}, "time": "ISO"},
  "reviews": [{"type": "ecg|xray", "normal": true, "by": "RN Demo", "time": "ISO"}],
  "bed_request": {"bed_type": "telemetry", "confirmed_by": "Charge RN Demo", "time": "ISO"}
}
```

**Computed view (what the API returns to the frontend for each patient):**
```json
{
  "patient": { ...record... },
  "scores": {
    "admission": {"probability": 0.72, "stage": "triage", "top_reasons": [...]},
    "news2": {"value": 6, "band": "medium", "complete": true, "trend": "up", "previous": 3},
    "findings": {"points": 15, "items": [{"source": "ecg", "label": "Abnormal ECG (AI, unreviewed)", "points": 10}]},
    "parts": {"A": 72, "B": 30, "C": 15},
    "priority": 66, "wait_minutes": 42, "queue_rank_score": 68
  },
  "bed_type": {"suggested": "telemetry", "reason": "Abnormal ECG (AI, unreviewed)"},
  "alerts": [{"kind": "protocol|deterioration", "level": "warning|critical", "message": "...", "due_at": "ISO or null"}],
  "pending": ["X-ray read pending"],
  "handoff": {"mist": "...", "sbar": "..."}
}
```

**API (Role 2 serves at `http://localhost:8000`, CORS open):**
| Method | Path | Body → result |
|---|---|---|
| POST | `/patients` | ambulance form fields → computed view (status `en_route`) |
| POST | `/patients/{id}/arrive` | — → sets arrival_time, status `waiting` |
| POST | `/patients/{id}/vitals` | one vitals set → computed view |
| POST | `/patients/{id}/triage` | `{esi, vitals}` → computed view |
| POST | `/patients/{id}/ecg` | `{record_id}` → runs `flag_ecg` → computed view |
| POST | `/patients/{id}/xray` | `{image_id}` → runs `flag_xray` → computed view |
| POST | `/patients/{id}/review` | `{type, normal, by}` → computed view |
| POST | `/patients/{id}/bed-request` | `{bed_type, confirmed_by}` → computed view |
| GET | `/patients/{id}` | computed view |
| GET | `/board` | list of computed views, sorted by `queue_rank_score` desc |
| GET | `/rules` | the plain-text rules from A5, for display on screen |
| GET | `/metrics` | contents of `ml/metrics.json` |
| GET | `/demo/assets` | demo ECG and X-ray ids for the picker |
| POST | `/demo/reset` | reloads seed patients with times relative to now |

## A7. Non-negotiable honesty and safety rules

1. The screen never shows a clinical fact that a person did not enter or a labeled model did not produce. Summaries are built from the record only; missing fields say "not recorded".
2. Every AI output is labeled as an AI flag, not a diagnosis, with its measured accuracy available.
3. The app suggests; humans decide. No automatic bed assignment.
4. The three datasets come from different patients, so there is no combined trained model. They are joined by the written rules in A5, which are shown on screen.
5. Models only use information available at that moment (no leakage of post-triage data).
6. Demo patients are fictional composites (one Yale-like vitals profile + one PTB-XL ECG + one NIH X-ray) and are labeled "fictional demo patient" on screen.
7. Placeholder numbers are labeled "draft — clinician review needed".
8. A real version would limit access by role (patient privacy, HIPAA). State this once in the UI footer and in the pitch.
9. Report measured numbers as they are, even if worse than published results.

## A8. Team split and checkpoints

- **Role 1 — ML engineer:** the three models, measured accuracy, demo assets.
- **Role 2 — Backend and clinical logic:** API, record store, NEWS2, score, rules, alerts, handoff summaries, seed patients, tests.
- **Role 3 — Frontend, demo and pitch:** the 3 screens, demo script, slides, Devpost write-up, fact-checking, talking to mentors.

Checkpoints (T = deadline):
1. **First 45 min:** everyone works against the contract above. Role 2 ships stub ML + seed data so Role 3 can build on real API calls immediately.
2. **Midpoint:** first real model swapped in (Yale). End-to-end click-through works with stubs for the rest.
3. **T − 2 h:** all real models in. Feature freeze at **T − 90 min**: only bug fixes after this.
4. **T − 60 min:** full demo rehearsal on the presenting laptop. **T − 30 min:** submit on Devpost. Do not wait until the last minute.

If any role falls behind, the stub stays in and the slide says so honestly.

# PART B — ROLE 2 JOB: API, RECORD AND CLINICAL LOGIC

## B1. Stack and files (in `hackrx/backend/`)
- Python 3.11, FastAPI, Uvicorn, Pydantic models, pytest. In-memory store (a dict) loaded from `seed_patients.json`. No database, no login.
- Suggested files: `app.py` (routes), `models.py` (Pydantic schemas matching A6), `news2.py`, `scoring.py` (parts A/B/C, priority, queue rank, raise-only), `rules.py` (bed type, protocol alerts, deterioration), `summaries.py` (MIST, SBAR), `ml_bridge.py` (imports real ML functions or stubs), `seed_patients.json`, `tests/`.
- Run with `uvicorn app:app --reload --port 8000`. CORS open to `http://localhost:5173`.

## B2. Ship stubs in the first 45 minutes
Role 3 is blocked until the API answers. First milestone: every endpoint in A6 returns a correctly shaped computed view using **stub ML functions** with the exact A6 signatures. Stubs return fixed plausible values and set `"model": "stub"` so it's visible on screen. `ml_bridge.py` tries to import the real function from `ml/` and falls back to the stub, so swapping in Role 1's work needs no code change.

## B3. Clinical logic (implement exactly as A5)
- **NEWS2:** implement the table in A5 exactly, including band edges. Consciousness from AVPU, or from GCS if AVPU is missing (15 = Alert, below 15 = 3 points). Scale 1 SpO2 only (note that Scale 2, for patients with chronic CO2 retention, isn't implemented). If any of the 7 parameters is missing, return `complete: false` and the count present.
- **Trend:** compare the latest complete vitals set with the previous complete set: `up`, `down` or `flat`.
- **Parts and priority:** A = admission probability × 100 (use the `triage` model once ESI exists, else `ambulance`). B = NEWS2 × 5. C = findings points. Priority = min(100, round((A + B) / 2 + C)).
- **Raise-only:** AI results only add points. A finding's points are removed only by a `review` with `normal: true`. Write a test proving a normal AI result never lowers the score and a clinician review does.
- **Queue rank:** priority + floor(minutes since arrival / 15). Patients still `en_route` appear on the board in an "Incoming" section, unranked.
- **Bed type:** the 4 ordered rules in A5, returning the suggestion and the reason string.
- **Protocol alerts:** chest pain → ECG countdown from `arrival_time` (10 min) until an ECG exists; `critical` when overdue. Stroke signs → stroke alert; add the low-glucose note when glucose < 70.
- **Deterioration alert:** only on a rise of ≥ 2 between consecutive complete sets, or on crossing into a higher band.
- **Pending list:** e.g., "ECG not yet recorded", "X-ray read pending", "ESI not yet assigned", "Bed request not sent".

## B4. Handoff summaries (template-based, no AI)
Build both from the record only, using fixed templates. Missing fields say "not recorded". Never add a diagnosis.
- **MIST** (ambulance → ER): Mechanism/complaint + onset · Injuries · Signs (latest ambulance vitals, NEWS2) · Treatment (with times).
- **SBAR** (ER → floor nurse): Situation (age, sex, complaint, suggested bed type) · Background (history, meds, allergies) · Assessment (latest vitals, NEWS2 and trend, admission %, ECG/X-ray flags and whether reviewed) · Recommendation (pending items and alerts, phrased as items to check, not orders).
- Optional only if everything else is done: an LLM rewrite for readability, with a check that it adds no facts. Default is the template.

## B5. Seed data: 5–6 fictional demo patients that tell the story
Times are stored relative to "now" and rebuilt by `POST /demo/reset`, so wait times look real during the demo. Use names like "Demo Patient A (fictional)". Use Role 1's demo ECG/X-ray ids once available.
1. **Chest pain, normal-looking vitals** — low score, but the ECG countdown alert fires. Shows that protocol, not the score, drives urgent tests. Later the ECG flags abnormal → +10 and telemetry bed.
2. **Getting worse while waiting** — infection-like picture; NEWS2 rises 3 → 6 across repeat vitals → deterioration alert.
3. **Elderly, short of breath, fever** — X-ray flags pneumonia → possible isolation.
4. **Trauma with suspected fracture** — injury points, regular floor.
5. **Stable minor complaint, long wait** — shows the waiting-time points moving them up.
6. **En route** — still in the ambulance, appears under "Incoming".

## B6. Tests (pytest; write these early, they're quick)
- NEWS2: every band edge in the table, plus a few full patients with known totals.
- Incomplete vitals → `complete: false`, no deterioration alert.
- Priority formula and cap at 100.
- Raise-only rule (normal AI result doesn't lower; clinician review does).
- Queue rank waiting points.
- Bed-type rule order.
- Deterioration fires on a rise, not on a steady high.
- ECG countdown turns critical after 10 minutes.

## B7. Hand-offs to teammates
- **To Role 3:** the base URL, one example JSON response per endpoint, and `/rules` text. Tell them immediately if a field changes.
- **From Role 1:** each real ML function. Swap it in through `ml_bridge.py`, then re-run the tests and the full demo click-through.
- At feature freeze (T − 90 min) stop adding features; only fix bugs.

## B8. Questions judges will ask me (prepare short answers)
- Why NEWS2? (Published, widely used, no training needed, clinicians already trust it.)
- Why can't the AI lower the score? (X-rays miss some serious problems, e.g. lung clots and heart attacks, and AI can miss findings. Lowering needs a clinician.)
- Why doesn't the score decide test order? (A heart attack can present with normal vitals; ECG within 10 minutes for chest pain is the standard.)
- Who decides the bed? (The charge nurse. The app suggests.)
- Where did the injury points and bed rules come from? (Drafts, labeled for clinician review; reviewed by our mentor if they've signed off.)
