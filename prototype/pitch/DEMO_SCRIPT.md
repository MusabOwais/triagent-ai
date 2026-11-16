# Demo script (about 2 minutes)

Before you start: run the server, open http://localhost:8000, click **Reset demo**. Keep the formulas page open in a second tab.

| Time | Screen | Say | Do |
|---|---|---|---|
| 0:00 | ER board | "Ambulance information arrives on paper and gets lost at each handoff. Triagent AI keeps one record and one risk score from the ambulance to the bed." | Point at the legend: 1–100, five bands. |
| 0:15 | Ambulance | "A paramedic enters what they measure. The score is a model trained on 92,000 Yale ambulance arrivals." | Open **Ambulance**. Set age 68, complaint chest pain, HR 104. Change SpO2 to 89 and tick oxygen: the score jumps and the NEWS2 floor appears. |
| 0:35 | Ambulance | "Every point is explained: these bars show what moved the score. Chest pain gives a provisional telemetry bed request, so the hospital can prepare." | Point at **What moved the score** and **Provisional bed**. Enter a name, click **Send handoff to ER**. |
| 0:50 | Patient | "On arrival the full handoff is here: allergies, medications, treatments with times. Nobody has to re-ask." | Click **Mark arrived and receive handoff**. |
| 1:00 | ER board | "ECG and X-ray queues are ordered by risk. Chest pain jumps the ECG queue: the 10-minute rule is a protocol, not a score." | Open **ER board**, point at the red **10-min ECG rule** chip. |
| 1:10 | Patient (R. Alvarez) | "Now the ECG. This is a real held-out ECG run through our PTB-XL model, which scores 0.92 AUROC." | Open Alvarez, choose **ECG sample 3**, click **Run ECG model**. Score rises to about 91; bed changes to CCU. |
| 1:30 | Patient | "The score history explains every change. A normal test can lower urgency a little, never below what the vitals demand, and our weaker X-ray model can only raise scores." | Point at **Score history** and the **Demo transparency** label. |
| 1:45 | Patient → Board | "Each bed type has its own waitlist. The clinician confirms; the app never assigns a bed." | Click **Confirm bed type**, go to the board, show the CCU list. |
| 1:55 | — | "We also found a data leak in Yale: medication lists inflated accuracy from 0.79 to 0.90. We removed them and report the honest number." | End. |

## Likely judge questions

- **Is this validated on ambulance data?** No. Yale vitals are ER triage vitals of ambulance arrivals, minutes later. Field validation is next.
- **Why does a car crash score low?** The model predicts admission and most crash patients go home. Serious injuries add overlay points, and NEWS2 sets a floor.
- **Where do the ECG/X-ray weights come from?** Hand-set severity choices. No dataset links imaging to outcomes. They are on screen and in docs/FORMULAS.md for review.
- **Can the AI lower someone's priority?** Only by a capped amount, never when unsure, never below the NEWS2 floor. The X-ray model cannot lower at all yet.
- **Does this shorten waits?** We do not claim that. A score does not create beds. It helps the sickest patient get the next suitable bed and keeps information from being lost.
