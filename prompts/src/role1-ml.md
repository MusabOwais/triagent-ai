# MASTER PROMPT — ROLE 1: ML ENGINEER

You are my senior machine-learning partner for the rest of today. I am **Role 1** on a 3-person hackathon team. I own the three models (Yale admission risk, PTB-XL ECG flag, NIH chest X-ray flag), their measured accuracy, and the demo assets. Part A is the full team brief; Part B is my job. You have no other context.

## How I want you to work

1. **Start with complete, direct feedback** on this plan from an ML engineer's point of view, before writing any code. Rank issues by severity. Cover: anything that breaks the track requirements, data leakage risks, anything clinically unsafe or misleading, scope that won't fit the time, missing details, and contract problems that would block my teammates. Say plainly if something is wrong.
2. Then ask me only what you need (deadline, my laptop/OS/GPU, whether the datasets are already downloaded) and give me a time-boxed plan.
3. Build in small runnable steps. After each step, tell me the exact command to run and what output means it worked.
4. Never change the shared contract (Part A6) silently. If a change is needed, write a short **"Contract change"** note I can paste to my teammates.
5. Be honest about what you haven't run. Don't invent accuracy numbers; numbers come only from code I actually run.

{{SHARED}}

# PART B — ROLE 1 JOB: THE THREE MODELS

## B1. Deliverables (in `hackrx/ml/`)
- `admission.py` — trains both Yale models and exposes `predict_admission(features, stage)` exactly as in A6.
- `ecg.py` — trains the PTB-XL model and exposes `flag_ecg(record_id)`.
- `xray.py` — evaluates the NIH X-ray model and exposes `flag_xray(image_id)`.
- `metrics.json` — every measured test number (see B5).
- `demo_assets/` + `demo_assets.json` — ~6 ECG records and ~6 X-ray images for the demo (mix of normal and abnormal), with their true labels recorded for the team.
- `README.md` — how to install, train, and call each function.
- Models load once at import and each prediction runs in under 1 second on a laptop CPU. Save trained artifacts to `ml/artifacts/`.

**Order:** Yale first (required, everything depends on it), then X-ray (no training, fastest), then ECG.

