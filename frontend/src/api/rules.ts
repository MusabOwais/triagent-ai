// Clinical rules from docs/CONTRACT.md (A5), as pure functions.
// The mock backend uses them; the real backend is the source of truth once wired.
import type {
  Alert, BedType, Complaint, FindingItem, Injury, News2, PatientRecord, PatientView, Vitals,
} from './types'

export const COMPLAINTS: { id: Complaint; label: string }[] = [
  { id: 'chest_pain', label: 'Chest pain' },
  { id: 'shortness_of_breath', label: 'Shortness of breath' },
  { id: 'stroke_signs', label: 'Stroke signs' },
  { id: 'abdominal_pain', label: 'Abdominal pain' },
  { id: 'trauma', label: 'Trauma / injury' },
  { id: 'altered_mental_status', label: 'Altered mental status' },
  { id: 'fever_infection', label: 'Fever / infection' },
  { id: 'other', label: 'Other' },
]
export const complaintLabel = (c: Complaint) => COMPLAINTS.find(x => x.id === c)?.label ?? c

/** Draft points, awaiting clinician review. */
export const INJURIES: { id: Injury; label: string; points: number }[] = [
  { id: 'minor_wound', label: 'Minor wound', points: 2 },
  { id: 'suspected_fracture', label: 'Suspected fracture', points: 5 },
  { id: 'open_fracture', label: 'Open fracture', points: 10 },
  { id: 'minor_burn', label: 'Minor burn', points: 5 },
  { id: 'major_burn', label: 'Major burn', points: 15 },
  { id: 'heavy_bleeding', label: 'Heavy bleeding', points: 15 },
  { id: 'frostbite', label: 'Frostbite', points: 5 },
]

export const BED_LABEL: Record<BedType, string> = {
  icu_review: 'ICU review',
  telemetry: 'Telemetry (heart-monitored)',
  isolation: 'Possible isolation',
  floor: 'Regular floor',
}

export const cToF = (c: number) => Math.round((c * 9 / 5 + 32) * 10) / 10
export const fToC = (f: number) => Math.round(((f - 32) * 5 / 9) * 10) / 10

const has = (x: unknown): x is number => typeof x === 'number' && !Number.isNaN(x)

/** NEWS2, SpO2 scale 1 only. Returns per-parameter points; null means not recorded. */
export function news2Of(v: Vitals | undefined): Omit<News2, 'trend' | 'previous'> {
  const parts: Record<string, number | null> = {
    'Breathing rate': null, 'SpO2': null, 'Air or oxygen': null, 'Systolic BP': null,
    'Pulse': null, 'Consciousness': null, 'Temperature': null,
  }
  if (v) {
    const { resp_rate: rr, spo2, sbp, heart_rate: hr, temp_c: t } = v
    if (has(rr)) parts['Breathing rate'] = rr <= 8 ? 3 : rr <= 11 ? 1 : rr <= 20 ? 0 : rr <= 24 ? 2 : 3
    if (has(spo2)) parts['SpO2'] = spo2 <= 91 ? 3 : spo2 <= 93 ? 2 : spo2 <= 95 ? 1 : 0
    if (typeof v.on_oxygen === 'boolean') parts['Air or oxygen'] = v.on_oxygen ? 2 : 0
    if (has(sbp)) parts['Systolic BP'] = sbp <= 90 ? 3 : sbp <= 100 ? 2 : sbp <= 110 ? 1 : sbp <= 219 ? 0 : 3
    if (has(hr)) parts['Pulse'] = hr <= 40 ? 3 : hr <= 50 ? 1 : hr <= 90 ? 0 : hr <= 110 ? 1 : hr <= 130 ? 2 : 3
    if (v.avpu) parts['Consciousness'] = v.avpu === 'A' ? 0 : 3
    else if (has(v.gcs)) parts['Consciousness'] = v.gcs >= 15 ? 0 : 3
    if (has(t)) parts['Temperature'] = t <= 35 ? 3 : t <= 36 ? 1 : t <= 38 ? 0 : t <= 39 ? 1 : 2
  }
  const vals = Object.values(parts).filter((x): x is number => x !== null)
  const value = vals.reduce((a, b) => a + b, 0)
  return {
    value, parts, present: vals.length, complete: vals.length === 7,
    band: value >= 7 ? 'high' : value >= 5 ? 'medium' : 'low',
  }
}

