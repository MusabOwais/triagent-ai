import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '../api'
import type { DemoAssets, PatientView, Strip } from '../api'
import { cToF, news2Of } from '../api/rules'
import {
  AlertRow, Btn, Chip, cx, draftHasValues, draftProblems, draftToVitals, emptyDraft, Field, fmtClock, fmtWait,
  Input, labelOf, Panel, Select, toast, Trend, useLive, useNow, useOptions, VitalsFields,
} from '../ui'
import type { VitalsDraft } from '../ui'

const STATUS = { en_route: 'In the ambulance', waiting: 'Waiting in ER', bed_requested: 'Bed requested', in_bed: 'In a bed' }
const bandText = { low: 'text-ok', medium: 'text-warn', high: 'text-crit' }

export default function Patient({ id }: { id: string }) {
  const { data: v, error, setData } = useLive<PatientView>(() => api.patient(id), id)
  const [assets, setAssets] = useState<DemoAssets | null>(null)
  const now = useNow()
  const { opts } = useOptions()
  const bedName = (id: string) => labelOf(opts?.beds, id)
  useEffect(() => { api.assets().then(setAssets).catch(() => {}) }, [])

  if (error && !v) return <p className="rounded-md bg-crit-bg px-4 py-3 font-semibold text-crit">{error} <a className="underline" href="#board">Back to the bed board</a></p>
  if (!v) return <div className="h-64 animate-pulse rounded-lg bg-line/50" aria-label="Loading patient" />

  const p = v.patient, s = v.scores
  const act = async (fn: () => Promise<PatientView>, done: string) => {
    try { setData(await fn()); toast(done) } catch (e) { toast(e instanceof Error ? e.message : 'That did not work. Try again.') }
  }

  return (
    <div className="flex flex-col gap-4">
      {v.alerts.length > 0 && <div className="flex flex-col gap-2" aria-label="Alerts">{v.alerts.map(a => <AlertRow key={a.message} a={a} now={now} />)}</div>}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <a href="#board" className="text-[14px] font-semibold text-action underline-offset-4 hover:underline">Bed board</a>
          <h1 className="mt-0.5 text-[26px] font-extrabold tracking-tight">{p.name}</h1>
          <p className="text-muted">{p.age} y · {p.sex === 'M' ? 'male' : 'female'} · {labelOf(opts?.complaints, p.complaint_category)} · {STATUS[p.status]}{p.arrival_time ? ` · arrived ${fmtWait(s.wait_minutes)} ago` : ''}{p.esi ? ` · ESI ${p.esi}` : ''}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {p.demo && <Chip tone="info">Fictional demo patient</Chip>}
          {p.status === 'en_route' && <Btn kind="primary" onClick={() => act(() => api.arrive(id), 'Arrival recorded. Handoff received from the ambulance crew.')}>Mark arrived</Btn>}
        </div>
      </div>

      {/* Score: the number and the three parts that make it, always together. */}
      {s.strip ? <StripView strip={s.strip} score={s.priority} /> : <section className="grid gap-px overflow-hidden rounded-lg border border-line bg-line md:grid-cols-[220px_repeat(3,minmax(0,1fr))]">
        <div className="bg-ink p-4 text-white sm:p-5">
          <div className="text-[14px] font-semibold opacity-80">Bed priority</div>
          <div className="num text-[64px] font-extrabold leading-none">{s.priority}</div>
          <div className="num mt-1 text-[14px] opacity-80">({s.parts.A} + {s.parts.B}) ÷ 2 + {s.parts.C}{s.priority === 100 ? ', capped' : ''}</div>
        </div>
        <Part letter="A" name="Needs a bed" value={`${s.parts.A}%`}>
          Admission model, {s.admission.stage} version.
          {s.admission.top_reasons.length > 0 && <> Main factors: {s.admission.top_reasons.map(r => `${r.label} (${r.direction === 'up' ? 'raises' : 'lowers'})`).join(', ')}.</>}
        </Part>
        <Part letter="B" name="Sick right now" value={<span className={bandText[s.news2.band]}>{s.news2.value}<span className="ml-1 text-[18px]"><Trend dir={s.news2.trend} /></span></span>} sub={`NEWS2 × 5 = ${s.parts.B}`}>
          {s.news2.complete ? <>NEWS2 out of 20{s.news2.previous !== null ? `, was ${s.news2.previous}` : ''}.</> : <>Incomplete: {s.news2.present} of 7 vitals recorded.</>}
          {' '}{Object.entries(s.news2.parts).filter(([, x]) => x).map(([k, x]) => `${k} +${x}`).join(', ') || 'No vital sign is scoring.'}
        </Part>
        <Part letter="C" name="Findings" value={`+${s.parts.C}`}>
          {s.findings.items.length === 0 ? 'No ECG, X-ray or injury findings.' : (
            <ul className="flex flex-col gap-0.5">{s.findings.items.map(i => <li key={i.label} className={cx(i.points === 0 && 'line-through decoration-muted')}><span className="num font-semibold">+{i.points}</span> {i.label}</li>)}</ul>
          )}
        </Part>
      </section>}

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border border-line bg-surface px-4 py-3">
        <span className="text-[14px] font-semibold text-muted">Suggested bed</span>
        <b className="text-[17px]">{bedName(v.bed_type.suggested)}</b>
        <span className="text-muted">{v.bed_type.reason}</span>
        {p.bed_request
          ? <Chip tone="ok">Requested: {bedName(p.bed_request.bed_type)}, confirmed by {p.bed_request.confirmed_by}</Chip>
          : <span className="ml-auto text-[14px] text-muted">A suggestion only. The charge nurse sends the request from the <a className="font-semibold text-action underline" href="#board">bed board</a>.</span>}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-4">
          <VitalsPanel v={v} onSave={(vit, esi) => act(() => esi ? api.triage(id, esi, vit) : api.addVitals(id, vit), esi ? 'Triage saved. Score updated.' : 'Vitals saved. Score updated.')} />
          <Handoff v={v} />
          {v.history && v.history.length > 0 && (
            <Panel title="Score history" aside="Every change, with its reason">
              <ol className="flex flex-col divide-y divide-line text-[15px]">{v.history.map((h, i) => (
                <li key={i} className="grid grid-cols-[76px_minmax(0,1fr)_auto] items-baseline gap-3 py-2"><span className="num whitespace-nowrap text-muted">{fmtClock(h.time)}</span><span>{h.text}</span><span className="num font-bold">{h.score}</span></li>))}</ol>
            </Panel>)}
          <Panel title="Record from the ambulance">
            <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1.5 text-[15px]">
              <Row k="Complaint" val={p.complaint_text} /><Row k="Onset" val={p.onset_time} />
              <Row k="History" val={p.history} /><Row k="Medications" val={p.medications} />
              <dt className="text-muted">Allergies</dt><dd className="font-bold">{p.allergies || 'Not recorded'}</dd>
              <Row k="Treatments" val={p.treatments.map(t => `${t.time} ${t.what}`).join('; ')} />
            </dl>
          </Panel>
        </div>

        <div className="flex min-w-0 flex-col gap-4">
          <Diag kind="ecg" v={v} assets={assets} disabled={p.status === 'en_route'}
            onRun={rid => act(() => api.ecg(id, rid), 'ECG recorded. Score updated.')}
            onReview={(normal, by) => act(() => api.review(id, 'ecg', normal, by), normal ? 'ECG marked normal. Its points were removed.' : 'ECG finding confirmed.')} />
          <Diag kind="xray" v={v} assets={assets} disabled={p.status === 'en_route'}
            onRun={iid => act(() => api.xray(id, iid), 'X-ray recorded. Score updated.')}
            onReview={(normal, by) => act(() => api.review(id, 'xray', normal, by), normal ? 'X-ray marked normal. Its points were removed.' : 'X-ray finding confirmed.')} />
          <Panel title="Still to do">
            {v.pending.length === 0 ? <p className="text-muted">Nothing pending.</p> : <ul className="flex list-disc flex-col gap-1 pl-5 text-[15px]">{v.pending.map(x => <li key={x}>{x}</li>)}</ul>}
          </Panel>
        </div>
      </div>
    </div>
  )
}

