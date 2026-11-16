// Adapter for the Triagent AI backend in prototype/app/server.py (paths under /api).
// It translates that API into the shapes the screens use. Requests go to the same origin;
// vite.config.ts proxies /api and /samples to the backend, so no CORS setup is needed.
import { buildHandoff, cToF, fToC } from './rules'
import type {
  Alert, Api, DemoAssets, IntakeForm, ModelMetric, News2, Options, PatientRecord, PatientView, Strip, Vitals,
} from './types'

type Parts = [string, number][]
interface RMeta {
  complaints: { id: string; label: string }[]; rhythms: { id: string; label: string }[]; injuries: string[]; beds: string[]
  samples: { ecg: { id: string; age: number; sex: string; true_labels: string[] }[]; cxr: { id: string; file: string; true_labels: string[] }[] }
  models_loaded: { ecg: boolean; xray: boolean }
  /** Stored model outputs for the demo samples, used when the weights are not on this machine. */
  precomputed?: { ecg: boolean; xray: boolean }
  metrics: { model_b_auroc: number; model_a_auroc: number; ecg_auroc: number; cxr_auroc: number; n_yale: number }
}
interface RStage1 {
  model: 'A' | 'B'; L1: number; score_raw: number; news2: number; news2_parts: Record<string, number>; floor: number
  score: number; model_parts: Parts; overlay_parts: Parts; p_admit_model: number; bed: string; bed_reason: string
}
interface RDiag { source: string; probs: Record<string, number>; delta: number; note: string }
interface RIntake {
  name: string; age: number; sex: 'M' | 'F'; complaint: string | null; complaint_detail: string; onset: string; mechanism: string
  history: string; medications: string; allergies: string; treatments: string; hr: number; sbp: number; dbp: number; rr: number
  spo2: number; temp_f: number; o2: boolean; gcs: number; pain: number; rhythm: string; injuries: string[]
}
interface RView {
  id: string; intake: RIntake; status: 'incoming' | 'in ER' | 'bed assigned'; created_at: number; arrived_at: number | null
  stage1: RStage1; L: number; floor: number; score: number; ecg: RDiag | null; xray: RDiag | null
  events: { t: number; kind: string; text: string; score: number }[]
  queues: Partial<Record<'ecg' | 'xray', { minutes: number; override: boolean }>>
  bed: { type: string; status: 'provisional' | 'confirmed' | 'assigned'; reason: string; minutes: number; priority: number }
  minutes_since_handoff: number | null
}

const NAMES_KEY = 'relay-confirmed-by'
const names: Record<string, string> = (() => { try { return JSON.parse(sessionStorage.getItem(NAMES_KEY) || '{}') } catch { return {} } })()

async function httpCall<T>(path: string, body?: unknown): Promise<T> {
  let r: Response
  try {
    r = await fetch(path, body === undefined ? undefined : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  } catch { throw new Error('Cannot reach the backend on port 8000. Start it, then try again.') }
  const j = await r.json().catch(() => ({}))
  if (!r.ok) throw new Error(typeof j.detail === 'string' ? j.detail : r.status === 422 ? 'Some values are out of range. Check age (18–110), GCS (3–15) and pain (0–10).' : `The backend answered ${r.status}.`)
  return j as T
}

// Where requests go: the Python backend over HTTP, or the in-browser port of it (relayEngine.ts).
type Transport = (path: string, body?: unknown) => Promise<unknown>
let transport: Transport = httpCall
let inBrowser = false
const call = <T,>(path: string, body?: unknown) => transport(path, body) as Promise<T>
/** Switches the adapter to the in-browser engine. Used for the hosted static build. */
export function useBrowserEngine(t: Transport) { transport = t; inBrowser = true; return relayApi }

let metaP: Promise<RMeta> | null = null
const meta = () => (metaP ??= call<RMeta>('/api/meta').catch(e => { metaP = null; throw e }))

const iso = (t: number) => new Date(t * 1000).toISOString()
const sgn = (x: number) => `${x >= 0 ? '+' : '−'}${Math.abs(x).toFixed(2)}`
const sigmoid = (x: number) => 1 / (1 + Math.exp(-x))
const pretty = (s: string) => s.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase())
const N2_NAME: Record<string, string> = { RR: 'Breathing rate', SpO2: 'SpO2', O2: 'Air or oxygen', SBP: 'Systolic BP', HR: 'Pulse', GCS: 'Consciousness', Temp: 'Temperature' }
const ECG_NAME: Record<string, string> = { NORM: 'Normal', MI: 'Myocardial infarction', STTC: 'ST/T change', CD: 'Conduction disturbance', HYP: 'Hypertrophy' }

