// In-browser stand-in for the backend. Follows docs/CONTRACT.md so the screens can be built
// and rehearsed before the real API is wired. The "models" here are STUBS with fixed outputs.
import { BED_LABEL, COMPLAINTS, computeView, INJURIES, news2Of, RULES_TEXT } from './rules'
import type {
  Api, DemoAssets, EcgResult, IntakeForm, PatientRecord, PatientView, Vitals, XrayResult,
} from './types'

const NOTE = 'AI flag, not a diagnosis (stub model)'
const ECGS: Record<string, { label: string; prob: number }> = {
  'ecg-demo-1': { label: 'Demo ECG 1', prob: 0.86 },
  'ecg-demo-2': { label: 'Demo ECG 2', prob: 0.08 },
  'ecg-demo-3': { label: 'Demo ECG 3', prob: 0.61 },
}
const XRAYS: Record<string, { label: string; findings: Record<string, number> }> = {
  'xr-demo-1': { label: 'Demo X-ray 1', findings: { Pneumonia: 0.78, Effusion: 0.12, Edema: 0.05, Cardiomegaly: 0.3, Pneumothorax: 0.02 } },
  'xr-demo-2': { label: 'Demo X-ray 2', findings: { Pneumonia: 0.06, Effusion: 0.04, Edema: 0.03, Cardiomegaly: 0.11, Pneumothorax: 0.01 } },
  'xr-demo-3': { label: 'Demo X-ray 3', findings: { Pneumonia: 0.14, Effusion: 0.66, Edema: 0.21, Cardiomegaly: 0.58, Pneumothorax: 0.02 } },
}
const flagEcg = (id: string): EcgResult => {
  const p = ECGS[id]?.prob ?? 0.5
  return { abnormal_prob: p, abnormal: p >= 0.5, threshold: 0.5, model: 'stub', note: NOTE }
}
const flagXray = (id: string): XrayResult => {
  const findings = XRAYS[id]?.findings ?? {}
  const thresholds = Object.fromEntries(Object.keys(findings).map(k => [k, 0.5]))
  return { findings, thresholds, flagged: Object.keys(findings).filter(k => findings[k] >= 0.5), model: 'stub', note: NOTE }
}

/** Stub for predict_admission(): a hand-written formula, NOT a trained model. */
function stubAdmission(p: PatientRecord): PatientView['scores']['admission'] {
  const latest = [...p.vitals].sort((a, b) => a.time.localeCompare(b.time)).pop()
  const n = news2Of(latest).value
  const cc: Record<string, number> = { chest_pain: 0.5, shortness_of_breath: 0.7, stroke_signs: 1.1, altered_mental_status: 0.8, fever_infection: 0.3, abdominal_pain: 0.1, trauma: -0.3, other: -0.2 }
  const parts: [string, number][] = [
    [`Age ${p.age}`, 0.035 * (p.age - 45)],
    [`NEWS2 ${n}`, 0.28 * n - 0.4],
    [`Complaint`, cc[p.complaint_category] ?? 0],
  ]
  const stage = p.esi ? 'triage' : 'ambulance'
  if (p.esi) parts.push([`ESI ${p.esi}`, (3 - p.esi) * 0.7])
  const L = -0.9 + parts.reduce((a, b) => a + b[1], 0)
  return {
    probability: 1 / (1 + Math.exp(-L)), stage, model: 'stub',
    top_reasons: parts.sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 3)
      .map(([label, w]) => ({ label, direction: w >= 0 ? 'up' as const : 'down' as const })),
  }
}

const KEY = 'relay-mock-v2'
let store: Record<string, PatientRecord> = {}
const save = () => { try { sessionStorage.setItem(KEY, JSON.stringify(store)) } catch { /* private mode */ } }
const ago = (min: number) => new Date(Date.now() - min * 60000).toISOString()
const view = (p: PatientRecord) => structuredClone(computeView(p, stubAdmission(p)))
const get = (id: string) => { const p = store[id]; if (!p) throw new Error('Patient not found.'); return p }