function Part({ letter, name, value, sub, children }: { letter: string; name: string; value: ReactNode; sub?: string; children: ReactNode }) {
  return (
    <div className="min-w-0 bg-surface p-4 sm:p-5">
      <div className="text-[14px] font-semibold text-muted"><span className="num mr-1.5 text-ink">{letter}</span>{name}</div>
      <div className="num mt-0.5 flex items-baseline gap-2 text-[34px] font-extrabold leading-tight">{value}{sub && <span className="text-[14px] font-semibold text-muted">{sub}</span>}</div>
      <div className="mt-1 text-[14px] text-muted">{children}</div>
    </div>
  )
}
const Row = ({ k, val }: { k: string; val: string }) => (<><dt className="text-muted">{k}</dt><dd>{val || <span className="text-muted">Not recorded</span>}</dd></>)

function VitalsPanel({ v, onSave }: { v: PatientView; onSave: (vit: ReturnType<typeof draftToVitals>, esi?: number) => void }) {
  const [mode, setMode] = useState<null | 'vitals' | 'triage'>(null)
  const [d, setD] = useState<VitalsDraft>(emptyDraft)
  const [esi, setEsi] = useState('3')
  const rows = [...v.patient.vitals].sort((a, b) => a.time.localeCompare(b.time))
  const arrived = v.patient.status !== 'en_route'
  const cell = (x: number | undefined, unit = '') => (x === undefined ? <span className="text-muted">–</span> : `${x}${unit}`)
  const save = () => {
    if (draftProblems(d).length) return toast('Fix the highlighted vitals first.')
    if (!draftHasValues(d)) return toast('Enter at least one vital sign.')
    onSave(draftToVitals(d, mode === 'triage' ? 'triage' : 'er'), mode === 'triage' ? +esi : undefined); setMode(null); setD(emptyDraft())
  }
  return (
    <Panel title="Vitals from ambulance to now" aside={`${rows.length} set${rows.length === 1 ? '' : 's'}`}>
      <div className="overflow-x-auto">
        <table className="num w-full min-w-[620px] whitespace-nowrap text-left text-[15px]">
          <thead className="text-[13px] text-muted"><tr>{['Time', 'Where', 'Pulse', 'BP', 'Breathing', 'SpO2', 'Temp', 'Alert', 'Pain', 'NEWS2'].map(h => <th key={h} className="border-b border-line py-1.5 pr-3 font-semibold">{h}</th>)}</tr></thead>
          <tbody>
            {rows.map((r, i) => { const n = news2Of(r); return (
              <tr key={i} className="border-b border-line last:border-0">
                <td className="py-2 pr-3 font-semibold">{fmtClock(r.time)}</td>
                <td className="pr-3"><Chip tone={r.source === 'ambulance' ? 'info' : 'neutral'}>{r.source === 'er' ? 'ER' : r.source === 'triage' ? 'Triage' : 'Ambulance'}</Chip></td>
                <td className="pr-3">{cell(r.heart_rate)}</td><td className="pr-3">{r.sbp === undefined ? cell(undefined) : `${r.sbp}/${r.dbp ?? '–'}`}</td>
                <td className="pr-3">{cell(r.resp_rate)}</td><td className="pr-3">{cell(r.spo2, '%')}{r.on_oxygen ? ' O₂' : ''}</td>
                <td className="pr-3">{r.temp_c === undefined ? cell(undefined) : `${cToF(r.temp_c)} °F`}</td><td className="pr-3">{r.avpu ?? (r.gcs !== undefined ? `GCS ${r.gcs}` : '–')}</td>
                <td className="pr-3">{cell(r.pain)}</td>
                <td className={cx('font-bold', n.complete && bandText[n.band])}>{n.complete ? n.value : `${n.present}/7`}</td>
              </tr>) })}
          </tbody>
        </table>
      </div>
      {mode === null ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {api.can.repeatVitals && <Btn disabled={!arrived} onClick={() => setMode('vitals')}>Add vitals</Btn>}
          {api.can.triage && <Btn disabled={!arrived} onClick={() => setMode('triage')}>{v.patient.esi ? 'Redo triage' : 'Enter triage (ESI + vitals)'}</Btn>}
          {!api.can.repeatVitals ? <span className="self-center text-[14px] text-muted">The backend keeps one set of vitals per patient for now, so there is no trend yet.</span>
            : !arrived && <span className="self-center text-[14px] text-muted">Available once the patient arrives.</span>}
        </div>
      ) : (
        <div className="mt-4 rounded-md bg-sunk p-3 sm:p-4">
          <h3 className="mb-3 font-bold">{mode === 'triage' ? 'Triage' : 'New set of vitals'}</h3>
          {mode === 'triage' && <div className="mb-3 max-w-[260px]"><Field label="ESI level" hint="1 is most urgent, 5 least.">
            <Select id="pt-esi" value={esi} onChange={e => setEsi(e.target.value)}>{[1, 2, 3, 4, 5].map(n => <option key={n}>{n}</option>)}</Select></Field></div>}
          <VitalsFields d={d} set={setD} idp="pt-v" />
          <div className="mt-4 flex gap-2"><Btn kind="primary" onClick={save}>Save</Btn><Btn onClick={() => setMode(null)}>Cancel</Btn></div>
        </div>
      )}
    </Panel>
  )
}

