# ml/ — Role 1: the three models

Three AI flags for the bed-priority score (spec: `prompts/1-ML-engineer.md`, signatures: `docs/CONTRACT.md` A6).
Each is labelled "AI flag, not a diagnosis", and every number in `metrics.json` comes from running the
scripts below on held-out data. Put downloaded datasets in `ml/data/` (git-ignored).

| Function | Trained on | Tested on | Model |
|---|---|---|---|
| `predict_admission(features, stage)` | Yale ED visits (sample) | Yale held-out 15% | XGBoost + isotonic calibration |
| `flag_ecg(record_id)` | PTB-XL folds 1–8 | PTB-XL fold 10 | small 1D CNN (GBM fallback) |
| `flag_xray(image_id)` | CheXpert (by torchxrayvision authors) | NIH sample, half B | DenseNet121 (optional NIH linear probe) |

## Install (once, before the venue if possible)

```bash
pip install -r ml/requirements.txt
python -m ml.xray download-weights        # caches CheXpert weights in ml/artifacts/xrv_weights (28 MB)
```

All commands run from the **repo root**.

## Run order (Yale first, then X-ray, then ECG)

```bash
# 1. Yale admission
python ml/inspect_yale.py /path/to/yale_file.rdata --slim ml/data/yale_slim.parquet
python -m ml.admission train ml/data/yale_slim.parquet            # --frac 0.2 for speed; --site-holdout optional
python -m ml.admission demo                                       # two example predictions + latency

# 2. NIH X-ray (Kaggle "Random Sample of NIH Chest X-ray Dataset" folder)
python -m ml.xray evaluate --nih-dir /path/to/nih_sample --limit 10   # sanity check first
python -m ml.xray evaluate --nih-dir /path/to/nih_sample              # full run, ~10–20 min on CPU
#   add --ship probe if organizers require training on NIH (reruns from cache in seconds)

# 3. PTB-XL ECG
python -m ml.ecg prepare --ptbxl-dir /path/to/ptb-xl-1.0.3
python -m ml.ecg train                       # 1D CNN, 12 epochs
python -m ml.ecg train --model gbm           # fallback if the CNN is too slow or weak

# 4. Demo assets + tests
python -m ml.demo_assets build --ptbxl-dir /path/to/ptb-xl-1.0.3
python -m pytest ml/tests -q
```

If the Yale column auto-detection picks the wrong column, override it:
`--col esi=acuity --col o2_device=triage_vital_o2_device`.

## Backend usage (Role 2)

```python
from ml import predict_admission, flag_ecg, flag_xray   # import ONCE at startup (5–10 s for torch)
```

* **`predict_admission(features, stage)`**: contract A6 output. Behaviour:
  * `stage="triage"` with `esi=None` → runs the ambulance model and returns `"stage": "ambulance"`.
  * Any feature may be `None` (handled as missing). Implausible vitals are treated as missing.
  * `ValueError` for: age < 18 (adult-only training data), unknown `complaint_category`, `sex` not M/F/None,
    `arrival_mode` not ambulance/walk_in/None.
  * `top_reasons`: up to 3 per-prediction model contributions (XGBoost `pred_contribs`), "up" first.
    They explain the model's arithmetic, not medical causes. Values nobody entered are never used as reasons.
  * ~3 ms per call.
* **`flag_ecg(record_id)`**: accepts `"ptbxl_12345"` or `"12345"`. ~10 ms.
* **`flag_xray(image_id)`**: e.g. `"00001234_000.png"`. ~150 ms on CPU.
* Both flag functions only accept ids in `ml/demo_assets.json` and raise **`KeyError`** otherwise.
  The backend should catch it and show "AI result unavailable".
* If torch can't load on the presenting laptop, the flag functions serve the stored output of the same
  model for demo assets, with the note "(precomputed by the same model)".
* Image/ECG files for the frontend: paths in `demo_assets.json` are relative to `ml/`.

## Design decisions (the short version for judges)

**Yale: same inputs at training and prediction time.** The model uses only fields the app collects
(contract A6): age, sex, arrival mode, one of 8 complaint categories, triage vitals, and ESI
for the triage version. Yale's ~200 chief-complaint columns are collapsed into the 8 categories by keyword,
with a fixed priority order when several apply (stroke > chest pain > breathing > altered mental status >
trauma > fever/infection > abdominal > other). The exact column → category table is written to
`artifacts/complaint_mapping.json` at training time and should be reviewed. Because we use far fewer
variables than the paper, our AUC isn't comparable to its 0.87/0.92.

**Leakage.**
* No post-triage data, prior-visit history, labs or imaging go into the model.
* Race, ethnicity, insurance, religion and language are never features. They are used only to report subgroup AUCs.
* Split is train 70 / calibration 15 / test 15. Calibration is fitted on its own split, and the test set is used once.
* If the file has no patient ID, repeat visits can sit in both train and test, which makes results slightly optimistic. `metrics.json` says so.
* PTB-XL uses the official patient-separated folds.
* NIH is split by `Patient ID`.
* Demo assets come only from held-out data (PTB-XL fold 10, NIH half B), and a test checks this.

**"Ambulance" vs "triage" models.** The ambulance version uses triage vitals as a stand-in for
paramedic vitals, so on slides say "data a paramedic could collect". `metrics.json` also reports
ESI alone and a partial NEWS2 (6 of 7 parameters) as baselines on the same test rows.

**X-ray: why a CheXpert model on NIH.** Testing an NIH-trained model on NIH images would test on data it may
have seen. A CheXpert-trained model on NIH is an outside test. The NIH-adapted linear probe is reported
too, in case "using NIH" has to mean training on it. Thresholds come from half A (Youden), and results from half B.
The bed score adds +10 if **any** of 5 findings is flagged, so `nih_xray.any_flag` reports that combined rate.

**ECG: "abnormal" ≠ acute.** Abnormal = any of MI, STTC, CD, HYP, which includes old infarcts, bundle branch
blocks and LVH. This is not a STEMI detector. Time-critical ECG care stays on protocol.

## Files

| Path | What |
|---|---|
| `admission.py`, `ecg.py`, `xray.py` | training/evaluation CLIs + contract functions |
| `inspect_yale.py` | step-1 column inspection of the Yale file |
| `demo_assets.py` | picks held-out demo assets, copies them, writes `demo_assets.json` with true labels |
| `common.py` | paths, `metrics.json` writer, AUC + bootstrap CI, threshold helpers |
| `metrics.json` | every measured number (written by the scripts, never by hand) |
| `artifacts/` | trained models, calibration, thresholds, CheXpert weights |
| `data/` | local datasets and caches (git-ignored) |
| `tests/test_ml.py` | contract, latency, fallback, bad-input and held-out checks |
