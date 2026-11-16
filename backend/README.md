# backend/ — Role 2: backend and clinical logic

FastAPI app on port 8000: patient record, NEWS2, bed-priority score, rules, alerts, MIST/SBAR summaries, seed patients, tests. Implements `docs/CONTRACT.md` A5 and A6 exactly. See also `prompts/2-Backend-clinical-logic.md`.

## Run

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --port 8000          # add --reload while developing (it wipes the in-memory store on each save)
python -m pytest -q                  # 77 tests
```

Check it works: open http://localhost:8000/board (six demo patients) or http://localhost:8000/docs (interactive API).

## Files

| File | What it does |
|---|---|
| `app.py` | Routes from A6 and the computed view |
| `models.py` | Request schemas (A6 field names) |
| `news2.py` | NEWS2 table, bands, completeness, trend |
| `scoring.py` | Parts A/B/C, priority, queue rank, raise-only flag state |
| `rules.py` | Bed type, protocol alerts, deterioration alerts, pending list |
| `summaries.py` | MIST and SBAR templates (no AI, "not recorded" for gaps) |
| `ml_bridge.py` | Uses Role 1's functions from `ml/` when they exist, else stubs (`"model": "stub"`) |
| `seed_patients.json` | Six fictional demo patients; times rebuilt relative to now by `POST /demo/reset` |
| `rules.txt` | Plain-text rules served by `GET /rules` |
| `config.py` | Switches for proposed contract changes (all off) |
| `API_EXAMPLES.md` | One real response per endpoint, for Role 3 |
| `CONTRACT_CHANGES.md` | Proposed changes and clarifications to paste to the team |

## For Role 1: how your functions get picked up

Expose `predict_admission`, `flag_ecg` and `flag_xray` with the A6 signatures from `ml/__init__.py` (or `ml/predict.py`), and add `ml/metrics.json` and `ml/demo_assets.json`. Restart the backend; `GET /rules` shows `ml_sources` switching from `stub` to `real`. Demo ids the seed data uses: ECG `ptbxl_14912` (abnormal) and `ptbxl_19669` (normal); X-ray `00000773_001.png` (pneumonia) and `00000842_000.png` (no finding).

## Demo story (seed patients)

| Id | Story |
|---|---|
| P-001 | Chest pain, normal vitals: low score, ECG countdown running. Record ECG `ptbxl_14912` → +10, telemetry |
| P-002 | Infection, NEWS2 3 → 6 while waiting: deterioration alert |
| P-003 | 81, short of breath, 38.6 °C, X-ray flags pneumonia: possible isolation |
| P-004 | Fall, suspected fracture + graze: injury points (draft), regular floor |
| P-005 | Minor abdominal pain, waiting 3 h: waiting points move her up |
| P-006 | Stroke signs, en route: Incoming (unranked), stroke alert, low-glucose mimic note |
