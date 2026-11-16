// The Relay Triage backend, ported to run in the browser so the app can be hosted as a static site.
// A line-for-line port of prototype/app/scoring.py and the endpoints of prototype/app/server.py.
// Every weight comes from src/data/relay.json, which is generated from the Python code and model
// outputs; nothing is retyped here. ECG and X-ray use the trained models' stored outputs.
// Checked against the Python backend by scripts/check-engine.ts.

type Parts = [string, number][]
type Probs = Record<string, number>
/* eslint-disable @typescript-eslint/no-explicit-any */
export interface RelayData {
  A: { intercept: number; co: Record<string, number> }; B: { intercept: number; co: Record<string, number> }
  bins: Record<string, [string, number, number][]>; label: Record<string, string>
  complaints: { id: string; label: string }[]; rhythms: { id: string; label: string }[]
  overlay: { rhythm: Record<string, number>; injury: Record<string, number> }
  ecg_w: Probs; ecg_norm_w: number; cxr_w: Probs; cxr_norm_w: number; max_drop: number; cxr_allow_down: boolean
  beds: string[]; samples: { ecg: any[]; cxr: any[] }; pre: { ecg: Record<string, Probs>; cxr: Record<string, Probs> }
  lead2: Record<string, number[]>; examples: any[]; metrics: Record<string, number>
}
export interface Store { getItem(k: string): string | null; setItem(k: string, v: string): void }

const sigmoid = (x: number) => 1 / (1 + Math.exp(-x))
export const toScore = (L: number) => 1 + Math.round(99 * sigmoid(L))