const bandRank = { low: 0, medium: 1, high: 2 } as const
const sorted = (vs: Vitals[]) => [...vs].sort((a, b) => a.time.localeCompare(b.time))
const reviewOf = (p: PatientRecord, type: 'ecg' | 'xray') =>
  [...p.reviews].reverse().find(r => r.type === type)

export function findingsOf(p: PatientRecord): { points: number; items: FindingItem[] } {
  const items: FindingItem[] = []
  if (p.ecg?.result.abnormal) {
    const r = reviewOf(p, 'ecg')
    if (r?.normal) items.push({ source: 'ecg', label: `ECG flag cleared: reviewed normal by ${r.by}`, points: 0 })
    else items.push({ source: 'ecg', label: r ? `Abnormal ECG (confirmed by ${r.by})` : 'Abnormal ECG (AI, unreviewed)', points: 10 })
  }
  if (p.xray && p.xray.result.flagged.length) {
    const r = reviewOf(p, 'xray'), what = p.xray.result.flagged.join(', ')
    if (r?.normal) items.push({ source: 'xray', label: `X-ray flag cleared: reviewed normal by ${r.by}`, points: 0 })
    else items.push({ source: 'xray', label: r ? `X-ray: ${what} (confirmed by ${r.by})` : `X-ray: ${what} (AI, unreviewed)`, points: 10 })
  }
  for (const i of p.injuries) {
    const def = INJURIES.find(x => x.id === i)
    if (def) items.push({ source: 'injury', label: `${def.label} (draft points)`, points: def.points })
  }
  return { points: items.reduce((a, b) => a + b.points, 0), items }
}

const fmtTime = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
const nr = (x: unknown, unit = '') => (x === undefined || x === null || x === '' ? 'not recorded' : `${x}${unit}`)

function vitalsLine(v: Vitals | undefined) {
  if (!v) return 'not recorded'
  return [
    `HR ${nr(v.heart_rate)}`, `BP ${has(v.sbp) ? `${v.sbp}/${nr(v.dbp)}` : 'not recorded'}`, `RR ${nr(v.resp_rate)}`,
    `SpO2 ${nr(v.spo2, '%')} ${v.on_oxygen === undefined ? '' : v.on_oxygen ? 'on oxygen' : 'on air'}`.trim(),
    `Temp ${has(v.temp_c) ? `${v.temp_c} °C (${cToF(v.temp_c)} °F)` : 'not recorded'}`,
    `${v.avpu ? `AVPU ${v.avpu}` : `GCS ${nr(v.gcs)}`}`, `Pain ${nr(v.pain, '/10')}`,
    `Glucose ${nr(v.glucose_mg_dl, ' mg/dL')}`,
  ].join(' · ') + ` (${fmtTime(v.time)}, ${v.source})`
}