function toView(v: RView, m: RMeta): PatientView {
  const I = v.intake, s1 = v.stage1
  const complaint = I.complaint == null ? 'Unknown complaint' : m.complaints.find(c => c.id === I.complaint)?.label ?? 'Other complaint'
  const rhythm = m.rhythms.find(r => r.id === I.rhythm)?.label ?? I.rhythm
  const vitals: Vitals[] = [{
    time: iso(v.created_at), source: 'ambulance', heart_rate: I.hr, sbp: I.sbp, dbp: I.dbp, resp_rate: I.rr, spo2: I.spo2,
    temp_c: fToC(I.temp_f), on_oxygen: I.o2, gcs: I.gcs, pain: I.pain, rhythm,
  }]
  const when = (kind: string) => { const e = [...v.events].reverse().find(x => x.kind === kind); return e ? iso(e.t) : iso(v.created_at) }
  const effect = (d: RDiag) => `Score change: ${sgn(d.delta)} log-odds${d.note ? `. ${d.note}` : ''}.`
  const how = (live: boolean) => (live ? '' : '. Result stored from the trained model for this demo sample')

  const ecgHot = v.ecg ? ['MI', 'STTC', 'CD', 'HYP'].filter(c => v.ecg!.probs[c] >= 0.5) : []
  const xrFlagged = v.xray ? Object.keys(v.xray.probs).filter(k => v.xray!.probs[k] >= 0.5) : []
  const patient: PatientRecord = {
    id: v.id, demo: true, name: I.name.replace(/^Example patient:\s*/, ''), age: I.age, sex: I.sex,
    complaint_category: I.complaint ?? '__none', complaint_text: [I.complaint_detail, I.mechanism].filter(Boolean).join('. '),
    onset_time: I.onset, history: I.history, medications: I.medications, allergies: I.allergies, injuries: I.injuries,
    treatments: I.treatments ? [{ time: '', what: I.treatments }] : [], vitals, esi: null,
    arrival_time: v.arrived_at ? iso(v.arrived_at) : null,
    status: v.status === 'incoming' ? 'en_route' : v.status === 'bed assigned' ? 'in_bed' : v.bed.status === 'confirmed' ? 'bed_requested' : 'waiting',
    ecg: v.ecg && {
      record_id: v.ecg.source, time: when('ecg'),
      result: {
        abnormal_prob: Math.max(...['MI', 'STTC', 'CD', 'HYP'].map(c => v.ecg!.probs[c] ?? 0)), abnormal: ecgHot.length > 0, threshold: 0.5,
        model: `1D ResNet trained on PTB-XL, test AUROC ${m.metrics.ecg_auroc}${how(m.models_loaded.ecg)}`, note: 'AI flag, not a diagnosis',
        classes: Object.fromEntries(Object.entries(v.ecg.probs).map(([k, p]) => [ECG_NAME[k] ?? k, p])), effect: effect(v.ecg),
      },
    },
    xray: v.xray && {
      image_id: v.xray.source, time: when('xray'),
      result: {
        findings: Object.fromEntries(Object.entries(v.xray.probs).map(([k, p]) => [pretty(k), p])), flagged: xrFlagged.map(pretty),
        thresholds: {}, model: `DenseNet-121 trained on an NIH ChestX-ray14 subset, test AUROC ${m.metrics.cxr_auroc}${how(m.models_loaded.xray)}`,
        note: 'AI flag, not a diagnosis', effect: effect(v.xray),
      },
    },
    reviews: [],
    bed_request: v.bed.status === 'provisional' ? null : { bed_type: v.bed.type, confirmed_by: names[v.id] ?? 'an ER clinician', time: '' },
  }

  const band = s1.news2 >= 7 ? 'high' : s1.news2 >= 5 ? 'medium' : 'low'
  const news2: News2 = {
    value: s1.news2, band, complete: true, present: 7, trend: null, previous: null,
    parts: Object.fromEntries(Object.entries(s1.news2_parts).map(([k, x]) => [N2_NAME[k] ?? k, x])),
  }
  const top = s1.model_parts.filter(([k]) => k !== 'Intercept').sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 3)
  const raw = 1 + Math.round(99 * sigmoid(v.L))
  const after = [...s1.overlay_parts.map(([k, w]) => `${k} ${sgn(w)}`), ...(v.ecg ? [`ECG ${sgn(v.ecg.delta)}`] : []), ...(v.xray ? [`Chest X-ray ${sgn(v.xray.delta)}`] : [])]
  const added = s1.overlay_parts.reduce((a, b) => a + b[1], 0) + (v.ecg?.delta ?? 0) + (v.xray?.delta ?? 0)
  const scoring = Object.entries(news2.parts).filter(([, x]) => x).map(([k, x]) => `${k} +${x}`)
  const strip: Strip = {
    title: 'Risk score',
    formula: v.score > raw ? `Model gives ${raw}; raised to ${v.floor} by the NEWS2 floor` : `1 + 99 × sigmoid(${v.L.toFixed(2)}) = ${raw}`,
    cells: [
      { name: 'Admission model', value: `${Math.round(s1.p_admit_model * 100)}%`, sub: `Yale Model ${s1.model}`,
        lines: top.length ? top.map(([k, w]) => `${k} ${sgn(w)}`) : ['All inputs in the normal range.'],
        note: s1.model === 'B' ? 'Vitals and complaint. Share of similar Yale ambulance arrivals who were admitted.' : 'Vitals only (complaint unknown).' },
      { name: 'NEWS2', value: `${s1.news2}`, tone: band, sub: v.floor ? `sets a floor of ${v.floor}` : 'no floor',
        lines: scoring.length ? scoring : ['No vital sign is scoring.'], note: 'The score can never go below this floor.' },
      { name: 'Crew findings and tests', value: sgn(added), sub: 'log-odds',
        lines: after.length ? after : ['Nothing recorded yet.'], note: 'Hand-set weights awaiting clinician review.' },
    ],
  }

  const alerts: Alert[] = []
  if (v.queues.ecg?.override && v.arrived_at)
    alerts.push({ kind: 'protocol', level: v.queues.ecg.minutes > 10 ? 'critical' : 'warning', message: 'ECG due within 10 min of arrival', due_at: iso(v.arrived_at + 600) })
  const pending: string[] = []
  if (v.queues.ecg) pending.push(`ECG ordered, in queue ${Math.round(v.queues.ecg.minutes)} min`)
  if (v.queues.xray) pending.push(`Chest X-ray ordered, in queue ${Math.round(v.queues.xray.minutes)} min`)
  if (v.status === 'in ER' && v.bed.status === 'provisional') pending.push('Bed type not yet confirmed by a clinician')

  return {
    patient,
    scores: {
      admission: { probability: s1.p_admit_model, stage: 'ambulance', model: `Yale Model ${s1.model}`, top_reasons: top.map(([label, w]) => ({ label, direction: w >= 0 ? 'up' : 'down' })) },
      news2, findings: { points: 0, items: [] }, parts: { A: Math.round(s1.p_admit_model * 100), B: s1.news2 * 5, C: 0 },
      priority: v.score, wait_minutes: Math.round(v.minutes_since_handoff ?? 0), queue_rank_score: v.bed.priority, wait_bonus: null, strip,
    },
    bed_type: { suggested: v.bed.type, reason: v.bed.reason },
    alerts, pending,
    handoff: buildHandoff(patient, {
      complaint, injuries: I.injuries.map(pretty), bed: `${v.bed.type} (${v.bed.reason})`, news2,
      scoreLine: `Risk score ${v.score} of 100; admission model ${Math.round(s1.p_admit_model * 100)}%`,
      todo: [...alerts.map(a => a.message), ...pending],
    }),
    history: v.events.map(e => ({ time: iso(e.t), text: e.text, score: e.score })),
  }
}