export function createEngine(D: RelayData, store?: Store) {
  const pretty = (c: string | null) => (c ? D.complaints.find(x => x.id === c)?.label ?? c.slice(3) : 'Unknown')
  const rhythmLabel = (r: string) => D.rhythms.find(x => x.id === r)?.label ?? r

  // ---------- scoring.py ----------
  function news2(v: any): [number, Record<string, number>] {
    const { rr, spo2: sp, sbp, hr } = v, gcs = v.gcs ?? 15, t = (v.temp_f - 32) * 5 / 9
    const p = {
      RR: rr <= 8 ? 3 : rr <= 11 ? 1 : rr <= 20 ? 0 : rr <= 24 ? 2 : 3,
      SpO2: sp <= 91 ? 3 : sp <= 93 ? 2 : sp <= 95 ? 1 : 0,
      O2: v.o2 ? 2 : 0,
      SBP: sbp <= 90 ? 3 : sbp <= 100 ? 2 : sbp <= 110 ? 1 : sbp <= 219 ? 0 : 3,
      HR: hr <= 40 ? 3 : hr <= 50 ? 1 : hr <= 90 ? 0 : hr <= 110 ? 1 : hr <= 130 ? 2 : 3,
      GCS: gcs >= 15 ? 0 : 3,
      Temp: t <= 35.0 ? 3 : t <= 36.0 ? 1 : t <= 38.0 ? 0 : t <= 39.0 ? 1 : 2,
    }
    return [Object.values(p).reduce((a, b) => a + b, 0), p]
  }
  const news2Floor = (total: number, parts: Record<string, number>) =>
    total >= 7 ? 80 : total >= 5 ? 60 : Math.max(...Object.values(parts)) === 3 ? 45 : 0

  function modelLogit(v: any, complaint: string | null): [number, Parts, 'A' | 'B'] {
    const m = complaint !== null ? D.B : D.A, co = m.co
    let L = m.intercept
    const parts: Parts = [['Intercept', m.intercept]]
    for (const [name, bins] of Object.entries(D.bins))
      for (const [lab, lo, hi] of bins)
        if (lo <= v[name] && v[name] <= hi) { L += co[`${name} ${lab}`]; parts.push([`${D.label[name]} ${lab}`, co[`${name} ${lab}`]]) }
    if (v.o2) { L += co.supplemental_o2; parts.push(['Supplemental O2', co.supplemental_o2]) }
    if (v.male) { L += co.male; parts.push(['Male', co.male]) }
    if (complaint) {
      const k = `complaint: ${complaint.slice(3)}`
      if (k in co) { L += co[k]; parts.push([`Complaint: ${pretty(complaint)}`, co[k]]) }
    }
    return [L, parts, complaint !== null ? 'B' : 'A']
  }

  function overlay(v: any): [number, Parts] {
    const parts: Parts = [], gcs = v.gcs ?? 15
    const g = gcs <= 8 ? 2.0 : gcs <= 12 ? 1.0 : gcs <= 14 ? 0.5 : 0.0
    if (g) parts.push([`GCS ${v.gcs}`, g])
    const r = D.overlay.rhythm[v.rhythm ?? 'sinus'] ?? 0
    if (r) parts.push([`Rhythm: ${rhythmLabel(v.rhythm)}`, r])
    for (const inj of v.injuries ?? []) parts.push([`Injury: ${inj.replace(/_/g, ' ')}`, D.overlay.injury[inj]])
    if ((v.pain ?? 0) >= 8) parts.push([`Pain ${v.pain}/10`, 0.3])
    return [parts.reduce((a, p) => a + p[1], 0), parts]
  }

  function provisionalBed(n: number, complaint: string | null): [string, string] {
    if (n >= 7) return ['ICU', 'NEWS2 >= 7']
    if (complaint === 'cc_chestpain' || complaint === 'cc_syncope') return ['Telemetry', `Complaint: ${pretty(complaint)}`]
    if ((complaint === 'cc_suicidal' || complaint === 'cc_psychiatricevaluation') && n < 5) return ['Psychiatric', `Complaint: ${pretty(complaint)}, NEWS2 < 5`]
    return ['General ward', 'No specific rule matched']
  }

  function stage1(d: any) {
    const v = { age: d.age, male: d.sex === 'M', hr: d.hr, sbp: d.sbp, dbp: d.dbp, rr: d.rr, spo2: d.spo2, temp_f: d.temp_f, o2: d.o2, gcs: d.gcs, pain: d.pain, rhythm: d.rhythm, injuries: d.injuries }
    const [Lm, mparts, which] = modelLogit(v, d.complaint), [Lo, oparts] = overlay(v), [n, nparts] = news2(v)
    const fl = news2Floor(n, nparts), L1 = Lm + Lo, raw = toScore(L1), [bed, why] = provisionalBed(n, d.complaint)
    return { model: which, L_model: Lm, L1, score_raw: raw, news2: n, news2_parts: nparts, floor: fl, score: Math.max(raw, fl),
      model_parts: mparts, overlay_parts: oparts, p_admit_model: sigmoid(Lm), bed, bed_reason: why }
  }

  function ecgDelta(pc: Probs) {
    const d = Object.keys(D.ecg_w).reduce((a, c) => a + D.ecg_w[c] * pc[c], 0) - D.ecg_norm_w * pc.NORM
    const top = Math.max(...Object.values(pc)), unsure = top >= 0.3 && top <= 0.7
    if (d < 0 && unsure) return { delta_raw: d, delta: 0, note: 'Model unsure: no downward move' }
    return { delta_raw: d, delta: Math.max(d, -D.max_drop), note: d < -D.max_drop ? 'Capped at -0.5' : '' }
  }
  function cxrDelta(pc: Probs) {
    const top = Math.max(...Object.values(pc)), pNorm = 1 - top
    const d = Object.keys(D.cxr_w).reduce((a, c) => a + D.cxr_w[c] * pc[c], 0) - D.cxr_norm_w * pNorm
    if (d < 0 && !D.cxr_allow_down) return { delta_raw: d, delta: 0, note: 'X-ray model may only raise scores (proof-of-concept limit)', p_normal: pNorm }
    if (d < 0 && top >= 0.3 && top <= 0.7) return { delta_raw: d, delta: 0, note: 'Model unsure: no downward move', p_normal: pNorm }
    return { delta_raw: d, delta: Math.max(d, -D.max_drop), note: d < -D.max_drop ? 'Capped at -0.5' : '', p_normal: pNorm }
  }
  function bedAfterEcg(current: string, pc: Probs): [string, string] {
    if (current === 'ICU') return ['ICU', 'Stays ICU']
    if (pc.MI >= 0.5) return ['CCU', `ECG p(MI) = ${pc.MI.toFixed(2)}`]
    if (current === 'CCU') return [current, 'No change']
    if (pc.STTC >= 0.5 || pc.CD >= 0.5) return ['Telemetry', `ECG p(ST/T) = ${pc.STTC.toFixed(2)}, p(CD) = ${pc.CD.toFixed(2)}`]
    return [current, 'No change']
  }
  const priority = (L: number, minutes: number) => L + 0.01 * minutes

  // ---------- server.py ----------
  const KEY = 'relay-browser-v1'
  let PAT: Record<string, any> = {}
  const save = () => { try { store?.setItem(KEY, JSON.stringify(PAT)) } catch { /* storage unavailable */ } }
  const now = () => Date.now() / 1000
  const mins = (t: number | null) => (t ? (now() - t) / 60 : 0)
  const fail = (msg: string): never => { throw new Error(msg) }
  const get = (id: string) => PAT[id] ?? fail('Patient not found.')
  const log = (p: any, kind: string, text: string, dL = 0) => p.events.push({ t: now(), kind, text, dL, score: p.score, L: p.L })
  const ecgOverride = (p: any) => p.intake.complaint === 'cc_chestpain' || ['stemi', 'vt', 'vf'].includes(p.intake.rhythm)

  function view(p: any) {
    const queues: any = {}
    for (const svc of ['ecg', 'xray']) if (p.queue[svc])
      queues[svc] = { since: p.queue[svc], minutes: mins(p.queue[svc]), priority: priority(p.L, mins(p.queue[svc])), override: svc === 'ecg' && ecgOverride(p) }
    const { queue: _q, bed, ...rest } = p
    return { ...rest, queues, bed: { ...bed, minutes: mins(bed.since), priority: priority(p.L, mins(bed.since)) },
      minutes_since_handoff: p.arrived_at ? mins(p.arrived_at) : null }
  }

  const DEFAULTS = { name: '', sex: 'F', dob: '', complaint: null, complaint_detail: '', onset: '', mechanism: '', history: '', medications: '',
    allergies: '', treatments: '', o2: false, gcs: 15, pain: 0, rhythm: 'sinus', injuries: [], order_ecg: true, order_xray: true, minutes_ago: 0 }
  function intake(body: any) {
    const d = { ...DEFAULTS, ...body }
    for (const k of ['age', 'hr', 'sbp', 'dbp', 'rr', 'spo2', 'temp_f']) if (typeof d[k] !== 'number' || Number.isNaN(d[k])) fail('Some vital signs are missing. Pulse, blood pressure, breathing rate, SpO2 and temperature are needed.')
    if (d.age < 18 || d.age > 110 || d.gcs < 3 || d.gcs > 15 || d.pain < 0 || d.pain > 10) fail('Some values are out of range. Check age (18–110), GCS (3–15) and pain (0–10).')
    return d
  }
  function create(body: any) {
    const d = intake(body), id = Math.random().toString(16).slice(2, 8), r = stage1(d), t0 = now() - d.minutes_ago * 60
    delete d.minutes_ago
    const p = { id, intake: d, status: 'incoming', created_at: t0, arrived_at: null, stage1: r, L: r.L1, floor: r.floor, score: r.score, ecg: null, xray: null,
      events: [] as any[], queue: {} as any, bed: { type: r.bed, status: 'provisional', reason: r.bed_reason, since: t0 } }
    PAT[id] = p
    log(p, 'ambulance', `Ambulance score ${r.score} (Model ${r.model}${r.floor > r.score_raw ? `, NEWS2 floor ${r.floor} applied` : ''}). Provisional bed: ${r.bed}.`)
    return p
  }
  function arrive(p: any, minutesAgo = 0) {
    if (p.status !== 'incoming') fail('Patient has already arrived.')
    const t = now() - minutesAgo * 60
    p.status = 'in ER'; p.arrived_at = t
    if (p.intake.order_ecg) p.queue.ecg = t
    if (p.intake.order_xray) p.queue.xray = t
    log(p, 'handoff', `Handoff 1: ambulance crew to ER. Joined ${Object.keys(p.queue).map(k => k.toUpperCase()).join(', ') || 'no'} queue(s).`)
  }
  const signed = (x: number) => `${x >= 0 ? '+' : ''}${x.toFixed(2)}`
  function applyEcg(p: any, sid: string) {
    const pc = D.pre.ecg[sid] ?? fail('Unknown ECG sample.'), d = ecgDelta(pc)
    p.L += d.delta; p.score = Math.max(toScore(p.L), p.floor)
    const old = p.bed.type, [nb, why] = bedAfterEcg(old, pc)
    p.ecg = { source: sid, probs: pc, ...d }; delete p.queue.ecg
    log(p, 'ecg', `ECG read. Change ${signed(d.delta)} log-odds${d.note ? ` (${d.note})` : ''}. Score now ${p.score}.`, d.delta)
    if (nb !== old) { Object.assign(p.bed, { type: nb, status: 'provisional', reason: why }); log(p, 'bed', `Bed waitlist changed: ${old} to ${nb} (${why}). Waiting time kept.`) }
  }
  function applyCxr(p: any, sid: string) {
    const pc = D.pre.cxr[sid] ?? fail('Unknown X-ray sample.'), d = cxrDelta(pc)
    p.L += d.delta; p.score = Math.max(toScore(p.L), p.floor)
    p.xray = { source: sid, probs: pc, ...d }; delete p.queue.xray
    log(p, 'xray', `Chest X-ray read. Change ${signed(d.delta)} log-odds${d.note ? ` (${d.note})` : ''}. Score now ${p.score}.`, d.delta)
  }
  function reset() {
    PAT = {}
    for (const ex of D.examples) {
      const { arrive: arr, ecg: _e, ...e } = ex
      const p = create(e)
      if (arr !== undefined && arr !== null) arrive(p, arr)
    }
    save()
  }
  try { PAT = JSON.parse(store?.getItem(KEY) || '{}') } catch { PAT = {} }
  if (!Object.keys(PAT).length) reset()

  /** Same paths and JSON as the Python server. */
  async function call(path: string, body?: any): Promise<any> {
    const m = (re: RegExp) => path.match(re)
    let x: RegExpMatchArray | null
    if (path === '/api/meta') return { complaints: D.complaints, rhythms: D.rhythms, injuries: Object.keys(D.overlay.injury), beds: D.beds, samples: D.samples,
      models_loaded: { ecg: false, xray: false }, precomputed: { ecg: true, xray: true }, metrics: D.metrics }
    if (path === '/api/preview') return stage1(intake(body))
    if (path === '/api/board') return { patients: Object.values(PAT).map(view).sort((a, b) => b.score - a.score) }
    if (path === '/api/reset') { reset(); return {} }
    if (path === '/api/patients') { const p = create(body); save(); return view(p) }
    if ((x = m(/^\/api\/samples\/ecg\/(.+)$/))) return { data: [[], D.lead2[x[1]] ?? fail('Unknown ECG sample.')] }
    if ((x = m(/^\/api\/patients\/([^/]+)$/))) return view(get(x[1]))
    if ((x = m(/^\/api\/patients\/([^/]+)\/(arrive|ecg|xray|bed\/confirm)$/))) {
      const p = get(x[1])
      if (x[2] === 'arrive') arrive(p)
      else if (x[2] === 'ecg') applyEcg(p, body.sample_id)
      else if (x[2] === 'xray') applyCxr(p, body.sample_id)
      else {
        if (!D.beds.includes(body.type)) fail('Unknown bed type.')
        const old = p.bed.type
        Object.assign(p.bed, { type: body.type, status: 'confirmed', reason: 'Confirmed by ER clinician' })
        log(p, 'bed', `ER clinician confirmed ${body.type} bed${old !== body.type ? ` (changed from ${old})` : ''}.`)
      }
      save(); return view(p)
    }
    return fail(`No such endpoint: ${path}`)
  }
  return { call, stage1, ecgDelta, cxrDelta, bedAfterEcg }
}