/** MIST and SBAR text, built from the record only. Missing fields say "not recorded". */
export function buildHandoff(p: PatientRecord, x: {
  complaint: string; injuries: string[]; bed: string; news2: News2; scoreLine: string; todo: string[]
}): { mist: string; sbar: string } {
  const vs = sorted(p.vitals), latest = vs[vs.length - 1]
  const amb = [...vs].reverse().find(v => v.source === 'ambulance')
  const tx = p.treatments.map(t => t.time ? `${t.what} (${t.time})` : t.what).join('; ') || 'none recorded'
  const n2 = (n: { value: number; complete: boolean; present: number }) => n.complete ? `${n.value}` : `incomplete (${n.present}/7)`
  const rev = (type: 'ecg' | 'xray', flagged: boolean) => {
    const r = reviewOf(p, type)
    return r ? `, reviewed by ${r.by} as ${r.normal ? 'normal' : 'abnormal'}` : flagged ? ', not yet reviewed by a clinician' : ''
  }
  const flags = [
    p.ecg ? `ECG: ${p.ecg.result.abnormal ? 'AI flag abnormal' : 'no AI flag'}${rev('ecg', p.ecg.result.abnormal)}` : 'ECG: not recorded',
    p.xray ? `Chest X-ray: ${p.xray.result.flagged.length ? `AI flag ${p.xray.result.flagged.join(', ')}` : 'no AI flag'}${rev('xray', p.xray.result.flagged.length > 0)}` : 'Chest X-ray: not recorded',
  ]
  const mist = [
    `M — ${x.complaint}: ${p.complaint_text || 'details not recorded'}. Onset: ${p.onset_time || 'not recorded'}.`,
    `I — Injuries: ${x.injuries.join(', ') || 'none recorded'}.`,
    `S — ${vitalsLine(amb)}. NEWS2 ${n2(news2Of(amb))}.`,
    `T — ${tx}.`,
  ].join('\n')
  const sbar = [
    `S — ${p.age}-year-old ${p.sex === 'M' ? 'male' : 'female'}, ${x.complaint.toLowerCase()}: ${p.complaint_text || 'details not recorded'}. Suggested bed: ${x.bed}.`,
    `B — History: ${p.history || 'not recorded'}. Medications: ${p.medications || 'not recorded'}. Allergies: ${p.allergies || 'not recorded'}. ESI: ${p.esi ?? 'not recorded'}.`,
    `A — ${vitalsLine(latest)}. NEWS2 ${n2(x.news2)}${x.news2.trend ? `, trend ${x.news2.trend}` : ''}. ${x.scoreLine}. ${flags.join('. ')}. AI flags are not diagnoses.`,
    `R — To check: ${x.todo.join('; ') || 'nothing pending'}.`,
  ].join('\n')
  return { mist, sbar }
}

/** Builds everything the screens show from one record. `admission` comes from the model (or a stub). */
export function computeView(
  p: PatientRecord,
  admission: PatientView['scores']['admission'],
  now = Date.now(),
): PatientView {
  const vs = sorted(p.vitals)
  const latest = vs[vs.length - 1]
  const cur = news2Of(latest)
  const complete = vs.map(v => ({ v, n: news2Of(v) })).filter(x => x.n.complete)
  const last = complete[complete.length - 1], prev = complete[complete.length - 2]
  const latestIsComplete = !!last && last.v === latest
  const trend = latestIsComplete && prev
    ? (last.n.value > prev.n.value ? 'up' : last.n.value < prev.n.value ? 'down' : 'flat') : null
  const news2: News2 = { ...cur, trend, previous: latestIsComplete && prev ? prev.n.value : null }

  const findings = findingsOf(p)
  const A = Math.round(admission.probability * 100), B = news2.value * 5, C = findings.points
  const priority = Math.min(100, Math.round((A + B) / 2 + C))
  const wait = p.arrival_time ? Math.max(0, Math.floor((now - Date.parse(p.arrival_time)) / 60000)) : 0
  const queue_rank_score = priority + Math.floor(wait / 15)

  // Bed type: first match wins.
  const ecgCleared = reviewOf(p, 'ecg')?.normal, xrCleared = reviewOf(p, 'xray')?.normal
  let bed: { suggested: BedType; reason: string }
  if (news2.value >= 7 || (has(latest?.gcs) && latest!.gcs! <= 8))
    bed = { suggested: 'icu_review', reason: news2.value >= 7 ? `NEWS2 is ${news2.value} (7 or more)` : `GCS is ${latest!.gcs} (8 or below)` }
  else if (p.ecg?.result.abnormal && !ecgCleared)
    bed = { suggested: 'telemetry', reason: reviewOf(p, 'ecg') ? 'Abnormal ECG (clinician confirmed)' : 'Abnormal ECG (AI, unreviewed)' }
  else if (p.xray?.result.flagged.includes('Pneumonia') && !xrCleared && has(latest?.temp_c) && latest!.temp_c! >= 38.1)
    bed = { suggested: 'isolation', reason: `X-ray flags pneumonia and temperature is ${latest!.temp_c} °C` }
  else bed = { suggested: 'floor', reason: 'No specific rule matched' }

  const alerts: Alert[] = []
  if (p.complaint_category === 'chest_pain' && p.arrival_time && !p.ecg) {
    const due = Date.parse(p.arrival_time) + 10 * 60000
    alerts.push({ kind: 'protocol', level: now > due ? 'critical' : 'warning', message: 'ECG due within 10 min of arrival', due_at: new Date(due).toISOString() })
  }
  if (p.complaint_category === 'stroke_signs') {
    alerts.push({ kind: 'protocol', level: 'critical', message: 'Stroke alert', due_at: null })
    if (has(latest?.glucose_mg_dl) && latest!.glucose_mg_dl! < 70)
      alerts.push({ kind: 'protocol', level: 'warning', message: `Low blood sugar can mimic stroke: glucose is ${latest!.glucose_mg_dl} mg/dL, check glucose`, due_at: null })
  }
  if (latestIsComplete && prev) {
    const rise = last.n.value - prev.n.value
    if (rise >= 2 || bandRank[last.n.band] > bandRank[prev.n.band])
      alerts.push({ kind: 'deterioration', level: last.n.band === 'high' ? 'critical' : 'warning', message: `Getting worse: NEWS2 rose ${prev.n.value} → ${last.n.value}`, due_at: null })
  }

  const pending: string[] = []
  if (p.status !== 'en_route' && p.esi === null) pending.push('ESI not yet assigned')
  if (!p.ecg) pending.push('ECG not yet recorded')
  else if (p.ecg.result.abnormal && !reviewOf(p, 'ecg')) pending.push('ECG flag awaiting clinician review')
  if (!p.xray) pending.push('Chest X-ray not yet recorded')
  else if (p.xray.result.flagged.length && !reviewOf(p, 'xray')) pending.push('X-ray flag awaiting clinician review')
  if (!news2.complete) pending.push(`NEWS2 incomplete (${news2.present}/7 vitals recorded)`)
  if (p.status !== 'en_route' && !p.bed_request) pending.push('Bed request not sent')

  const handoff = buildHandoff(p, {
    complaint: complaintLabel(p.complaint_category),
    injuries: p.injuries.map(i => INJURIES.find(x => x.id === i)?.label ?? i),
    bed: `${BED_LABEL[bed.suggested]} (${bed.reason})`, news2,
    scoreLine: `Chance of needing a bed ${A}% (model, ${admission.stage} stage)`,
    todo: [...alerts.map(a => a.message), ...pending],
  })

  return {
    patient: p,
    scores: { admission, news2, findings, parts: { A, B, C }, priority, wait_minutes: wait, queue_rank_score, wait_bonus: queue_rank_score - priority },
    bed_type: bed, alerts, pending, handoff,
  }
}