function toIntake(f: IntakeForm) {
  const v = f.vitals[f.vitals.length - 1]
  const need = [v?.heart_rate, v?.sbp, v?.dbp, v?.resp_rate, v?.spo2, v?.temp_c]
  if (need.some(x => x === undefined)) throw new Error('The model needs pulse, both blood pressures, breathing rate, SpO2 and temperature.')
  return {
    name: f.name, age: f.age, sex: f.sex, complaint: f.complaint_category === '__none' ? null : f.complaint_category,
    complaint_detail: f.complaint_text, onset: f.onset_time, history: f.history, medications: f.medications, allergies: f.allergies,
    treatments: f.treatments.map(t => `${t.what} ${t.time}`.trim()).join('; '),
    hr: v.heart_rate, sbp: v.sbp, dbp: v.dbp, rr: v.resp_rate, spo2: v.spo2, temp_f: cToF(v.temp_c!), o2: !!v.on_oxygen,
    gcs: v.gcs ?? 15, pain: v.pain ?? 0, rhythm: v.rhythm || 'sinus', injuries: f.injuries, order_ecg: true, order_xray: true,
  }
}

const source = { label: 'Live backend · checking models', mock: false }
const one = async (p: Promise<RView>) => toView(await p, await meta())
const unsupported = () => Promise.reject(new Error('The backend does not support this yet.'))

