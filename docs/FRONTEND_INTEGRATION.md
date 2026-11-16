# Connecting the React frontend to the Relay Triage backend

For Musab. The React screens in `frontend/` now run on your backend: `npm run dev:live` uses `frontend/src/api/relay.ts`, which translates your `/api/...` responses. Nothing in `prototype/` was changed. This lists what the adapter covers and what it still can't show.

## Still needed

1. **Model weights on the demo laptop.** `outputs/ecg_resnet1d.pt` and `outputs/cxr_densenet121.pt` are not in the repo. Without them the ECG and X-ray steps are switched off in the UI (the admission model and scoring still run).
2. **Tell me if the API changes.** The adapter depends on the field names in `view()`, `/api/meta`, `/api/board` and `/api/preview` as of commit `9fb5755`.

CORS is not needed: the Vite dev server proxies `/api` and `/samples` to port 8000.

## What the screens use, and what the backend has today

| Screen feature | Frontend calls | Backend today (`/api/...`) | Gap |
|---|---|---|---|
| Bed board list | `board()` | `GET /api/board` | Mapped by the adapter |
| Patient page | `patient(id)` | `GET /api/patients/{id}` | Same |
| Send from ambulance | `create(form)` | `POST /api/patients` | Complaint list differs (8 categories vs. 25 Yale `cc_*`); temperature °F on both sides, fine |
| Live score before sending | `preview(form)` | `POST /api/preview` | None |
| Mark arrived | `arrive(id)` | `POST /api/patients/{id}/arrive` | None |
| Record ECG / X-ray | `ecg(id, sample)`, `xray(id, sample)` | `POST .../ecg`, `.../xray` with `sample_id` | None |
| Demo sample list | `assets()` | `GET /api/meta` → `samples` | None |
| Model accuracy panel | `metrics()` | `GET /api/meta` → `metrics` | None; your measured AUROCs go straight on screen |
| Reset | `reset()` | `POST /api/reset` | None |
| **Repeat vitals + trend** | `addVitals(id, vitals)` | — | **Missing.** One vitals set per patient today |
| **Triage (ESI + vitals)** | `triage(id, esi, vitals)` | — | **Missing.** Optional if we drop the triage model version |
| **Clinician review of an AI flag** | `review(id, type, normal, by)` | — | **Missing.** See "Decisions" |
| **Nurse-confirmed bed request** | `bedRequest(id, bedType, by)` | `POST .../bed/confirm` (no name) and `POST /api/beds/{bed}/assign` | Add a `confirmed_by` name; see "Decisions" |
| **Alerts** (ECG countdown, getting worse) | `view.alerts` | `queues.ecg.override` flag only | Frontend can compute the countdown from `arrived_at`; "getting worse" needs repeat vitals |
| **Handoff summaries** (MIST / SBAR) | `view.handoff` | — | Frontend can build these from `intake` with its own templates |

## Decisions the team needs to make

In live mode the screens already follow the backend on points 1, 2 and 4.

1. **Score shape.** The screens show priority = (A + B) ÷ 2 + C with the three parts visible. The backend has one score (model + overlay, NEWS2 floor) with a contributions list. If we keep the backend's score, the top strip changes to: score, "what moved it" list, NEWS2 floor. About 30 minutes of frontend work.
2. **Can the AI lower a score?** Backend: an ECG can lower it by up to 0.5 log-odds when confident. Contract and current screens: only a clinician can. The "Review this finding" button exists for this. Pick one and say it the same way in the pitch.
3. **"Assign next bed" button.** `POST /api/beds/{bed}/assign` picks the patient itself. The pitch says the nurse decides. The React board instead highlights the top match and makes the nurse confirm with their name.
4. **Bed types.** Backend: ICU, CCU, Telemetry, Psychiatric, General ward. Screens: ICU review, Telemetry, Isolation, Regular floor. The backend's list has evidence behind it (`docs/RESULTS.md`), so the screens should probably adopt it.
5. **ECG queue.** Backend orders ECGs by score with chest pain jumping the queue. The screens show a 10-minute countdown instead. Keep both; they don't conflict.

## Other things spotted in the prototype

- The **Formulas** link in `app/static/index.html` points to a claude.ai artifact. Judges can't open it unless it's shared publicly; `docs/FORMULAS.md` is safer.
- The stats in `pitch/SUBMISSION.md` "Inspiration" still need sources (your own note says so).
