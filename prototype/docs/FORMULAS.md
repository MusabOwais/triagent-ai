# Formulas

Every formula used by Triagent AI. The code is `app/scoring.py`; the Model A/B weights below are generated from `outputs/vitals_scorecard.json`, the file the code reads.

## 0. Score conversion (used at every stage)

```
score = max( 1 + round(99 · σ(L)),  F_NEWS2 )
σ(L)  = 1 / (1 + e^(−L))
```

| Variable | Meaning |
|---|---|
| `L` | Log-odds at the current stage: `L1` in the ambulance, `L2` after diagnostics |
| `σ(L)` | Sigmoid: turns log-odds into a probability between 0 and 1 |
| `F_NEWS2` | Safety floor from NEWS2 (section 4) |
| `score` | Risk score, 1 to 100 |

**Why:** one running number (`L`) lets each new piece of evidence be added. The floor means the score never sits below what the vital signs alone demand.

| Score | Band | Queue action |
|---|---|---|
| 80–100 | Critical | Front of every queue |
| 60–79 | High | Next available ECG, X-ray or bed |
| 40–59 | Moderate | Standard priority |
| 20–39 | Low | Can wait; waiting time raises priority |
| 1–19 | Minimal | Lowest priority; waiting time raises priority |

Before diagnostics the score is a calibrated admission probability (70 ≈ 70% of similar Yale patients admitted). After ECG/X-ray it is a priority score on the same scale.

## 1. Model B: ambulance score with chief complaint (default)

```
L_B = -1.829 + w_age + w_HR + w_SBP + w_DBP + w_RR + w_SpO2 + w_T + 0.817·O2 + 0.110·male + w_CC
```

Trained by L2-regularised logistic regression on 92,172 Yale ambulance arrivals (age ≥ 18). Predicts admission. Test AUROC 0.791. Find the range each vital falls in and add its weight; the normal (reference) range adds 0.

| Variable | Range: weight |
|---|---|
| Age (years) | 18-39: 0 · 40-54: +0.684 · 55-64: +1.133 · 65-74: +1.570 · 75-84: +1.869 · 85+: +1.926 |
| Heart rate (bpm) | 51-90: 0 · <=50: +0.407 · 91-110: +0.363 · 111-130: +0.848 · >=131: +1.260 |
| Systolic BP (mmHg) | 111-159: 0 · <=90: +0.908 · 91-100: +0.363 · 101-110: +0.180 · 160-199: +0.063 · >=200: +0.381 |
| Diastolic BP (mmHg) | 51-109: 0 · <=50: +0.527 · >=110: +0.194 |
| Resp rate (/min) | 12-20: 0 · <=11: +0.124 · 21-24: +0.416 · >=25: +0.807 |
| SpO2 (%) | >=96: 0 · <=91: +0.890 · 92-93: +0.329 · 94-95: +0.093 |
| Temperature (°F) | 96.9-100.4: 0 · <=95.0: +0.464 · 95.1-96.8: +0.160 · 100.5-102.2: +1.094 · >=102.3: +0.903 |
| Supplemental O2 (`O2` = 1) | +0.817 |
| Male (`male` = 1) | +0.110 |

**`w_CC`, chief complaint** (the main reason for the call; any complaint not listed adds 0):

| Complaint | Weight |
|---|---|
| Altered mental status | +0.928 |
| Weakness | +0.837 |
| Psychiatric evaluation | +0.735 |
| Abdominal pain | +0.602 |
| Shortness of breath | +0.553 |
| Suicidal | +0.508 |
| Vomiting | +0.482 |
| Chest pain | +0.285 |
| Syncope (fainting) | +0.265 |
| Other | +0.164 |
| Medical problem | +0.010 |
| Leg pain | -0.081 |
| Dizziness | -0.142 |
| Seizure (known history) | -0.166 |
| Cough | -0.194 |
| Headache, new | -0.250 |
| Fall | -0.317 |
| Back pain | -0.383 |
| Fall, age over 65 | -0.485 |
| Alcohol problem | -0.965 |
| Drug problem | -1.050 |
| Anxiety | -1.055 |
| Assault | -1.160 |
| Alcohol intoxication | -1.439 |
| Motor vehicle crash | -1.929 |

## 2. Model A: ambulance score without complaint (fallback)

```
L_A = -1.867 + w_age + w_HR + w_SBP + w_DBP + w_RR + w_SpO2 + w_T + 1.039·O2 + (-0.010)·male
```

Same patients and method, trained without the complaint. Used when no complaint is known (e.g., unresponsive patient, no bystander). Test AUROC 0.749.

| Variable | Range: weight |
|---|---|
| Age (years) | 18-39: 0 · 40-54: +0.654 · 55-64: +1.159 · 65-74: +1.656 · 75-84: +2.006 · 85+: +2.037 |
| Heart rate (bpm) | 51-90: 0 · <=50: +0.506 · 91-110: +0.319 · 111-130: +0.811 · >=131: +1.231 |
| Systolic BP (mmHg) | 111-159: 0 · <=90: +0.897 · 91-100: +0.337 · 101-110: +0.172 · 160-199: +0.076 · >=200: +0.379 |
| Diastolic BP (mmHg) | 51-109: 0 · <=50: +0.552 · >=110: +0.185 |
| Resp rate (/min) | 12-20: 0 · <=11: +0.150 · 21-24: +0.519 · >=25: +0.915 |
| SpO2 (%) | >=96: 0 · <=91: +0.810 · 92-93: +0.247 · 94-95: +0.023 |
| Temperature (°F) | 96.9-100.4: 0 · <=95.0: +0.483 · 95.1-96.8: +0.140 · 100.5-102.2: +1.276 · >=102.3: +1.090 |
| Supplemental O2 (`O2` = 1) | +1.039 |
| Male (`male` = 1) | -0.010 |

