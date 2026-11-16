import { useEffect, useRef, useState } from 'react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { api } from './api'
import { fToC } from './api/rules'
import type { Alert, Avpu, News2, Options, Vitals } from './api'

// ---------- small shared pieces ----------
export const cx = (...a: (string | false | null | undefined)[]) => a.filter(Boolean).join(' ')

export function Panel({ title, aside, children, className }: { title?: ReactNode; aside?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cx('rounded-[4px] border border-line bg-surface p-4 sm:p-5', className)}>
      {(title || aside) && (
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
          {title && <h2 className="font-display text-[20px] font-semibold uppercase leading-tight tracking-[0.06em]">{title}</h2>}
          {aside && <div className="text-sm text-muted">{aside}</div>}
        </div>
      )}
      {children}
    </section>
  )
}

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { kind?: 'primary' | 'secondary' | 'quiet'; busy?: boolean }
export function Btn({ kind = 'secondary', busy, className, children, disabled, ...rest }: BtnProps) {
  return (
    <button
      type="button"
      disabled={disabled || busy}
      className={cx(
        'inline-flex min-h-11 items-center justify-center gap-2 rounded-[3px] px-4 font-display text-[17px] font-semibold uppercase tracking-[0.05em] transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-45',
        kind === 'primary' && 'bg-action text-black hover:bg-action-hover',
        kind === 'secondary' && 'border border-[#4a5157] bg-transparent text-ink hover:bg-sunk',
        kind === 'quiet' && 'text-muted underline underline-offset-4 hover:text-ink px-2',
        className,
      )}
      {...rest}
    >
      {busy ? 'Working…' : children}
    </button>
  )
}

export function Chip({ tone = 'neutral', children }: { tone?: 'neutral' | 'ok' | 'warn' | 'crit' | 'info'; children: ReactNode }) {
  const tones = {
    neutral: 'bg-sunk text-muted border-line',
    info: 'bg-info-bg text-info border-transparent',
    ok: 'bg-ok-bg text-ok border-transparent',
    warn: 'bg-warn-bg text-warn border-transparent',
    crit: 'bg-crit-bg text-crit border-transparent',
  }
  return <span className={cx('inline-flex items-center gap-1.5 whitespace-nowrap rounded-[3px] border px-2 py-0.5 font-display text-[15px] font-semibold uppercase tracking-[0.05em]', tones[tone])}>{children}</span>
}

export function Trend({ dir }: { dir: News2['trend'] }) {
  if (!dir) return null
  const rot = dir === 'up' ? '-45' : dir === 'down' ? '45' : '0'
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-label={`trend ${dir}`} role="img" className="inline-block">
      <g transform={`rotate(${rot} 8 8)`} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2.5 8h11M9 3.5 13.5 8 9 12.5" />
      </g>
    </svg>
  )
}

const bandTone = { low: 'ok', medium: 'warn', high: 'crit' } as const
const bandWord = { low: 'Low', medium: 'Urgent', high: 'Emergency' } as const
export function News2Pill({ n }: { n: News2 }) {
  if (!n.complete && n.present === 0) return <Chip>NEWS2 not recorded</Chip>
  return (
    <Chip tone={bandTone[n.band]}>
      <span className="num">NEWS2 {n.value}</span>
      <span>· {n.complete ? bandWord[n.band] : `incomplete ${n.present}/7`}</span>
      <Trend dir={n.trend} />
    </Chip>
  )
}

