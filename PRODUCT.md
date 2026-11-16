# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

React + Vite + TypeScript + Tailwind in `frontend/` (set by the Role 3 brief). Backend is FastAPI, owned by a teammate.

## Users

- **Paramedic**, in a moving ambulance, on a phone: enters vitals, injuries and history once.
- **ER nurse and ER doctor**, at a desktop: read one patient's record, add vitals and tests, review AI flags.
- **Charge nurse / bed manager**, at a desktop or wall screen: sees who is waiting, who is getting worse, and confirms bed requests.
- **Hackathon judges (clinicians, researchers, sponsors)** see it on a laptop at the team's table, standing close.

## Product Purpose

Triagent AI is a proof of concept that follows an emergency patient from the ambulance to a hospital bed with one shared record. It shows a bed-priority score built from visible parts, protocol alerts for time-critical tests, and automatic handoff summaries. Success: the sickest patient gets the next suitable bed, nobody gets worse unnoticed, and staff stop re-entering the same information.

## Positioning

Every number on screen can be explained in one tap, AI findings can raise a score but never lower it without a clinician, and the app suggests while a human decides.

## Operating Context

Bright ER lighting, interrupted attention, shared screens. Clinical formats already in use: NEWS2, ESI, MIST and SBAR handoffs, ECG within 10 minutes for chest pain.

## Capabilities and Constraints

- Three screens only: ambulance form, patient view, bed board.
- All patients are fictional demo composites and are labeled as such.
- Injury points and bed-type rules are drafts awaiting clinician review and are labeled as such.
- No login. A real version would limit access by role (HIPAA).
- The backend API is still changing; the frontend talks to it through one swappable data layer (`frontend/src/api`).

## Evidence on Hand

Measured model results live in the teammate's `prototype/outputs/` on the `relay-triage-prototype` branch. No statistics about ER boarding or handoff loss are verified yet; none may appear in the UI.

## Product Principles

1. Never show a clinical fact nobody entered and no labeled model produced.
2. Explain every number where it is shown.
3. Colour means clinical state, nothing else.
4. The app suggests; a named human confirms.

## Accessibility & Inclusion

Readable at arm's length and on a phone held in one hand; state is never carried by colour alone.
