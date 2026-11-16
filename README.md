# Triagent AI

**Live demo: https://triagent-ai.vercel.app** (runs in the browser; each visitor gets a private copy, **Reset demo** restores the example patients)

Built at SacHacks HackRx (UC Davis Betty Irene Moore School of Nursing), for the **Best Clinical Impact** track.

A proof-of-concept website that follows an emergency patient from the ambulance to a hospital bed. Paramedics enter vitals and visible injuries, and every next provider sees and adds to the same record. The app shows a **bed-priority score** built from three visible parts:

- **A. Needs a bed:** admission probability from a model trained on the Yale ED admission dataset
- **B. Sick right now:** NEWS2, recalculated with every new set of vitals
- **C. Findings:** ECG flag (model trained on PTB-XL), chest X-ray flag (CheXpert-trained model tested on NIH), visible-injury points

Urgent tests follow hospital protocols (for example, ECG within 10 minutes for chest pain), not the score. AI findings can only raise the score; lowering it needs a clinician. The charge nurse confirms every bed request; the app only suggests.

The full spec, scoring rules and API contract are in [docs/CONTRACT.md](docs/CONTRACT.md).

## Who owns what

| Folder | Owner | Contents |
|---|---|---|
| `ml/` | Role 1: ML engineer | Yale, PTB-XL and NIH models, `metrics.json`, demo assets |
| `backend/` | Role 2: backend and clinical logic | FastAPI app, NEWS2, scoring, rules, handoff summaries, seed patients, tests |
| `frontend/` | Role 3: frontend, demo and pitch | Ambulance form, patient view, bed board |
| `pitch/` | Role 3 | Slides, demo script, Devpost text |
| `prompts/` | Everyone | One master prompt per role. Paste yours into a new Claude chat. |

## Working together

- Work inside your own folder. If you need to touch someone else's, tell them first.
- Commit small and push often: `git pull --rebase` before every `git push`.
- Never commit datasets, model weights or `.env` files. `.gitignore` already blocks the usual paths. Put data in `ml/data/`.
- Any change to the API or data shapes in `docs/CONTRACT.md` needs a heads-up to the whole team.

## Running it

Filled in as each part lands:

```bash
# backend (Role 2)
cd backend && pip install -r requirements.txt && uvicorn app:app --reload --port 8000

# frontend (Role 3)
cd frontend && npm install && npm run dev
```

## Honesty notes

Demo patients are fictional composites. The three datasets come from different patients, so they are combined by written rules shown in the app, not by one trained model. Injury points and bed-type rules are drafts awaiting clinician review. A real version would limit access by role (HIPAA).
