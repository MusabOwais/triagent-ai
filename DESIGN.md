# Design: Arrivals board

Written from the built frontend (`frontend/src`). Direction seed `963344be`.

## The idea

The ER read as an arrivals board. Patients are rows on one board, not cards on a dashboard. Scores sit on split-flap tiles that flip when they change. Scene it was chosen for: a charge nurse glancing up at a wall board across a bright, noisy ER, and judges reading a laptop at arm's length, so the ground is matte dark with large warm-white characters.

## Colour (tokens in `frontend/src/index.css`)

| Token | Value | Use |
|---|---|---|
| `page` | `#0c0e0f` | Board ground, input wells |
| `surface` / `sunk` | `#15181a` / `#1d2124` | Panels / inset blocks |
| `ink` / `muted` | `#f4f0e6` / `#a6aaa2` | Characters / secondary text |
| `line` | `#2d3236` | Hairlines |
| `action` | `#ffd60a` | **The next decision only**: primary button, "next" stop on the journey, protocol band, open-bed match, clock |
| `ok` `warn` `crit` | `#62d992` `#ffa64d` `#ff6259` | Lamps for clinical state (NEWS2 bands, alerts). Never decoration |
| `info` | `#a9cdfc` | Neutral labels ("Fictional demo patient", "Ambulance") |

Rules: yellow never marks a plain link or a decoration. Critical bands are solid red with black text. ECG strips stay pink paper with a dark trace, as printed.

## Type

One grotesque in two widths: **Barlow Condensed** (600/700, uppercase, tracked) for the brand, headings, patient names, bed types, buttons, chips, table heads and flap tiles; **Barlow** (400–700) for body, labels and values. Numbers are tabular.

## Components

- **Flap tiles** (`Flaps`): one character per tile with a hinge line. Keyed by value, so a changed score flips (0.34 s). The only authored motion; off under reduced motion.
- **Lamp** (`Lamp`): filled = done or on, hollow = not yet. State is never colour alone.
- **Journey line**: five fixed stops (Ambulance, ER door, ECG, Chest X-ray, Bed); the next one is yellow.
- **Bands** (`AlertRow`): full-width, uppercase. Yellow = next protocol step with countdown, orange = getting worse, red = overdue or critical.
- **Plates**: buttons, chips, inputs and panels use 3–4 px corners. Primary button is the yellow plate; secondary is an outlined plate.
- **Board rows**: rank, name in condensed caps, flap score, NEWS2 chip, bed type in condensed caps, time waited.

## Layout

Sticky black header with brand, two tabs, live clock, data-source chip (moves to the footer on phones) and Reset demo. Content max width 1240 px. Tables scroll inside their own container on phones; nothing else scrolls sideways.

## Not yet reviewed

Checked by me on desktop (1280×720) and phone (375×812). No independent design review was run.