function Diag({ kind, v, assets, disabled, onRun, onReview }: {
  kind: 'ecg' | 'xray'; v: PatientView; assets: DemoAssets | null; disabled: boolean
  onRun: (id: string) => void; onReview: (normal: boolean, by: string) => void
}) {
  const p = v.patient, name = kind === 'ecg' ? '12-lead ECG' : 'Chest X-ray'
  const list = (kind === 'ecg' ? assets?.ecgs : assets?.xrays) ?? []
  const [pick, setPick] = useState(''); const [by, setBy] = useState(''); const [reviewing, setReviewing] = useState(false)
  const review = [...p.reviews].reverse().find(r => r.type === kind)
  const flagged = kind === 'ecg' ? !!p.ecg?.result.abnormal : !!p.xray?.result.flagged.length
  const done = kind === 'ecg' ? p.ecg : p.xray
  const res = kind === 'ecg' ? p.ecg?.result : p.xray?.result
  const off = assets?.unavailable?.[kind]
  const chosen = pick || list[0]?.id || ''
  const sampleId = kind === 'ecg' ? p.ecg?.record_id : p.xray?.image_id
  const sample = list.find(a => a.id === sampleId) as DemoAssets['xrays'][number] | undefined
  const thumbs = kind === 'xray' && (assets?.xrays ?? []).some(x => x.image_url)
  // ECG: per-class bars when the model reports them, otherwise one "abnormal" bar. X-ray: the top findings.
  const bars: [string, number, boolean][] = kind === 'ecg'
    ? (p.ecg?.result.classes ? Object.entries(p.ecg.result.classes).sort((x, y) => y[1] - x[1]).map(([k, x]) => [k, x, k !== 'Normal' && x >= 0.5])
      : p.ecg ? [['Abnormal', p.ecg.result.abnormal_prob, p.ecg.result.abnormal]] : [])
    : Object.entries(p.xray?.result.findings ?? {}).sort((x, y) => y[1] - x[1]).slice(0, 6).map(([k, x]) => [k, x, p.xray!.result.flagged.includes(k)])

  return (
    <Panel title={name} aside={done ? `Recorded ${fmtClock(done.time)}` : undefined}>
      {!done ? (
        <div className="flex flex-col gap-3">
          {off ? <p className="rounded-md bg-warn-bg px-3 py-2 text-[15px] font-semibold text-warn">{off}</p> : thumbs ? (
            <div>
              <div className="mb-1 text-[14px] font-semibold">Choose a held-out demo X-ray</div>
              <div className="grid grid-cols-4 gap-2">{(assets?.xrays ?? []).map(x => (
                <button key={x.id} type="button" disabled={disabled} aria-label={x.label} aria-pressed={chosen === x.id} onClick={() => setPick(x.id)}
                  className={cx('overflow-hidden rounded-md border-2 bg-ink disabled:opacity-50', chosen === x.id ? 'border-action' : 'border-transparent')}>
                  <img src={x.image_url} alt="" className="aspect-square w-full object-cover" /></button>))}</div>
            </div>
          ) : (
            <Field label={`Choose a demo ${kind === 'ecg' ? 'ECG recording' : 'X-ray image'}`} hint="Held-out demo sample the model has not seen, standing in for the real test.">
              <Select id={`pt-${kind}-pick`} value={chosen} onChange={e => setPick(e.target.value)} disabled={disabled}>{list.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}</Select>
            </Field>
          )}
          {kind === 'ecg' && !off && chosen && <EcgTrace id={chosen} />}
          {disabled && <p className="text-[14px] text-muted">Available once the patient arrives.</p>}
          <Btn kind="primary" disabled={disabled || !!off || !list.length} onClick={() => onRun(chosen)}>Record {kind === 'ecg' ? 'ECG' : 'X-ray'} and run the model</Btn>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <Chip tone={flagged ? (review?.normal ? 'neutral' : 'crit') : 'ok'}>{flagged ? (kind === 'ecg' ? 'AI flag: abnormal' : `AI flag: ${p.xray!.result.flagged.join(', ')}`) : 'No AI flag'}</Chip>
            {flagged && api.can.review && <Chip tone={review ? 'ok' : 'warn'}>{review ? `Reviewed by ${review.by}: ${review.normal ? 'normal' : 'abnormal'}` : 'Unreviewed'}</Chip>}
          </div>
          {kind === 'ecg' && sampleId && <EcgTrace id={sampleId} />}
          <div className={cx(sample?.image_url && 'grid grid-cols-[96px_minmax(0,1fr)] items-start gap-3')}>
            {sample?.image_url && <img src={sample.image_url} alt="Chest X-ray sample" className="aspect-square w-full rounded-md bg-ink object-cover" />}
            <div className="flex flex-col gap-1.5">{bars.map(([k, x, hot]) => <Bar key={k} label={k} p={x} hot={hot} />)}</div>
          </div>
          {res?.effect && <p className="num text-[15px] font-semibold">{res.effect}</p>}
          <p className="text-[14px] text-muted">AI flag, not a diagnosis. Model: {res?.model === 'stub' ? 'stub (fixed demo output, no measured accuracy)' : res?.model}. <a className="font-semibold text-action underline" href="#board">How it was measured is on the bed board</a>.</p>
          {sample?.truth && <p className="rounded-md bg-sunk px-3 py-2 text-[14px]">Demo transparency: the expert label for this held-out sample is <b>{sample.truth.join(', ')}</b>.</p>}
          {!flagged && api.can.review && <p className="text-[14px] text-muted">A clear AI result adds nothing and takes nothing off the score.</p>}
          {flagged && api.can.review && !review && !reviewing && (
            <div className="flex flex-wrap gap-2"><Btn onClick={() => setReviewing(true)}>Review this finding</Btn></div>
          )}
          {flagged && api.can.review && !review && reviewing && (
            <div className="rounded-md bg-sunk p-3">
              <Field label="Your name and role" hint="Only a clinician can take these points off the score.">
                <Input id={`pt-${kind}-by`} value={by} onChange={e => setBy(e.target.value)} placeholder="e.g. Dr. Lee, ER physician" />
              </Field>
              <div className="mt-3 flex flex-wrap gap-2">
                <Btn kind="primary" disabled={!by.trim()} onClick={() => onReview(true, by.trim())}>Reviewed — normal</Btn>
                <Btn disabled={!by.trim()} onClick={() => onReview(false, by.trim())}>Confirm abnormal</Btn>
                <Btn kind="quiet" onClick={() => setReviewing(false)}>Cancel</Btn>
              </div>
            </div>
          )}
        </div>
      )}
    </Panel>
  )
}

