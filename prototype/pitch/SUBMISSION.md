# Devpost submission: Triagent AI

**Track:** Best Clinical Impact
**Datasets:** Yale ED Admission Prediction, PTB-XL, NIH ChestX-ray14
**Tagline:** One record and one risk score that follow an emergency patient from the ambulance to the right hospital bed.

> Before submitting: any statistic about ER boarding or handoff loss in "Inspiration" must have its source checked and linked. The numbers in "How we built it" and "Accomplishments" are our own measured results and can stay as they are.

## Inspiration

Admitted patients often wait in the ER for hours until a hospital bed opens. While they wait, the information gathered by the ambulance crew is passed on verbally or on paper, and parts of it get lost at each handoff. Clinicians we spoke to told us ambulance information often never makes it into the hospital system, and that patients frequently get their chest X-ray while waiting for a bed. We wanted the details the crew collects to keep working for the patient all the way to the bed.

## What it does

- **In the ambulance**, the crew enters vitals, chief complaint, GCS, cardiac rhythm, visible injuries, history, medications, allergies and treatments. Triagent AI gives a **1–100 risk score**, shows exactly what moved it, and places a **provisional bed request** (ICU, CCU, Telemetry, Psychiatric or General ward) so the hospital can prepare.
- **At the ER door**, the whole record arrives as a digital handoff.
- **ECG and chest X-ray queues** are ordered by risk. Chest pain still gets an ECG within 10 minutes, whatever the score.
- **After each test**, our ECG and X-ray models adjust the score. Dangerous findings raise it. Reassuring findings can lower it only slightly, never when the model is unsure, and never below what the vital signs demand.
- **Each bed type has its own waitlist**, ordered by the same score plus waiting time. An ER clinician confirms the bed type; the app suggests and never assigns.
- **A second handoff** goes to the admitting team with the full record and a score history explaining every change ("71 → 91: ECG suggests MI").

## How we built it

- **Ambulance score (Yale).** We trained on 92,172 Yale ED visits that arrived by ambulance, using only what a crew can measure: age, sex, heart rate, blood pressure, breathing rate, SpO2, oxygen use, temperature and chief complaint. We grouped each vital into clinical ranges and fit a logistic regression, so the model is a transparent points table. Test AUROC 0.791, calibrated within 4%, within 0.01 of a black-box model on the same inputs, and well above NEWS2 (0.621).
- **ECG model (PTB-XL).** A 1D ResNet on 12-lead ECGs, trained with the official patient-disjoint folds. Test macro AUROC 0.921, matching published benchmarks.
- **Chest X-ray model (NIH).** A DenseNet-121 trained on a 5,000-image subset with patients kept separate across splits. Test macro AUROC 0.708. Because that is modest, the X-ray model may only raise scores in this prototype.
- **Safety layer.** NEWS2 sets a minimum score. Hand-set weights cover what the datasets lack (GCS, monitor rhythm, visible injuries). All model probabilities are calibrated.
- **Website.** FastAPI backend running the real models; plain HTML/JS frontend with three views: ambulance intake, ER board, patient handoff.

## Challenges we ran into

- **A result that looked too good.** Our first Yale model scored AUROC 0.904. Medication counts were the top feature, and 90% of discharged patients had zero medications recorded versus 33% of admitted patients. That pattern suggests medication lists are completed during admission, which would leak the outcome. We removed them and report the honest 0.79.
- **Three datasets, three different patient groups.** No patient appears in more than one dataset, so we could not train one combined model. We joined them with written, visible rules instead.
- **Admission is not severity.** The model gives car-crash patients low scores because most are discharged. We added an EMT overlay for serious injuries and a NEWS2 floor so sick patients are never ranked low.
- **No bed-unit labels anywhere.** We kept only bed types whose triggers exist in the data and checked each against admission rates (for example, the ICU rule matches patients admitted 91% of the time, versus 47% overall).

## Accomplishments that we're proud of

- An ECG model that matches the published PTB-XL benchmark (0.921).
- Catching and documenting a data leak instead of reporting the inflated number.
- A score a clinician can audit line by line: every weight is on screen and in the repo.
- Safety rules enforced in code and covered by tests: capped drops, no drops from unsure models, NEWS2 floor.

## What we learned

- Validate surprising features before trusting them.
- A simple, transparent model can match a black box when the inputs are limited.
- In clinical tools, what the system refuses to do (lower a score on weak evidence, assign a bed on its own) matters as much as what it does.

## What's next for Triagent AI

- Validate on real ambulance-recorded vitals and on ECGs recorded in the field.
- Train the X-ray model on the full NIH set (expected AUROC ~0.8) so reassuring films can safely lower scores.
- Have clinicians review the hand-set weights and bed rules.
- Simulate queue ordering against first-come-first-served using real arrival times.
- Role-based access control for patient privacy (HIPAA).

## Built with

Python, PyTorch, LightGBM, scikit-learn, FastAPI, HTML/CSS/JavaScript, Yale ED Admission data, PTB-XL, NIH ChestX-ray14.
