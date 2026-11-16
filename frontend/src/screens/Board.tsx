import { Fragment, useState } from 'react'
import { api } from '../api'
import type { BedType, Options, PatientView } from '../api'
import { Btn, Chip, cx, Field, Flaps, fmtWait, Input, labelOf, News2Pill, Panel, Select, toast, useLive, useNow, useOptions } from '../ui'


export default function Board() {
  const { data, error, reload } = useLive<PatientView[]>(() => api.board(), 'board')
  const now = useNow()
  const { opts } = useOptions()
  const bedName = (id: string) => labelOf(opts?.beds, id).replace(/ \(.*\)$/, '')
  const ccName = (id: string) => labelOf(opts?.complaints, id)
  const [opened, setOpened] = useState<BedType | null>(null) // "a bed of this type just opened"
  const [reqFor, setReqFor] = useState<string | null>(null)

  if (error && !data) return <p className="rounded-md bg-crit-bg px-4 py-3 font-semibold text-crit">{error}</p>
  if (!data || !opts) return <div className="h-64 animate-pulse rounded-lg bg-line/50" aria-label="Loading bed board" />

  const incoming = data.filter(v => v.patient.status === 'en_route')
  const waiting = data.filter(v => v.patient.status === 'waiting')
  const requested = data.filter(v => v.patient.status === 'bed_requested' || v.patient.status === 'in_bed')
  const match = opened ? waiting.find(v => v.bed_type.suggested === opened) : null

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[38px] font-bold">Bed board</h1>
          <p className="mt-1 max-w-[70ch] text-muted">Ranked by {opts.scoreName.toLowerCase()} plus time waited, so nobody waits forever. The board suggests; you confirm every bed request. <a className="font-semibold text-ink underline" href="#how">How every number is made</a></p>
        </div>
        <div className="num text-[15px] text-muted">{waiting.length} waiting · {incoming.length} incoming · {requested.length} requested</div>
      </div>

      {incoming.length > 0 && (
        <Panel title="Incoming ambulances">
          <ul className="grid gap-2 md:grid-cols-2">
            {incoming.map(v => (
              <li key={v.patient.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-line px-3 py-2.5">
                <Flaps value={v.scores.priority} className="text-[38px]" />
                <a href={`#p-${v.patient.id}`} className="font-display text-[22px] font-semibold uppercase leading-tight tracking-[0.03em] underline-offset-4 hover:underline">{v.patient.name}</a>
                <span className="text-muted">{ccName(v.patient.complaint_category)}</span>
                <News2Pill n={v.scores.news2} />
                {v.alerts.map(a => <Chip key={a.message} tone={a.level === 'critical' ? 'crit' : 'warn'}>{a.message.split(':')[0]}</Chip>)}
                <Btn className="ml-auto min-h-9 px-3 text-[14px]" onClick={async () => { await api.arrive(v.patient.id); toast(`${v.patient.name} arrived. Handoff received.`); reload() }}>Mark arrived</Btn>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <Panel title="Waiting for a bed" aside={
        <label className="flex items-center gap-2 text-ink">
          <span className="whitespace-nowrap font-semibold">A bed just opened:</span>
          <Select id="board-opened" className="h-10 !w-52" value={opened ?? ''} onChange={e => setOpened((e.target.value || null) as BedType | null)}>
            <option value="">Choose a bed type</option>{opts.beds.map(b => <option key={b.id} value={b.id}>{bedName(b.id)}</option>)}
          </Select>
        </label>}>
        {opened && (
          <p className={cx('mb-3 rounded-md px-3 py-2 text-[15px] font-semibold', match ? 'bg-action font-display text-[18px] uppercase tracking-[0.04em] text-black' : 'bg-sunk text-muted')}>
            {match ? <>Open bed: {bedName(opened)}. Highest-ranked match: {match.patient.name}. Review and send the request if you agree.</> : <>Open bed: {bedName(opened)}. Nobody waiting is suggested for this bed type.</>}
          </p>
        )}
        {waiting.length === 0 ? <p className="text-muted">Nobody is waiting. New patients appear here when an ambulance arrives.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-left text-[15px]">
              <thead className="text-[13px] text-muted"><tr>{['Rank', 'Patient', opts.scoreName, 'NEWS2', 'Admission model', 'Suggested bed', 'Waited', ''].map(h => <th key={h} className="whitespace-nowrap border-b border-line py-1.5 pr-3 font-semibold">{h}</th>)}</tr></thead>
              <tbody>
                {waiting.map((v, i) => {
                  const p = v.patient, hit = match?.patient.id === p.id, bonus = v.scores.wait_bonus ?? 0
                  return (
                    <Fragment key={p.id}>
                      <tr className={cx('border-b border-line align-top', hit && 'bg-action/10')}>
                        <td className="num py-3 pr-3 font-display text-[22px] font-semibold text-muted">{i + 1}</td>
                        <td className="py-3 pr-3">
                          <a href={`#p-${p.id}`} className="font-display text-[22px] font-semibold uppercase leading-tight tracking-[0.03em] underline-offset-4 hover:underline">{p.name}</a>
                          <div className="text-[14px] text-muted">{p.age} y · {ccName(p.complaint_category)}{p.esi ? ` · ESI ${p.esi}` : ''}</div>
                          {v.alerts.length > 0 && <div className="mt-1 flex flex-wrap gap-1">{v.alerts.map(a => {
                            const left = a.due_at ? Math.round((Date.parse(a.due_at) - now) / 60000) : null
                            return <Chip key={a.message} tone={a.level === 'critical' ? 'crit' : 'warn'}>{a.message}{left !== null ? (left >= 0 ? ` · ${left} min left` : ` · overdue ${-left} min`) : ''}</Chip> })}</div>}
                        </td>
                        <td className="num whitespace-nowrap py-3 pr-3"><Flaps value={v.scores.priority} className="text-[38px]" />{bonus > 0 && <span className="ml-1 text-[14px] text-muted">+{bonus} wait</span>}</td>
                        <td className="py-3 pr-3"><News2Pill n={v.scores.news2} /></td>
                        <td className="num py-3 pr-3">{v.scores.parts.A}%</td>
                        <td className="py-3 pr-3"><span className="font-display text-[20px] font-semibold uppercase tracking-[0.04em]">{bedName(v.bed_type.suggested)}</span><div className="text-[14px] text-muted">{v.bed_type.reason}</div></td>
                        <td className="num whitespace-nowrap py-3 pr-3">{fmtWait(v.scores.wait_minutes)}</td>
                        <td className="py-2 text-right"><Btn kind={hit ? 'primary' : 'secondary'} className="min-h-10 whitespace-nowrap px-3 text-[14px]" onClick={() => setReqFor(reqFor === p.id ? null : p.id)}>{reqFor === p.id ? 'Close' : 'Review bed request'}</Btn></td>
                      </tr>
                      {reqFor === p.id && <tr className="border-b border-line"><td colSpan={8} className="bg-sunk p-4"><BedRequest v={v} opts={opts} onSent={() => { setReqFor(null); setOpened(null); reload() }} /></td></tr>}
                    </Fragment>)
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      {requested.length > 0 && (
        <Panel title="Bed requested">
          <ul className="divide-y divide-line text-[15px]">
            {requested.map(v => (
              <li key={v.patient.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5">
                <a href={`#p-${v.patient.id}`} className="font-display text-[22px] font-semibold uppercase leading-tight tracking-[0.03em] underline-offset-4 hover:underline">{v.patient.name}</a>
                <Chip tone="ok">{bedName(v.patient.bed_request!.bed_type)}</Chip>
                <span className="text-muted">confirmed by {v.patient.bed_request!.confirmed_by}</span>
              </li>))}
          </ul>
        </Panel>
      )}
    </div>
  )
}

function BedRequest({ v, opts, onSent }: { v: PatientView; opts: Options; onSent: () => void }) {
  const [bed, setBed] = useState<BedType>(v.bed_type.suggested)
  const [by, setBy] = useState(''); const [busy, setBusy] = useState(false)
  const todo = v.pending.filter(x => !/^Bed (request|type) not/.test(x))
  const situation = v.handoff.sbar.split('\n')[0].replace(/^S — /, '')
  const send = async () => {
    setBusy(true)
    try { await api.bedRequest(v.patient.id, bed, by.trim()); toast(`Bed request sent for ${v.patient.name}: ${labelOf(opts.beds, bed)}.`); onSent() }
    catch (e) { toast(e instanceof Error ? e.message : 'Could not send the request.'); setBusy(false) }
  }
  return (
    <div className="grid gap-4 md:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
      <div className="min-w-0">
        <h3 className="font-bold">Bed request for {v.patient.name}</h3>
        <p className="mt-1 text-[15px]">{situation}</p>
        <p className="mt-2 text-[14px] text-muted">{opts.scoreName} {v.scores.priority}: {v.scores.strip ? v.scores.strip.formula : `(${v.scores.parts.A} + ${v.scores.parts.B}) ÷ 2 + ${v.scores.parts.C}`}. Waited {fmtWait(v.scores.wait_minutes)}.{todo.length ? ` Still to do: ${todo.join('; ')}.` : ''}</p>
      </div>
      <div className="flex min-w-0 flex-col gap-3">
        <Field label="Bed type" hint={bed === v.bed_type.suggested ? `Suggested because: ${v.bed_type.reason}.` : 'You changed the suggestion. Your choice is what gets sent.'}>
          <Select id={`req-bed-${v.patient.id}`} value={bed} onChange={e => setBed(e.target.value as BedType)}>{opts.beds.map(b => <option key={b.id} value={b.id}>{b.label}</option>)}</Select>
        </Field>
        <Field label="Your name and role"><Input id={`req-by-${v.patient.id}`} value={by} onChange={e => setBy(e.target.value)} placeholder="e.g. R. Gomez, charge nurse" /></Field>
        <Btn kind="primary" busy={busy} disabled={!by.trim()} onClick={send}>Confirm and send bed request</Btn>
      </div>
    </div>
  )
}