/** Lead II of the chosen ECG, drawn on a paper-style grid. Renders nothing if the backend has no traces. */
function EcgTrace({ id }: { id: string }) {
  const [lead, setLead] = useState<number[] | null>(null)
  useEffect(() => {
    let live = true; setLead(null)
    api.ecgTrace?.(id).then(d => live && setLead(d)).catch(() => {})
    return () => { live = false }
  }, [id])
  if (!api.ecgTrace) return null
  const W = 600, H = 120, pad = 10
  if (!lead) return <div className="h-[120px] animate-pulse rounded-md bg-sunk" aria-label="Loading ECG trace" />
  const lo = Math.min(...lead), hi = Math.max(...lead), span = hi - lo || 1
  const pts = lead.map((y, i) => `${(i / (lead.length - 1) * W).toFixed(1)},${(H - pad - (y - lo) / span * (H - 2 * pad)).toFixed(1)}`).join(' ')
  return (
    <figure className="m-0">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="ECG trace, lead II, 10 seconds" className="block w-full rounded-md border border-line bg-[#fff8f6]">
        {Array.from({ length: 51 }, (_, i) => <line key={i} x1={i * W / 50} x2={i * W / 50} y1="0" y2={H} stroke="#e9b9b2" strokeWidth={i % 5 ? 0.4 : 0.9} />)}
        {Array.from({ length: 7 }, (_, i) => <line key={`h${i}`} y1={i * H / 6} y2={i * H / 6} x1="0" x2={W} stroke="#e9b9b2" strokeWidth="0.4" />)}
        <polyline points={pts} fill="none" stroke="#12202c" strokeWidth="1.2" strokeLinejoin="round" />
      </svg>
      <figcaption className="mt-1 text-[13px] text-muted">Lead II · 10 seconds · held-out PTB-XL recording</figcaption>
    </figure>
  )
}