export const fmtWait = (m: number) => (m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${m % 60} min`)
export const fmtClock = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

/** A number on split-flap tiles. Each tile is keyed by its character, so it flips when the value changes. */
export function Flaps({ value, className }: { value: number | string; className?: string }) {
  const chars = String(value).split('')
  return <span className={cx('flaps', className)} aria-label={String(value)} role="img">{chars.map((c, i) => <span key={`${i}-${c}`} className="flap" aria-hidden="true">{c}</span>)}</span>
}
export const Lamp = ({ on, tone }: { on: boolean; tone?: 'ok' | 'warn' | 'crit' }) =>
  <span className={cx('lamp', tone === 'ok' && 'text-ok', tone === 'warn' && 'text-warn', tone === 'crit' && 'text-crit')} data-on={on} aria-hidden="true" />

// ---------- hooks ----------
export function useNow(ms = 1000) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), ms); return () => clearInterval(t) }, [ms])
  return now
}

/** Loads data, then refreshes every `every` ms. `reload()` refreshes immediately. */
export function useLive<T>(load: () => Promise<T>, key: string, every = 5000) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fn = useRef(load); fn.current = load
  const run = useRef(async () => {
    try { setData(await fn.current()); setError(null) } catch (e) { setError(e instanceof Error ? e.message : 'Could not reach the server.') }
  })
  useEffect(() => { setData(null); run.current(); const t = setInterval(run.current, every); return () => clearInterval(t) }, [key, every])
  return { data, error, reload: run.current, setData }
}

// ---------- backend options (complaints, injuries, bed types) ----------
let optsCache: Options | null = null
export function useOptions() {
  const [o, setO] = useState(optsCache)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => { if (!optsCache) api.options().then(x => { optsCache = x; setO(x) }).catch(e => setErr(e instanceof Error ? e.message : 'Could not reach the server.')) }, [])
  return { opts: o, error: err }
}
export const labelOf = (list: { id: string; label: string }[] | undefined, id: string) => list?.find(x => x.id === id)?.label ?? id

// ---------- toast ----------
let pushToast: (msg: string) => void = () => {}
export const toast = (msg: string) => pushToast(msg)
export function Toaster() {
  const [msg, setMsg] = useState<string | null>(null)
  useEffect(() => { let t: ReturnType<typeof setTimeout>; pushToast = m => { setMsg(m); clearTimeout(t); t = setTimeout(() => setMsg(null), 3500) } }, [])
  return (
    <div role="status" aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-5 z-50 flex justify-center px-4">
      {msg && <div className="rounded-[3px] bg-ink px-4 py-2.5 text-[15px] font-semibold text-page shadow-[0_8px_24px_rgba(0,0,0,0.55)]">{msg}</div>}
    </div>
  )
}

// ---------- alerts ----------
export function AlertRow({ a, now }: { a: Alert; now: number }) {
  let extra: ReactNode = null
  if (a.due_at) {
    const left = Math.round((Date.parse(a.due_at) - now) / 1000)
    const mm = Math.floor(Math.abs(left) / 60), ss = String(Math.abs(left) % 60).padStart(2, '0')
    extra = <span className="num font-bold">{left >= 0 ? `${mm}:${ss} left` : `overdue by ${mm}:${ss}`}</span>
  }
  const crit = a.level === 'critical'
  return (
    <div className={cx('flex flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded-[3px] px-4 py-2.5 font-display text-[19px] font-semibold uppercase tracking-[0.04em]', crit ? 'bg-crit text-black' : a.kind === 'protocol' ? 'bg-action text-black' : 'bg-warn text-black')}>
      <span><span className="mr-3 opacity-70">{a.kind === 'protocol' ? 'Next' : 'Getting worse'}</span>{a.message}</span>
      {extra}
    </div>
  )
}

// ---------- vitals entry (shared by the ambulance form and the patient view) ----------
export type VitalsDraft = Record<'resp_rate' | 'spo2' | 'sbp' | 'dbp' | 'heart_rate' | 'temp_f' | 'gcs' | 'pain' | 'glucose_mg_dl' | 'rhythm', string> & { on_oxygen: boolean; avpu: Avpu }
export const emptyDraft = (): VitalsDraft => ({ resp_rate: '', spo2: '', sbp: '', dbp: '', heart_rate: '', temp_f: '', gcs: '', pain: '', glucose_mg_dl: '', rhythm: '', on_oxygen: false, avpu: 'A' })

const RANGES: Record<string, [number, number, string]> = {
  resp_rate: [4, 60, 'Breathing rate is usually 4–60'], spo2: [50, 100, 'SpO2 must be 50–100%'],
  sbp: [50, 300, 'Systolic BP is usually 50–300'], dbp: [20, 200, 'Diastolic BP is usually 20–200'],
  heart_rate: [20, 250, 'Pulse is usually 20–250'], temp_f: [86, 110, 'Temperature is usually 86–110 °F'],
  gcs: [3, 15, 'GCS must be 3–15'], pain: [0, 10, 'Pain must be 0–10'], glucose_mg_dl: [20, 600, 'Glucose is usually 20–600 mg/dL'],
}
export const draftProblems = (d: VitalsDraft) =>
  Object.entries(RANGES).filter(([k, [lo, hi]]) => { const s = d[k as keyof VitalsDraft] as string; return s !== '' && (+s < lo || +s > hi) }).map(([k, r]) => [k, r[2]] as const)
export const draftHasValues = (d: VitalsDraft) => Object.keys(RANGES).some(k => (d[k as keyof VitalsDraft] as string) !== '')

export function draftToVitals(d: VitalsDraft, source: Vitals['source']): Vitals {
  const n = (s: string) => (s === '' ? undefined : +s)
  return {
    time: new Date().toISOString(), source, resp_rate: n(d.resp_rate), spo2: n(d.spo2), on_oxygen: d.on_oxygen,
    sbp: n(d.sbp), dbp: n(d.dbp), heart_rate: n(d.heart_rate), temp_c: d.temp_f === '' ? undefined : fToC(+d.temp_f),
    avpu: d.avpu, gcs: n(d.gcs), pain: n(d.pain), glucose_mg_dl: n(d.glucose_mg_dl), rhythm: d.rhythm || undefined,
  }
}

const inputCls = 'h-11 w-full rounded-[3px] border border-[#3d4449] bg-page px-3 text-[16px] text-ink placeholder:text-muted/60'
export function Field({ label, unit, hint, error, children }: { label: string; unit?: string; hint?: string; error?: string; children: ReactNode }) {
  return (
    <label className="flex min-w-0 flex-col gap-1 text-[14px] font-semibold text-muted">
      <span>{label}{unit && <span className="ml-1 font-normal text-muted">{unit}</span>}</span>
      {children}
      {error ? <span className="text-[13px] font-semibold text-crit">{error}</span> : hint ? <span className="text-[13px] font-normal text-muted">{hint}</span> : null}
    </label>
  )
}
export const Input = (p: React.InputHTMLAttributes<HTMLInputElement>) => <input {...p} className={cx(inputCls, p.className)} />
export const Select = (p: React.SelectHTMLAttributes<HTMLSelectElement>) => <select {...p} className={cx(inputCls, p.className)} />
export const TextArea = (p: React.TextareaHTMLAttributes<HTMLTextAreaElement>) => <textarea rows={2} {...p} className={cx(inputCls, 'h-auto py-2', p.className)} />

export function VitalsFields({ d, set, idp, rhythms }: { d: VitalsDraft; set: (d: VitalsDraft) => void; idp: string; rhythms?: { id: string; label: string }[] }) {
  const errs = Object.fromEntries(draftProblems(d))
  const num = (k: keyof typeof RANGES, label: string, unit: string, step = '1') => (
    <Field label={label} unit={unit} error={errs[k]}>
      <Input id={`${idp}-${k}`} type="number" inputMode="decimal" step={step} value={d[k as keyof VitalsDraft] as string}
        onChange={e => set({ ...d, [k]: e.target.value })} aria-invalid={!!errs[k]} />
    </Field>
  )
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {num('heart_rate', 'Pulse', '/min')}
      {num('sbp', 'Systolic BP', 'mmHg')}
      {num('dbp', 'Diastolic BP', 'mmHg')}
      {num('resp_rate', 'Breathing rate', '/min')}
      {num('spo2', 'SpO2', '%')}
      <Field label="Breathing" unit="air or oxygen">
        <Select id={`${idp}-o2`} value={d.on_oxygen ? 'y' : 'n'} onChange={e => set({ ...d, on_oxygen: e.target.value === 'y' })}>
          <option value="n">Room air</option><option value="y">On oxygen</option>
        </Select>
      </Field>
      <Field label="Temperature" unit="°F" error={errs.temp_f} hint={d.temp_f && !errs.temp_f ? `= ${fToC(+d.temp_f)} °C` : undefined}>
        <Input id={`${idp}-temp`} type="number" inputMode="decimal" step="0.1" value={d.temp_f} onChange={e => set({ ...d, temp_f: e.target.value })} />
      </Field>
      {api.can.avpu && <Field label="Alertness" unit="AVPU">
        <Select id={`${idp}-avpu`} value={d.avpu} onChange={e => set({ ...d, avpu: e.target.value as Avpu })}>
          <option value="A">Alert</option><option value="C">New confusion</option><option value="V">Responds to voice</option>
          <option value="P">Responds to pain</option><option value="U">Unresponsive</option>
        </Select>
      </Field>}
      {num('gcs', 'GCS', '3–15')}
      {num('pain', 'Pain', '0–10')}
      {api.can.glucose && num('glucose_mg_dl', 'Blood glucose', 'mg/dL')}
      <Field label="Rhythm" unit="on monitor">
        {rhythms
          ? <Select id={`${idp}-rhythm`} value={d.rhythm || rhythms[0]?.id} onChange={e => set({ ...d, rhythm: e.target.value })}>{rhythms.map(r => <option key={r.id} value={r.id}>{r.label}</option>)}</Select>
          : <Input id={`${idp}-rhythm`} value={d.rhythm} placeholder="e.g. sinus" onChange={e => set({ ...d, rhythm: e.target.value })} />}
      </Field>
    </div>
  )
}
