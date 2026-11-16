# frontend/ — the three screens (Role 3)

React + Vite + TypeScript + Tailwind. Ambulance form, patient view, bed board.

## Live link

https://relay-triage.vercel.app is the Vercel project `relay-triage`, connected to this repo: every push to `main` redeploys it from `frontend/`.

The hosted build needs no server. The Triagent AI scoring is ported to the browser (`src/api/relayEngine.ts`), with weights and rules exported from the Python code into `src/data/relay.json`. The Yale admission model runs live; ECG and X-ray use the trained models' stored outputs for the 16 demo samples. `npm run check:engine` confirms the port matches the Python backend (160 checks). Each visitor's patients live only in their own browser tab.

To run the same build locally: `npm run dev:browser`.

## Run it with the real models (for the demo)

Two terminals. First the backend from `prototype/`:

```bash
cd prototype
python3 -m venv .venv && .venv/bin/pip install fastapi "uvicorn[standard]" python-multipart numpy pillow torch torchvision
.venv/bin/python -m uvicorn app.server:app --port 8000
```

Then the screens:

```bash
cd frontend
npm install
npm run dev:live
```

Open http://localhost:5173. The chip in the header tells you what is running:

- **Live backend · real models**: the ECG and X-ray weight files are in `prototype/outputs/` and both models run live.
- **Live backend · ECG and X-ray results stored**: the weights are not on this machine, so the 8 ECG and 8 X-ray demo samples use results the trained models produced earlier (`prototype/app/samples/precomputed.json`). Scoring, bed rules and the Yale admission model still run live. Uploading your own X-ray needs the weights.

The browser only talks to port 5173; Vite forwards `/api` and `/samples` to port 8000, so the backend needs no CORS change.

## Run it with no backend

```bash
cd frontend && npm run dev
```

Built-in mock data with **stub models** (the header chip says so). Useful for working on the screens alone.

## How the data source is chosen

Everything goes through `src/api/`. Nothing else in the app knows where data comes from.

| Command | Data source |
|---|---|
| `npm run dev:live` (`VITE_API=relay`) | `src/api/relay.ts`: adapter for the Triagent AI backend in `prototype/` |
| `npm run dev` (`VITE_API=mock`) | `src/api/mock.ts`: in-browser store, rules from `docs/CONTRACT.md`, stub models |
| `VITE_API=contract VITE_API_URL=... npm run dev` | A backend that follows `docs/CONTRACT.md` (A6) exactly |

In live mode the screens show the backend's own score (risk score, NEWS2 floor, what moved it), complaint list, bed types and measured accuracy. Buttons the backend can't serve yet (repeat vitals, triage, clinician review of an AI flag) are hidden. See `docs/FRONTEND_INTEGRATION.md`.

## Where things are

- `src/api/types.ts` — data shapes (copied from the contract) and the `Api` interface
- `src/api/rules.ts` — NEWS2, bed priority, bed type, alerts, MIST/SBAR templates
- `src/api/relay.ts` — adapter for the real backend (`/api/...`)
- `src/api/mock.ts` — mock backend and the six seed patients
- `src/screens/Ambulance.tsx`, `Patient.tsx`, `Board.tsx` — the three screens
- `src/ui.tsx` — shared pieces (buttons, vitals fields, alert rows, polling hook)

## Demo path in live mode (2 minutes)

1. **Ambulance**: type a name, set SpO2 to 90 and breathing rate to 26. The risk score jumps live from the Yale model and the NEWS2 floor. Send to ER.
2. **Patient page**: mark arrived. Show the score strip (admission model, NEWS2 floor, crew findings), the handoff summary and the score history.
3. Open **R. Alvarez** (chest pain): the 10-minute ECG alert is on top. Record an ECG sample; the PTB-XL model re-scores and the bed type can change (needs the weights).
4. **Bed board**: choose **A bed just opened: Telemetry**. The top match is highlighted. Open **Review bed request**, type a name, confirm.
5. Scroll to **How every number is made** and **About the models** for the measured AUROCs.