function StripView({ strip, score }: { strip: Strip; score: number }) {
  return (
    <section className="grid gap-px overflow-hidden rounded-lg border border-line bg-line md:grid-cols-[220px_repeat(3,minmax(0,1fr))]">
      <div className="bg-ink p-4 text-white sm:p-5">
        <div className="text-[14px] font-semibold opacity-80">{strip.title}</div>
        <div className="num text-[64px] font-extrabold leading-none">{score}</div>
        <div className="num mt-1 text-[14px] opacity-80">{strip.formula}</div>
      </div>
      {strip.cells.map(c => (
        <div key={c.name} className="min-w-0 bg-surface p-4 sm:p-5">
          <div className="text-[14px] font-semibold text-muted">{c.name}</div>
          <div className="num mt-0.5 flex items-baseline gap-2 text-[34px] font-extrabold leading-tight"><span className={c.tone && bandText[c.tone]}>{c.value}</span>{c.sub && <span className="text-[14px] font-semibold text-muted">{c.sub}</span>}</div>
          <ul className="num mt-1 flex flex-col gap-0.5 text-[14px]">{c.lines.map(l => <li key={l}>{l}</li>)}</ul>
          {c.note && <p className="mt-1 text-[13px] text-muted">{c.note}</p>}
        </div>))}
    </section>
  )
}