export const RULES_TEXT = `BED PRIORITY (0–100) = (A + B) / 2 + C, capped at 100
  A. Needs a bed: admission model probability × 100 (ambulance version until ESI is entered, then triage version)
  B. Sick right now: NEWS2 (0–20) × 5
  C. Findings: abnormal ECG +10 · X-ray finding +10 · visible injuries (draft points, clinician review needed):
     minor wound 2, suspected fracture 5, open fracture 10, minor burn 5, major burn 15, heavy bleeding 15, frostbite 5

RAISE-ONLY
  An AI result can add points and never subtracts. Only a clinician marking a finding "Reviewed — normal" removes its points.

BED QUEUE RANK = bed priority + 1 point per full 15 minutes waited since arrival

SUGGESTED BED TYPE (draft, first match wins)
  1. NEWS2 7 or more, or GCS 8 or below → ICU review
  2. Abnormal ECG (unreviewed or confirmed) → Telemetry (heart-monitored)
  3. X-ray flags pneumonia and temperature 38.1 °C or more → Possible isolation
  4. Otherwise → Regular floor
  The charge nurse confirms every bed request. The app never assigns a bed.

PROTOCOL ALERTS (not driven by the score)
  Chest pain → ECG due within 10 minutes of arrival
  Stroke signs → Stroke alert; glucose under 70 mg/dL → "low blood sugar can mimic stroke"

GETTING-WORSE ALERT
  Only when NEWS2 rises by 2 or more between two complete sets of vitals, or moves up a band (5–6 urgent, 7+ emergency).

NEWS2 BANDS: 0–4 low · 5–6 medium (urgent review) · 7+ high (emergency). SpO2 scale 1 only.

The three datasets come from different patients. They are combined by these written rules, not by one trained model.`
