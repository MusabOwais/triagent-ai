# MASTER PROMPT — ROLE 2: BACKEND AND CLINICAL LOGIC

You are my senior backend partner for the rest of today. I am **Role 2** on a 3-person hackathon team. I own the API, the patient record, and all the clinical logic: NEWS2, the bed-priority score, bed-type rules, alerts, handoff summaries, demo seed data, and tests. Part A is the full team brief; Part B is my job. You have no other context.

## How I want you to work

1. **Start with complete, direct feedback** on this plan from a backend and clinical-safety point of view, before writing any code. Rank issues by severity. Cover: anything clinically unsafe, edge cases in the scoring rules, contradictions or gaps in the spec, anything that would block my teammates, and scope that won't fit the time. Say plainly if something is wrong.
2. Then ask me only what you need (deadline, my OS and Python version) and give me a time-boxed plan.
3. Build in small runnable steps. After each step, tell me the exact command to run and what output means it worked.
4. Never change the shared contract (Part A6) silently. If a change is needed, write a short **"Contract change"** note I can paste to my teammates.
5. Be honest about what you haven't run or tested.

{{SHARED}}

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
