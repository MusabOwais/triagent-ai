# Contract change notes (from Role 2)

Paste these to the team. Nothing below is active yet: the backend follows docs/CONTRACT.md exactly. Proposals 1 and 2 are built and can be switched on in `backend/config.py`.

---

## Contract change 1 (proposed): NEWS2 sets a minimum bed priority

**Problem.** `(A + B) / 2` lets a low admission probability hide an unstable patient. NEWS2 7 (emergency band) gives B = 35; with A = 20 the priority is 28, below stable patients. The Yale model gives low A to crash, intoxication and assault patients, because most of them are discharged.
**Change.** Priority is at least 70 if NEWS2 ≥ 7, at least 50 if NEWS2 is 5–6, and at least 40 if any single parameter scores 3.
**Who is affected.** Role 3: show "NEWS2 floor applied" next to the score when it fires. No field changes.
**Switch.** `NEWS2_PRIORITY_FLOOR = True`.

## Contract change 2 (proposed): NEWS2 status alert even without a rise

**Problem.** NEWS2 guidance calls for an emergency response at 7+ and an urgent response when a single parameter scores 3, even on the first reading. Under the current rule, a patient who arrives at NEWS2 9 and stays there never alerts.
**Change.** Keep the rise-based deterioration alert. Add one alert on the latest complete set: NEWS2 ≥ 7 → critical "emergency review"; single parameter = 3 → warning "urgent review". Same alert shape (`kind: "deterioration"`).
**Who is affected.** Role 3 only sees more alerts of an existing kind.
**Switch.** `NEWS2_STATUS_ALERTS = True`.

## Contract change 3 (proposed, needs Role 1): define "ECG abnormal"

**Problem.** PTB-XL "not normal" includes hypertrophy and old changes, which would send many patients to telemetry.
**Change.** `abnormal` = myocardial infarction, ST/T change or conduction disturbance above threshold, not simply "not normal". Optional extra field `classes: {"MI": 0.8, ...}` so the backend can raise a critical "possible acute ECG changes — physician review now" alert.
**Who is affected.** Role 1 (definition of `abnormal`), Role 2 (optional alert).

## Clarification A (built this way, no shape change): incomplete NEWS2

B uses the parameters present. `news2.complete = false` and `news2.present = n` are returned, and "Vitals incomplete (n/7 …)" appears in `pending`. Deterioration alerts use complete sets only. Role 3: show "NEWS2 ≥ x (n/7)" when incomplete.

## Clarification B (built this way): raise-only with repeat tests

A later normal AI read does **not** clear an earlier unreviewed abnormal flag; it is noted in `patient.notes` and the flag stays until a clinician review. A clinician review only applies to the result it was made on: a newer abnormal result brings the points back.

## Clarification C (built this way): ICU rule with incomplete vitals

A partial NEWS2 sum of 7+ already means NEWS2 ≥ 7, so it triggers "ICU review" even when incomplete. The reason string says "from n/7 parameters".

## New field (additive): `patient.notes`

List of strings for audit notes such as the repeat-ECG note above. Additive; nothing existing changes.

## Heads-up for Role 1: Yale medication columns leak the outcome

We measured this on the Yale data: 90% of discharged patients have zero recorded medications vs 33% of admitted patients (81% zero even among discharged patients aged 65+ on their first visit). Including `meds_*` columns inflates AUROC from about 0.84 to 0.90. The contract's feature list is already clean; just don't add them.

## Heads-up for Role 3: wording of the "insight"

Yale has no ambulance-recorded vitals: both model stages use **triage** vitals and differ only by ESI. Accurate wording: "how much the triage nurse's ESI adds on top of what an ambulance can measure." For reference, ESI alone predicted admission at AUROC 0.635 on Yale ambulance arrivals.