export const relayApi: Api = {
  source,
  can: { repeatVitals: false, triage: false, review: false, ambulanceEcg: false, avpu: false, glucose: false },
  async options(): Promise<Options> {
    const m = await meta()
    const can = (k: 'ecg' | 'xray') => m.models_loaded[k] || !!m.precomputed?.[k]
    source.label = inBrowser ? 'Browser demo · Yale model live, ECG and X-ray stored'
      : m.models_loaded.ecg && m.models_loaded.xray ? 'Live backend · real models'
      : can('ecg') && can('xray') ? 'Live backend · ECG and X-ray results stored' : 'Live backend · ECG and X-ray weights missing'
    return {
      complaints: [...m.complaints, { id: '', label: 'Other, not listed' }, { id: '__none', label: 'Unknown, patient cannot say' }],
      injuries: m.injuries.map(id => ({ id, label: pretty(id) })), beds: m.beds.map(id => ({ id, label: id })), rhythms: m.rhythms,
      scoreName: 'Risk score', injuryNote: 'Hand-set weights — clinician review needed',
    }
  },
  async board() {
    const [b, m] = await Promise.all([call<{ patients: RView[] }>('/api/board'), meta()])
    return b.patients.map(v => toView(v, m)).sort((a, c) => c.scores.queue_rank_score - a.scores.queue_rank_score)
  },
  patient: id => one(call(`/api/patients/${id}`)),
  async preview(f) {
    const body = toIntake(f), r = await call<RStage1>('/api/preview', body), t = Date.now() / 1000
    return toView({
      id: 'preview', intake: { mechanism: '', ...body } as RIntake, status: 'incoming', created_at: t, arrived_at: null, stage1: r, L: r.L1,
      floor: r.floor, score: r.score, ecg: null, xray: null, events: [], queues: {},
      bed: { type: r.bed, status: 'provisional', reason: r.bed_reason, minutes: 0, priority: r.L1 }, minutes_since_handoff: null,
    }, await meta())
  },
  create: f => one(call('/api/patients', toIntake(f))),
  arrive: id => one(call(`/api/patients/${id}/arrive`, {})),
  addVitals: unsupported, triage: unsupported, review: unsupported,
  ecg: (id, sample_id) => one(call(`/api/patients/${id}/ecg`, { sample_id })),
  xray: (id, sample_id) => one(call(`/api/patients/${id}/xray`, { sample_id })),
  bedRequest(id, type, by) {
    names[id] = by; try { sessionStorage.setItem(NAMES_KEY, JSON.stringify(names)) } catch { /* private mode */ }
    return one(call(`/api/patients/${id}/bed/confirm`, { type }))
  },
  async rules() { return RELAY_RULES },
  async metrics(): Promise<ModelMetric[]> {
    const m = await meta(), k = m.metrics
    const off = m.precomputed?.ecg ? ' On this machine the demo samples use results stored from the trained model.' : ' Weights are not on this machine, so this model cannot run here.'
    return [
      { name: 'Admission risk', dataset: 'Yale ED admissions', result: `Test AUROC ${k.model_b_auroc} with complaint · ${k.model_a_auroc} vitals only`,
        note: `Transparent points table (logistic regression) trained on ${k.n_yale.toLocaleString()} ambulance arrivals. Medication counts were removed because they leak the outcome.` },
      { name: 'ECG', dataset: 'PTB-XL', result: `Test macro AUROC ${k.ecg_auroc}`,
        note: `1D ResNet, 5 classes, official patient-disjoint folds (tested on fold 10).${m.models_loaded.ecg ? '' : off}` },
      { name: 'Chest X-ray', dataset: 'NIH ChestX-ray14', result: `Test macro AUROC ${k.cxr_auroc}`,
        note: `DenseNet-121 trained on a 4,999-image subset. Because this is modest, it may only raise scores.${m.models_loaded.xray ? '' : off}` },
    ]
  },
  async assets(): Promise<DemoAssets> {
    const m = await meta(), why = 'The model weights are not on this machine, so this step cannot run here.'
    return {
      ecgs: m.samples.ecg.map((s, i) => ({ id: s.id, label: `ECG sample ${i + 1} · ${Math.round(s.age)} y ${s.sex}`, truth: s.true_labels })),
      xrays: m.samples.cxr.map((s, i) => ({ id: s.id, label: `X-ray sample ${i + 1}`, image_url: `/samples/cxr/${s.file}`, truth: s.true_labels })),
      unavailable: { ecg: m.models_loaded.ecg || m.precomputed?.ecg ? undefined : why, xray: m.models_loaded.xray || m.precomputed?.xray ? undefined : why },
    }
  },
  async reset() { await call('/api/reset', {}) },
  async ecgTrace(id) { return (await call<{ data: number[][] }>(`/api/samples/ecg/${id}`)).data[1] },
}

