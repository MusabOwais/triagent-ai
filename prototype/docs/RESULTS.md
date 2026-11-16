# Results

All numbers are on held-out test data that was scored once. Source files are in `outputs/`.

## 1. Ambulance score (Yale)

Population: Yale ED visits that arrived by ambulance, age ≥ 18, with HR, SBP and RR recorded. n = 92,172 (39.1% admitted). Split: 64% train, 16% validation, 20% test (18,435).

| Model | Inputs | Test AUROC (95% CI) | Max calibration gap |
|---|---|---|---|
| **Model B** | Age, sex, HR, SBP, DBP, RR, SpO2, supplemental O2, temp, chief complaint (25 most common) | **0.791** (0.784–0.798) | 3.9% |
| **Model A** | Same without complaint | **0.749** (0.742–0.758) | 3.1% |
| LightGBM, same inputs as B (upper bound) | | 0.801 | |
| LightGBM, same inputs as A | | 0.759 | |
| NEWS2 from the same vitals | | 0.621 | |

The transparent scorecards are within 0.01 AUROC of a black-box model on the same inputs.

Subgroup AUROC, Model B: Black 0.798, Other 0.791, White 0.779; female 0.780, male 0.802.

## 2. Medication leakage finding

Feature-group ablation on all 190,370 ambulance arrivals (LightGBM, same split):

| Features | Test AUROC |
|---|---|
| Vitals only | 0.654 |
| Demographics + vitals | 0.754 |
| + chief complaint | 0.818 |
| + past medical history | 0.830 |
| + prior visits / admissions (no meds) | 0.836 |
| Medication counts only | 0.807 |
| Everything incl. medication counts | 0.904 |
| Reference: nurse-assigned ESI alone | 0.635 |

Why medications were removed:

| | Admitted | Discharged |
|---|---|---|
| Mean recorded medications | 6.9 | 0.5 |
| Zero recorded medications | 33.2% | 90.4% |
| Zero recorded, age 65+, first ED visit | 25.6% | 80.7% |

Most adults over 65 take regular medications, so 81% of discharged older patients having none recorded is implausible. The counts appear to be filled in during admission (medication reconciliation), which leaks the outcome.

## 3. ECG model (PTB-XL)

Official protocol: folds 1–8 train (17,084), fold 9 validation (2,146), fold 10 test (2,158). Folds are patient-disjoint. 1D ResNet, 12 leads, 100 Hz. Best epoch chosen on fold 9.

| Class | Test AUROC | Flag at p ≥ 0.5: correct (PPV) | Cases caught (sensitivity) |
|---|---|---|---|
| Normal | 0.941 | 0.81 | 0.91 |
| Myocardial infarction | 0.924 | 0.73 | 0.75 |
| ST/T change | 0.934 | 0.79 | 0.71 |
| Conduction disturbance | 0.913 | 0.88 | 0.60 |
| Hypertrophy | 0.891 | 0.71 | 0.47 |
| **Macro** | **0.921** | | |

Published benchmark (Strodthoff et al.): 0.92–0.93.

## 4. Chest X-ray model (NIH subset)

4,999 images from 1,335 patients (`images_001`), patient-disjoint split 70/10/20. ImageNet-pretrained DenseNet-121.

Test macro AUROC **0.708** (published on full NIH: ~0.81–0.84). Best: edema 0.876, effusion 0.808. Weakest: nodule 0.540. Pneumonia (0.659) has only 12 test positives, so it is unreliable. Because of this, the X-ray term may only raise scores in the prototype.

## 5. Calibration (Platt scaling, fitted on validation, checked on test)

Expected calibration error before → after, examples: ECG MI 0.032 → 0.017, ECG CD 0.051 → 0.020, X-ray effusion 0.098 → 0.012, X-ray atelectasis 0.169 → 0.015.

## 6. Evidence for the bed-type rules

No dataset records which unit a patient was admitted to. What the data does show:

| Bed type | Rule | Yale ambulance arrivals matching | Admitted |
|---|---|---|---|
| ICU | NEWS2 ≥ 7 | 941 (0.5%) | 90.6% |
| Telemetry | Complaint chest pain or syncope | 16,996 (8.9%) | 57.6% |
| Psychiatric | Complaint suicidal / psych evaluation, NEWS2 < 5 | 9,586 (5.0%) | 40.2% |
| General ward | Everyone else | 162,746 (85.5%) | 46.3% |
| CCU | ECG p(MI) ≥ 0.5 | PTB-XL test: 73% of flags correct, 75% of MIs caught | |

Overall ambulance admission rate: 47.3%. An isolation-room rule (fever + cough/shortness of breath) matched only 92 patients, so it was dropped.