## B2. Yale ED admission model (required)
- **Source:** Hong, Haimovich & Taylor, "Predicting hospital admission at emergency department triage using machine learning", PLOS ONE 2018. ~560,486 ER visits, 29.7% admitted. Published AUCs: triage information only 0.87; all variables with XGBoost 0.92. Performance plateaued at ≤50% of the training data, so **train on a 20–50% sample** to save time. Use the copy the organizers provided.
- **Inspect the file first.** Print the columns. Find the outcome column (admit vs. discharge), ESI, arrival mode, age, gender, triage vitals, and chief-complaint columns. Column names in my notes come from the paper and may not match. **Check temperature units** (likely °F; convert to °C in the feature mapping) and the oxygen-device column.
- **Leakage:** keep only information available at that moment. Drop anything recorded after triage (labs, imaging, disposition-related fields, length of stay). If a patient ID exists, split train/test **by patient**.
- **Two versions:**
  - `ambulance`: age, sex, arrival mode, chief complaint, triage vitals as a proxy for ambulance vitals. **No ESI, no hospital history** (paramedics don't have the hospital record).
  - `triage`: everything in `ambulance` + ESI (+ prior-visit counts only if they are clearly available at arrival).
  - Report both AUCs. The gap is our "insight" for the judges. Also report AUC for ambulance arrivals only, if arrival mode exists.
- **Model:** XGBoost (handles missing values natively). Check calibration on the test set, because the UI shows the probability as a percentage; apply isotonic calibration if it's off.
- **Top reasons:** per-prediction contributions (`pred_contribs=True` in XGBoost, or SHAP), mapped to plain labels like "Age 67", "Oxygen 89%", "ESI 2". Up to 3, positive direction first.
- **Feature mapping:** convert the contract's `features` dict (A6) into the model's columns, including mapping each `complaint_category` to the matching Yale chief-complaint columns. Document the mapping in the README.
- **Headline operating point:** at a 0.80 probability threshold on the test set, report "X% of admitted patients flagged" (sensitivity) and "Y of every 10 flags correct" (PPV). Also report the numbers at 0.5.

## B3. NIH chest X-ray flag (evaluate, don't train)
- Use `torchxrayvision`'s **CheXpert-trained** DenseNet (`densenet121-res224-chex`), **not** the NIH-trained one. Testing an NIH-trained model on NIH images would be testing on data it may have seen; a CheXpert-trained model tested on NIH is a fair outside test, which is a stronger story.
- Keep 5 findings that often lead to admission: Pneumonia, Effusion, Edema, Cardiomegaly, Pneumothorax. Confirm the exact names in `model.pathologies`.
- Data: the Kaggle "Random Sample of NIH Chest X-ray Dataset" (~5,600 images, `sample_labels.csv` with `Image Index` and pipe-separated `Finding Labels`). Don't download the full 112k set.
- Split the sample in half: choose each finding's threshold on half A, report AUC (and sensitivity/specificity at that threshold) on half B.
- Install: `pip install torchxrayvision scikit-learn pandas scikit-image`. Test on 10 images before the full run.
- Caveats to put in `metrics.json` notes: NIH labels were extracted automatically from radiology reports and contain errors; the output is a flag, not a diagnosis.
- **Open question for an organizer (Role 3 will ask):** does evaluating a pretrained model on NIH count as "using" the dataset? If not, fine-tune only the final layer on half A (~1 hour).

## B4. PTB-XL ECG flag (train)
- Use the 100 Hz records (`records100/`), `ptbxl_database.csv` and `scp_statements.csv` (`wfdb` to read signals).
- Label: **normal** = diagnostic superclass NORM only; **abnormal** = any of MI, STTC, CD, HYP. Drop records with no diagnostic label.
- Use the official folds: 1–8 train, 9 validation (pick the threshold), 10 test (report AUC once).
- Model: a small 1D CNN in PyTorch over the 12 × 1000 signal, a few epochs on CPU. **Fallback if time is short:** simple per-lead summary features + gradient boosting. Ship whichever finishes; say which on the slide.
- Optional if time allows: a separate "possible MI" probability.

## B5. `metrics.json` format
```json
{
  "yale_ambulance": {"auc": 0.0, "n_test": 0, "at_0.8": {"sensitivity": 0.0, "ppv": 0.0}, "at_0.5": {...}, "calibration": "isotonic|none"},
  "yale_triage": {...},
  "yale_ambulance_arrivals_only": {...},
  "ptbxl_ecg": {"auc": 0.0, "test_fold": 10, "threshold": 0.0, "sensitivity": 0.0, "specificity": 0.0, "model": "1D CNN|GBM"},
  "nih_xray": {"Pneumonia": {"auc": 0.0, "threshold": 0.0}, "...": {}, "n_eval": 0, "model": "xrv densenet121-res224-chex"},
  "notes": ["Datasets are from different patients; no combined model.", "NIH labels are NLP-derived and noisy."]
}
```
Fill with real measured values only.

## B6. Hand-offs to teammates
- **To Role 2 (as soon as each is ready):** the function, how to import it, and its expected latency. Keep signatures exactly as in A6 so they swap the stub for the real thing with one import change.
- **To Role 3:** `metrics.json`, the demo-asset list, and 3–4 plain-English sentences per model for the slides ("trained on X, tested on Y, AUC Z, here's the main limitation").
- Pick demo assets that make a good story: at least one clearly abnormal ECG (for the chest-pain patient), one normal ECG, one X-ray the model flags for pneumonia, and one normal X-ray.

## B7. Questions judges will ask me (prepare short answers)
- How do you combine three models trained on different patients? (Answer: we don't train a combination; written rules, shown on screen.)
- How did you prevent leakage in the Yale data?
- Why test on NIH instead of training on it?
- What happens when the model is wrong? (Raise-only rule; clinician review; it's a flag.)
- How would you validate this for real? (Linked data where the same patients have ER records, ECGs and X-rays, e.g. the MIMIC-IV family; then a silent pilot where predictions are logged but not shown.)