function seed() {
  const base = { demo: true, onset_time: '', reviews: [], bed_request: null, ecg: null, xray: null, injuries: [], treatments: [] }
  const v = (min: number, source: Vitals['source'], x: Partial<Vitals>): Vitals =>
    ({ time: ago(min), source, on_oxygen: false, avpu: 'A', gcs: 15, ...x })
  const list: PatientRecord[] = [
    { ...base, id: 'A', name: 'Demo Patient A (fictional)', age: 58, sex: 'M', complaint_category: 'chest_pain',
      complaint_text: 'Pressure in the centre of the chest for 40 minutes, sweating', onset_time: '40 min before call',
      history: 'High blood pressure', medications: 'Lisinopril', allergies: 'None known',
      treatments: [{ time: '14:02', what: 'Aspirin 324 mg by mouth' }],
      vitals: [v(16, 'ambulance', { heart_rate: 84, sbp: 132, dbp: 84, resp_rate: 16, spo2: 97, temp_c: 36.8, pain: 6, glucose_mg_dl: 118, rhythm: 'sinus' })],
      esi: null, arrival_time: ago(4), status: 'waiting' },
    { ...base, id: 'B', name: 'Demo Patient B (fictional)', age: 71, sex: 'F', complaint_category: 'fever_infection',
      complaint_text: 'Fever and confusion since this morning, burning on urination for 3 days', onset_time: 'This morning',
      history: 'Type 2 diabetes', medications: 'Metformin', allergies: 'Sulfa drugs',
      treatments: [{ time: '13:20', what: 'IV access, 250 mL saline' }],
      vitals: [
        v(75, 'ambulance', { heart_rate: 98, sbp: 118, dbp: 70, resp_rate: 20, spo2: 96, temp_c: 38.4, pain: 3, glucose_mg_dl: 162 }),
        v(52, 'triage', { heart_rate: 104, sbp: 114, dbp: 68, resp_rate: 20, spo2: 95, temp_c: 38.6, pain: 3 }),
        v(6, 'er', { heart_rate: 112, sbp: 108, dbp: 62, resp_rate: 22, spo2: 96, temp_c: 38.9, pain: 3 }),
      ],
      esi: 3, arrival_time: ago(58), status: 'waiting' },
    { ...base, id: 'C', name: 'Demo Patient C (fictional)', age: 82, sex: 'M', complaint_category: 'shortness_of_breath',
      complaint_text: 'Worse breathlessness over 2 days, cough with yellow sputum', onset_time: '2 days',
      history: 'COPD', medications: 'Tiotropium inhaler', allergies: 'Penicillin (rash)',
      treatments: [{ time: '12:48', what: 'Salbutamol nebuliser' }],
      vitals: [
        v(95, 'ambulance', { heart_rate: 96, sbp: 124, dbp: 72, resp_rate: 21, spo2: 94, temp_c: 38.3, pain: 2 }),
        v(30, 'er', { heart_rate: 94, sbp: 122, dbp: 70, resp_rate: 20, spo2: 95, temp_c: 38.4, pain: 2 }),
      ],
      esi: 2, arrival_time: ago(82), status: 'waiting',
      xray: { image_id: 'xr-demo-1', result: flagXray('xr-demo-1'), time: ago(40) } },
    { ...base, id: 'D', name: 'Demo Patient D (fictional)', age: 27, sex: 'F', complaint_category: 'trauma',
      complaint_text: 'Fell from a bicycle, right forearm deformity', onset_time: '30 min before call',
      history: 'None', medications: 'None', allergies: 'None known', injuries: ['suspected_fracture'],
      treatments: [{ time: '13:55', what: 'Splint to right forearm' }],
      vitals: [v(44, 'ambulance', { heart_rate: 92, sbp: 126, dbp: 80, resp_rate: 18, spo2: 99, temp_c: 36.9, pain: 7 })],
      esi: 4, arrival_time: ago(36), status: 'waiting' },
    { ...base, id: 'E', name: 'Demo Patient E (fictional)', age: 44, sex: 'M', complaint_category: 'abdominal_pain',
      complaint_text: 'Cramping lower abdominal pain since last night, no vomiting', onset_time: 'Last night',
      history: 'None', medications: 'None', allergies: 'None known',
      vitals: [v(150, 'ambulance', { heart_rate: 78, sbp: 128, dbp: 82, resp_rate: 16, spo2: 98, temp_c: 37.1, pain: 5 })],
      esi: 4, arrival_time: ago(138), status: 'waiting' },
    { ...base, id: 'F', name: 'Demo Patient F (fictional)', age: 66, sex: 'F', complaint_category: 'stroke_signs',
      complaint_text: 'Sudden slurred speech and right arm weakness', onset_time: '25 min before call',
      history: 'Type 1 diabetes', medications: 'Insulin', allergies: 'None known',
      vitals: [v(3, 'ambulance', { heart_rate: 88, sbp: 158, dbp: 94, resp_rate: 18, spo2: 97, temp_c: 36.6, avpu: 'V', gcs: 13, pain: 0, glucose_mg_dl: 62 })],
      esi: null, arrival_time: null, status: 'en_route' },
  ]
  store = Object.fromEntries(list.map(p => [p.id, p]))
  save()
}