// Summarised from prototype/app/scoring.py. The full table of weights is in prototype/docs/FORMULAS.md.
const RELAY_RULES = `RISK SCORE (1–100) = 1 + 99 × sigmoid(L), never below the NEWS2 floor
  L (log-odds) = Yale admission model + crew findings + ECG change + X-ray change
  Before any test, the score is a calibrated admission probability: 70 ≈ 70% of similar Yale ambulance arrivals were admitted.

ADMISSION MODEL (trained on Yale)
  Model B: age, sex, pulse, blood pressure, breathing rate, SpO2, oxygen, temperature and chief complaint.
  Model A: the same without the complaint, used when the patient cannot say.
  A transparent points table: every weight is in the repository.

NEWS2 FLOOR (the model predicts admission, not severity, so NEWS2 sets a minimum)
  NEWS2 7 or more → at least 80 · NEWS2 5–6 → at least 60 · any single vital sign scoring 3 → at least 45

CREW FINDINGS (hand-set weights, awaiting clinician review)
  GCS, monitor rhythm, visible injuries and pain 8 or more add to L.

ECG AND CHEST X-RAY
  Dangerous findings raise the score. A reassuring ECG can lower it by at most 0.5, and never when the model is unsure.
  The X-ray model may only raise scores in this proof of concept.

QUEUES
  Queue priority = L + 0.01 × minutes waiting, so nobody waits forever.
  Chest pain, or a STEMI, VT or VF rhythm, goes to the front of the ECG queue (10-minute ECG rule) whatever the score.

BED TYPE (provisional until a clinician confirms)
  NEWS2 7 or more → ICU · ECG suggests MI → CCU · chest pain, syncope, or ST/T or conduction change on ECG → Telemetry
  Suicidal thoughts or psychiatric evaluation with NEWS2 under 5 → Psychiatric · otherwise → General ward
  The app suggests. It never assigns a bed on its own.

WHAT THIS DOES NOT DO YET
  The Yale data records triage vitals, used here as a stand-in for ambulance vitals. Real ambulance data is the next test.
  The model predicts admission, not severity. Severe cases are caught by the NEWS2 floor and crew findings, not the model.
  The X-ray model was trained on a small subset (AUROC 0.708), so it can raise a score but never lower one.
  Crew-finding weights, ECG and X-ray weights and bed rules are hand-set and await clinician review.
  A score does not create beds. We do not claim shorter waits.
  No hospital-system integration and no role-based access (HIPAA) yet. All patients shown are fictional.

The three datasets come from different patients. They are combined by these written rules, not by one trained model.`
