import { Fragment, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import type { Complaint, DemoAssets, Injury, IntakeForm, PatientView, Vitals } from '../api'
import { cToF, news2Of } from '../api/rules'
import {
  Btn, Chip, draftHasValues, draftProblems, draftToVitals, emptyDraft, Field, fmtClock, Input, News2Pill,
  labelOf, Panel, Select, TextArea, toast, useOptions, VitalsFields,
} from '../ui'
import type { VitalsDraft } from '../ui'

const START: VitalsDraft = { ...emptyDraft(), heart_rate: '96', sbp: '138', dbp: '84', resp_rate: '18', spo2: '96', temp_f: '98.6', gcs: '15', pain: '5' }

export default function Ambulance() {
  const [f, setF] = useState({ name: '', age: '58', sex: 'M' as 'M' | 'F', complaint_category: '__unset' as Complaint, complaint_text: '', onset_time: '', history: '', medications: '', allergies: '' })
  const [injuries, setInjuries] = useState<Injury[]>([])
  const [treatments, setTreatments] = useState<{ time: string; what: string }[]>([])
  const [tx, setTx] = useState('')
  const [sets, setSets] = useState<Vitals[]>([])
  const [draft, setDraft] = useState<VitalsDraft>(START)
  const [dirty, setDirty] = useState(true)
  const [ecgId, setEcgId] = useState('')
  const [assets, setAssets] = useState<DemoAssets | null>(null)
  const [preview, setPreview] = useState<PatientView | null>(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => { api.assets().then(setAssets).catch(() => {}) }, [])
  const { opts, error: optsError } = useOptions()
  // Start on chest pain when the backend's complaint list has it.
  useEffect(() => {
    if (opts && !opts.complaints.some(c => c.id === f.complaint_category))
      setF(x => ({ ...x, complaint_category: (opts.complaints.find(c => /chest/i.test(c.id)) ?? opts.complaints[0]).id }))
  }, [opts, f.complaint_category])

  const problems = draftProblems(draft)
  const ageOk = +f.age >= 18 && +f.age <= 110
  const form: IntakeForm = useMemo(() => ({
    ...f, age: +f.age, injuries, treatments, ecg_record_id: ecgId || undefined,
    vitals: dirty && draftHasValues(draft) ? [...sets, draftToVitals(draft, 'ambulance')] : sets,
  }), [f, injuries, treatments, ecgId, sets, draft, dirty])

  // Live preview. NEWS2 is worked out here; the priority needs the backend's model.
  useEffect(() => {
    if (!api.preview || !opts || !ageOk || problems.length) { setPreview(null); return }
    let live = true
    const t = setTimeout(() => api.preview!(form).then(v => live && setPreview(v)).catch(() => live && setPreview(null)), 250)
    return () => { live = false; clearTimeout(t) }
  }, [form, opts, ageOk, problems.length])

  const news2 = { ...news2Of(form.vitals[form.vitals.length - 1]), trend: null, previous: null }
  const up = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })

  const addSet = () => {
    if (problems.length) return toast('Fix the highlighted vitals first.')
    if (!draftHasValues(draft)) return toast('Enter at least one vital sign.')
    setSets([...sets, draftToVitals(draft, 'ambulance')]); setDirty(false)
    toast('Vitals set saved with the current time. Change any value to start the next set.')
  }
  const send = async () => {
    if (!f.name.trim()) { toast('Enter the patient’s name before sending.'); document.getElementById('amb-name')?.focus(); return }
    if (!ageOk) return toast('Age must be between 18 and 110.')
    if (problems.length) return toast('Fix the highlighted vitals first.')
    if (!form.vitals.length) return toast('Record at least one set of vitals.')
    setBusy(true)
    try { const v = await api.create(form); toast(`Sent. ${f.name} is on the bed board as incoming.`); location.hash = `p-${v.patient.id}` }
    catch (e) { toast(e instanceof Error ? e.message : 'Could not send.'); setBusy(false) }
  }

  if (optsError) return <p className="rounded-md bg-crit-bg px-4 py-3 font-semibold text-crit">{optsError}</p>
  if (!opts) return <div className="h-64 animate-pulse rounded-lg bg-line/50" aria-label="Loading form" />

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="flex min-w-0 flex-col gap-4">
        <div>
          <h1 className="text-[26px] font-extrabold tracking-tight">Ambulance handoff</h1>
          <p className="mt-1 max-w-[65ch] text-muted">Enter it once here. The ER sees this record before you arrive, and nobody has to ask for it again.</p>
        </div>

        <Panel title="Patient">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="col-span-2"><Field label="Name"><Input id="amb-name" value={f.name} onChange={up('name')} placeholder="Full name" autoComplete="off" /></Field></div>
            <Field label="Age" error={f.age !== '' && !ageOk ? 'Must be 18–110' : undefined}><Input id="amb-age" type="number" inputMode="numeric" value={f.age} onChange={up('age')} /></Field>
            <Field label="Sex"><Select id="amb-sex" value={f.sex} onChange={up('sex')}><option value="M">Male</option><option value="F">Female</option></Select></Field>
          </div>
        </Panel>

        <Panel title="Main complaint">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Reason for the call"><Select id="amb-cc" value={f.complaint_category} onChange={up('complaint_category')}>{opts.complaints.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}</Select></Field>
            <Field label="When it started"><Input id="amb-onset" value={f.onset_time} onChange={up('onset_time')} placeholder="e.g. 30 min before call" /></Field>
            <div className="sm:col-span-2"><Field label="What the patient describes"><TextArea id="amb-detail" value={f.complaint_text} onChange={up('complaint_text')} /></Field></div>
          </div>
        </Panel>

        <Panel title="Vital signs" aside={sets.length ? `${sets.length} set${sets.length > 1 ? 's' : ''} saved` : 'No set saved yet'}>
          <VitalsFields d={draft} set={d => { setDraft(d); setDirty(true) }} idp="amb-v" rhythms={opts.rhythms} />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Btn onClick={addSet}>Add vitals set</Btn>
            <span className="text-[14px] text-muted">{api.can.repeatVitals ? 'Each set is saved with the time, so the ER can see the trend.' : 'Each set is saved with the time. The ER system scores the latest set.'}</span>
          </div>
          {sets.length > 0 && (
            <ul className="mt-3 divide-y divide-line border-t border-line text-[14px]">
              {sets.map((s, i) => (
                <li key={i} className="num flex flex-wrap gap-x-4 py-2">
                  <b>{fmtClock(s.time)}</b><span>HR {s.heart_rate ?? '—'}</span><span>BP {s.sbp ?? '—'}/{s.dbp ?? '—'}</span><span>RR {s.resp_rate ?? '—'}</span>
                  <span>SpO2 {s.spo2 ?? '—'}%</span><span>Temp {s.temp_c !== undefined ? `${cToF(s.temp_c)} °F` : '—'}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Visible injuries" aside={<Chip tone="warn">{opts.injuryNote}</Chip>}>
          <div className="grid gap-2 sm:grid-cols-2">
            {opts.injuries.map(i => (
              <label key={i.id} className="flex min-h-11 cursor-pointer items-center gap-3 rounded-md border border-line px-3 text-[15px] has-checked:border-action has-checked:bg-[#eef2fa]">
                <input id={`amb-inj-${i.id}`} type="checkbox" className="size-5" checked={injuries.includes(i.id)}
                  onChange={e => setInjuries(e.target.checked ? [...injuries, i.id] : injuries.filter(x => x !== i.id))} />
                <span className="flex-1">{i.label}</span>{i.points !== undefined && <span className="num text-muted">+{i.points}</span>}
              </label>
            ))}
          </div>
        </Panel>

        <Panel title="Medical information">
          <div className="grid gap-3 sm:grid-cols-3">
            <Field label="Relevant history"><TextArea id="amb-hx" value={f.history} onChange={up('history')} /></Field>
            <Field label="Current medications"><TextArea id="amb-meds" value={f.medications} onChange={up('medications')} /></Field>
            <Field label="Allergies"><TextArea id="amb-all" value={f.allergies} onChange={up('allergies')} /></Field>
          </div>
        </Panel>

        <Panel title="Treatments given">
          <div className="flex gap-2">
            <Input id="amb-tx" value={tx} onChange={e => setTx(e.target.value)} placeholder="e.g. Aspirin 324 mg by mouth"
              onKeyDown={e => { if (e.key === 'Enter' && tx.trim()) { setTreatments([...treatments, { time: fmtClock(new Date().toISOString()), what: tx.trim() }]); setTx('') } }} />
            <Btn disabled={!tx.trim()} onClick={() => { setTreatments([...treatments, { time: fmtClock(new Date().toISOString()), what: tx.trim() }]); setTx('') }}>Add</Btn>
          </div>
          {treatments.length === 0
            ? <p className="mt-2 text-[14px] text-muted">Each treatment is stamped with the time you add it.</p>
            : <ul className="mt-3 divide-y divide-line border-t border-line text-[15px]">{treatments.map((t, i) => (
                <li key={i} className="flex items-center justify-between gap-3 py-2"><span><b className="num">{t.time}</b> · {t.what}</span>
                  <Btn kind="quiet" className="min-h-9" onClick={() => setTreatments(treatments.filter((_, j) => j !== i))}>Remove</Btn></li>))}</ul>}
        </Panel>

        {api.can.ambulanceEcg && <Panel title="12-lead ECG" aside="Optional">
          <Field label="Transmit an ECG with the handoff" hint="In this proof of concept you pick a held-out demo recording instead of a live transmission.">
            <Select id="amb-ecg" value={ecgId} onChange={e => setEcgId(e.target.value)}>
              <option value="">No ECG recorded in the ambulance</option>
              {assets?.ecgs.map(e => <option key={e.id} value={e.id}>{e.label}</option>)}
            </Select>
          </Field>
        </Panel>}
      </div>

      <aside className="lg:sticky lg:top-[76px] lg:self-start">
        <Panel title="Before you send">
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2"><News2Pill n={news2} /></div>
            {preview ? (
              <>
                <div className="flex items-end gap-3">
                  <span className="num text-[52px] font-extrabold leading-none">{preview.scores.priority}</span>
                  <span className="pb-1 text-[14px] text-muted">{opts.scoreName.toLowerCase()}<br />out of 100</span>
                </div>
                <dl className="num grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 text-[15px]">
                  {preview.scores.strip ? preview.scores.strip.cells.map(c => <Fragment key={c.name}><dt>{c.name}</dt><dd className="text-right font-semibold">{c.value}</dd></Fragment>) : <>
                    <dt>Needs a bed</dt><dd className="text-right font-semibold">{preview.scores.parts.A}%</dd>
                    <dt>Sick right now (NEWS2 × 5)</dt><dd className="text-right font-semibold">{preview.scores.parts.B}</dd>
                    <dt>Findings</dt><dd className="text-right font-semibold">+{preview.scores.parts.C}</dd></>}
                </dl>
                {preview.scores.strip && <p className="text-[14px] text-muted">{preview.scores.strip.formula}.</p>}
                <p className="text-[14px] text-muted">Suggested bed: <b className="text-ink">{labelOf(opts.beds, preview.bed_type.suggested)}</b>. {preview.bed_type.reason}.</p>
                {preview.alerts.filter(a => !a.due_at).map(a => <p key={a.message} className="rounded-md bg-crit-bg px-3 py-2 text-[14px] font-semibold text-crit">{a.message}</p>)}
              </>
            ) : (
              <p className="text-[14px] text-muted">{problems.length || !ageOk ? 'Fix the highlighted fields to see the score.' : api.preview ? 'The score appears once pulse, blood pressure, breathing rate, SpO2 and temperature are filled in.' : 'The score is calculated by the ER system when you send.'}</p>
            )}
            <Btn kind="primary" busy={busy} onClick={send} className="mt-1 w-full">Send to ER</Btn>
            <p className="text-[13px] text-muted">The ER charge nurse sees this patient as incoming straight away.</p>
          </div>
        </Panel>
      </aside>
    </div>
  )
}
