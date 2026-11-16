# Relay Triage (prototype branch)

An end-to-end prototype built alongside the team plan in `docs/CONTRACT.md`. It does **not** follow the contract's score formula, bed types or API paths. It is here so the team can review it and reuse parts (trained models, measured metrics, the medication-leakage finding, the vitals scorecard).

SacHacks 2026, Clinical Impact track. Proof of concept.

An ambulance crew enters vitals and observations and gets a 1–100 risk score. The score and full patient record are handed off to the ER, where the score orders the ECG and chest X-ray queues. ECG and X-ray results adjust the score, and the new score orders the patient on a waitlist for one of five bed types (ICU, CCU, Telemetry, Psychiatric, General ward). A second handoff goes to the admitting team.

## Datasets

| Dataset | Used for |
|---|---|
| [Yale EM Admission Prediction](https://github.com/yaleemmlc/admissionprediction) | Ambulance score (Model A: vitals; Model B: vitals + chief complaint) |
| [PTB-XL](https://physionet.org/content/ptb-xl/1.0.3/) | ECG model |
| [NIH ChestX-ray14](https://huggingface.co/datasets/alkzar90/NIH-Chest-X-ray-dataset) | Chest X-ray model (subset: `images_001`) |

Raw data is not in this repo. Download it into `data/yale`, `data/ptbxl` and `data/nih` to retrain.

## Results (held-out test sets)

| Model | Test AUROC |
|---|---|
| Model B, vitals + complaint (Yale ambulance arrivals, n = 92,172) | 0.791 |
| Model A, vitals only | 0.749 |
| NEWS2 on the same vitals (benchmark) | 0.621 |
| ECG, 5 diagnostic classes (PTB-XL fold 10) | 0.921 macro |
| Chest X-ray, 14 findings (NIH subset, patient-disjoint) | 0.708 macro |

Medication features were excluded after we found they leak the outcome. ESI is excluded because an ambulance does not have it.

## Limitations

- Training vitals are ER triage vitals of ambulance arrivals, not ambulance-recorded vitals.
- The models predict admission, not severity. Severe trauma is caught by the EMT overlay and the NEWS2 floor.
- The EMT overlay weights, ECG/X-ray severity weights and bed-type rules are hand-set clinical choices. No dataset links imaging to outcomes or records the admitting unit.
- The X-ray model is trained on 4% of NIH, so it may only raise scores.

## Run the website

```
pip install -r requirements.txt
python -m uvicorn app.server:app --port 8000
```

Open http://localhost:8000.

Model weights (`outputs/ecg_resnet1d.pt`, `outputs/cxr_densenet121.pt`) are not committed, per this repo's rule against committing weights. To recreate them, download PTB-XL into `data/ptbxl` and the NIH `images_001` archive plus labels CSV into `data/nih`, then run from `prototype/`:

```
python src/ecg_train.py
python src/cxr_train.py
python src/calibrate.py
```

Or ask Musab for the two `.pt` files and drop them into `outputs/`.

## Layout

- `src/`: training and evaluation scripts
- `outputs/`: trained models and metrics
- `app/scoring.py`: every scoring formula
- `app/server.py`: API and model inference
- `app/static/`: frontend