try { store = JSON.parse(sessionStorage.getItem(KEY) || '{}') } catch { store = {} }
if (!Object.keys(store).length) seed()

const draft = (f: IntakeForm, id: string): PatientRecord => ({
  id, demo: true, name: f.name, age: f.age, sex: f.sex, complaint_category: f.complaint_category,
  complaint_text: f.complaint_text, onset_time: f.onset_time, history: f.history, medications: f.medications,
  allergies: f.allergies, injuries: f.injuries, treatments: f.treatments, vitals: f.vitals, esi: null,
  arrival_time: null, status: 'en_route', reviews: [], bed_request: null, xray: null,
  ecg: f.ecg_record_id ? { record_id: f.ecg_record_id, result: flagEcg(f.ecg_record_id), time: new Date().toISOString() } : null,
})
const edit = async (id: string, fn: (p: PatientRecord) => void) => { const p = get(id); fn(p); save(); return view(p) }
const nowIso = () => new Date().toISOString()

export const mockApi: Api = {
  source: { label: 'Mock data · stub models', mock: true },
  can: { repeatVitals: true, triage: true, review: true, ambulanceEcg: true, avpu: true, glucose: true },
  async options() {
    return {
      complaints: COMPLAINTS, injuries: INJURIES, scoreName: 'Bed priority',
      beds: Object.entries(BED_LABEL).map(([id, label]) => ({ id, label })),
      injuryNote: 'Draft points — clinician review needed',
    }
  },
  async board() {
    return Object.values(store).map(view).sort((a, b) => b.scores.queue_rank_score - a.scores.queue_rank_score)
  },
  async patient(id) { return view(get(id)) },
  async preview(f) { return view(draft(f, 'preview')) },
  async create(f) {
    const id = 'N' + Math.random().toString(36).slice(2, 6).toUpperCase()
    store[id] = draft(f, id); save(); return view(store[id])
  },
  arrive: id => edit(id, p => { p.arrival_time = nowIso(); p.status = 'waiting' }),
  addVitals: (id, v) => edit(id, p => { p.vitals.push(v) }),
  triage: (id, esi, v) => edit(id, p => { p.esi = esi; p.vitals.push({ ...v, source: 'triage' }) }),
  ecg: (id, rid) => edit(id, p => { p.ecg = { record_id: rid, result: flagEcg(rid), time: nowIso() }; p.reviews = p.reviews.filter(r => r.type !== 'ecg') }),
  xray: (id, iid) => edit(id, p => { p.xray = { image_id: iid, result: flagXray(iid), time: nowIso() }; p.reviews = p.reviews.filter(r => r.type !== 'xray') }),
  review: (id, type, normal, by) => edit(id, p => { p.reviews.push({ type, normal, by, time: nowIso() }) }),
  bedRequest: (id, bed_type, by) => edit(id, p => { p.bed_request = { bed_type, confirmed_by: by, time: nowIso() }; p.status = 'bed_requested' }),
  async rules() { return RULES_TEXT },
  async metrics() {
    const none = 'Not measured: this is a stub'
    return [
      { name: 'Needs a bed', dataset: 'Yale ED admissions', result: none, note: 'Hand-written formula standing in for the trained model.' },
      { name: 'ECG flag', dataset: 'PTB-XL', result: none, note: 'Fixed outputs for three demo ECGs.' },
      { name: 'Chest X-ray flag', dataset: 'NIH ChestX-ray14', result: none, note: 'Fixed outputs for three demo X-rays.' },
    ]
  },
  async assets(): Promise<DemoAssets> {
    return {
      ecgs: Object.entries(ECGS).map(([id, e]) => ({ id, label: e.label })),
      xrays: Object.entries(XRAYS).map(([id, x]) => ({ id, label: x.label })),
    }
  },
  async reset() { seed() },
}