function Bar({ label, p, hot }: { label: string; p: number; hot: boolean }) {
  return (
    <div className="num grid grid-cols-[minmax(0,150px)_minmax(0,1fr)_44px] items-center gap-3 text-[15px]">
      <span>{label}</span>
      <span className="h-2.5 overflow-hidden rounded-full bg-sunk"><span className={cx('block h-full rounded-full', hot ? 'bg-crit' : 'bg-muted/50')} style={{ width: `${Math.round(p * 100)}%` }} /></span>
      <span className="text-right font-semibold">{Math.round(p * 100)}%</span>
    </div>
  )
}

function Handoff({ v }: { v: PatientView }) {
  const [tab, setTab] = useState<'mist' | 'sbar'>('sbar')
  const text = v.handoff[tab]
  const copy = async () => { try { await navigator.clipboard.writeText(text); toast('Handoff copied.') } catch { toast('Copy is blocked here. Select the text instead.') } }
  return (
    <Panel title="Handoff summary" aside="Written from this record only">
      <div className="mb-3 flex flex-wrap items-center gap-2" role="tablist">
        {(['sbar', 'mist'] as const).map(t => (
          <button key={t} type="button" role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={cx('min-h-10 rounded-md px-3 text-[15px] font-semibold', tab === t ? 'bg-ink text-white' : 'border border-line hover:bg-sunk')}>
            {t === 'sbar' ? 'SBAR · for the floor nurse' : 'MIST · from the ambulance'}
          </button>))}
        <Btn className="ml-auto min-h-10" onClick={copy}>Copy</Btn>
      </div>
      <pre className="whitespace-pre-wrap rounded-md bg-sunk p-3 font-sans text-[15px] leading-relaxed">{text}</pre>
    </Panel>
  )
}