## 3. EMT overlay (hand-set: these inputs are not in Yale)

```
L1 = L_B (or L_A) + w_GCS + w_rhythm + w_injury + w_pain
score1 = max( 1 + round(99 · σ(L1)),  F_NEWS2 )
```

| Variable | Condition: weight |
|---|---|
| `w_GCS` | GCS ≤ 8: +2.0 · 9–12: +1.0 · 13–14: +0.5 · 15: 0 |
| `w_rhythm` | VF / VT / ST-elevation / complete heart block: +2.5 · AF with rapid response / SVT: +1.0 · other: 0 |
| `w_injury` (each) | Open fracture / amputation / uncontrolled bleeding: +1.5 · closed long-bone fracture / frostbite / burn: +0.7 |
| `w_pain` | Pain ≥ 8/10: +0.3 |

**Why:** the model predicts admission, and many crash patients are sent home, so serious injuries need these points to rank correctly.

## 4. NEWS2 safety floor

```
N = n_RR + n_SpO2 + n_O2 + n_SBP + n_HR + n_GCS + n_T
F_NEWS2 = 80 if N ≥ 7;  60 if N = 5–6;  45 if any single n = 3;  0 otherwise
```

| Variable | Value: points |
|---|---|
| `n_RR` | ≤8: 3 · 9–11: 1 · 12–20: 0 · 21–24: 2 · ≥25: 3 |
| `n_SpO2` | ≤91: 3 · 92–93: 2 · 94–95: 1 · ≥96: 0 |
| `n_O2` | Supplemental O2: 2 · room air: 0 |
| `n_SBP` | ≤90: 3 · 91–100: 2 · 101–110: 1 · 111–219: 0 · ≥220: 3 |
| `n_HR` | ≤40: 3 · 41–50: 1 · 51–90: 0 · 91–110: 1 · 111–130: 2 · ≥131: 3 |
| `n_GCS` | GCS 15: 0 · GCS < 15: 3 |
| `n_T` (°C) | ≤35.0: 3 · 35.1–36.0: 1 · 36.1–38.0: 0 · 38.1–39.0: 1 · ≥39.1: 2 |

NEWS2 (Royal College of Physicians, 2017) is not used to rank; it sets a minimum score.

## 5. ECG adjustment (model trained on PTB-XL)

```
Δ_ECG = 2.5·p_MI + 1.2·p_STTC + 0.8·p_CD + 0.3·p_HYP − 0.4·p_NORM
```

| Variable | Meaning |
|---|---|
| `p_MI` | Probability of myocardial infarction |
| `p_STTC` | Probability of ST/T-wave change |
| `p_CD` | Probability of conduction disturbance |
| `p_HYP` | Probability of hypertrophy |
| `p_NORM` | Probability of a normal ECG |

Probabilities come from a 1D ResNet (test macro AUROC 0.921) after Platt calibration. Weights are hand-set severity choices.

## 6. X-ray adjustment (model trained on NIH ChestX-ray14)

```
Δ_XR = 2.0·p_PTX + 1.2·p_EDE + 1.0·p_PNA + 1.0·p_CON + 0.8·p_EFF + 0.5·p_CMG + 0.5·p_MAS
     + 0.3·p_ATL + 0.3·p_INF + 0.1·p_CHR − 0.4·p_NORM
p_NORM = 1 − max(all 14 finding probabilities)
```

| Variable | Finding |
|---|---|
| `p_PTX` | Pneumothorax |
| `p_EDE` | Edema |
| `p_PNA` | Pneumonia |
| `p_CON` | Consolidation |
| `p_EFF` | Effusion |
| `p_CMG` | Cardiomegaly |
| `p_MAS` | Mass |
| `p_ATL` | Atelectasis |
| `p_INF` | Infiltration |
| `p_CHR` | Sum of nodule, emphysema, fibrosis, pleural thickening, hernia (mostly chronic) |
| `p_NORM` | Probability the film is normal |

DenseNet-121, test macro AUROC 0.708 on a small subset, so in this prototype a negative `Δ_XR` is set to 0.

## 7. Re-score after diagnostics

```
L2 = L1 + max(Δ_ECG, −0.5) + max(Δ_XR, −0.5)
score2 = max( 1 + round(99 · σ(L2)),  F_NEWS2 )
```

- Each test can lower the log-odds by at most 0.5.
- A negative Δ is set to 0 if that model's top probability is between 0.3 and 0.7 (model unsure).
- The NEWS2 floor still applies. Upward moves are uncapped.

## 8. Queue priority

```
P_s = L_current + 0.01 · t_wait,s      s = ECG or X-ray queue
P_k = L_current + 0.01 · t_wait        k = bed type
```

| Variable | Meaning |
|---|---|
| `L_current` | `L1` before diagnostics, `L2` after |
| `t_wait` | Minutes waiting (+0.6 log-odds per hour), kept if a patient moves to another bed list |

Highest `P` goes next. Override: chest pain or an ST-elevation / VT / VF rhythm goes to the front of the ECG queue (10-minute door-to-ECG standard).

## 9. Bed type (provisional in the ambulance, confirmed by an ER clinician)

First match wins.

| Bed type | Provisional, from the ambulance | After the ECG |
|---|---|---|
| ICU | `N` ≥ 7 | Stays ICU |
| CCU | Not assignable before an ECG | `p_MI` ≥ 0.5 |
| Telemetry | Complaint = chest pain or syncope | `p_STTC` ≥ 0.5 or `p_CD` ≥ 0.5 |
| Psychiatric | Complaint = suicidal or psychiatric evaluation, and `N` < 5 | No change |
| General ward | Everyone else | No change |
