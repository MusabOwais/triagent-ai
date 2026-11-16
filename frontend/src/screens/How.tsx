import { useEffect, useState } from 'react'
import { api } from '../api'
import type { ModelMetric } from '../api'
import { Chip, Panel } from '../ui'

/** Rules text arrives as blocks: a heading line, then indented lines. Blank lines separate blocks. */
function parse(text: string) {
  return text.split(/\n\s*\n/).map(block => {
    const [head, ...rest] = block.split('\n').map(l => l.trim()).filter(Boolean)
    return { head, lines: rest }
  }).filter(b => b.head)
}

export default function How() {
  const [rules, setRules] = useState<string | null>(null)
  const [metrics, setMetrics] = useState<ModelMetric[]>([])
  useEffect(() => { api.rules().then(setRules).catch(() => setRules('')); api.metrics().then(setMetrics).catch(() => {}) }, [])
  const blocks = parse(rules ?? '')
  const sections = blocks.filter(b => b.lines.length), notes = blocks.filter(b => !b.lines.length)

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-[38px] font-bold">How it works</h1>
        <p className="mt-1 max-w-[70ch] text-muted">Every number on the board comes from one of three measured models or from a written rule on this page. Nothing is hidden, and the app never decides for the clinician.</p>
      </div>

      <Panel title="The three models" aside={api.source.mock ? <Chip tone="warn">Stub models in use</Chip> : <Chip tone="ok">Measured on held-out test data</Chip>}>
        <ul className="grid gap-px overflow-hidden rounded-[3px] bg-line md:grid-cols-3">
          {metrics.map(m => (
            <li key={m.name} className="flex min-w-0 flex-col gap-1 bg-surface p-4">
              <div className="font-display text-[16px] font-semibold uppercase tracking-[0.08em] text-muted">{m.dataset}</div>
              <div className="font-display text-[26px] font-bold uppercase leading-tight tracking-[0.02em]">{m.name}</div>
              <div className="num text-[16px] font-semibold">{m.result}</div>
              <p className="text-[14px] text-muted">{m.note}</p>
            </li>))}
        </ul>
        <p className="mt-3 max-w-[75ch] text-[14px] text-muted">The three datasets come from different patients, so no single model combines them. They meet only through the written rules below. Every model output is an AI flag, not a diagnosis.</p>
      </Panel>

      {rules === null ? <div className="h-64 animate-pulse rounded-[4px] bg-line/50" aria-label="Loading the rules" /> : (
        <div className="grid gap-4 lg:grid-cols-2">
          {sections.map(b => (
            <Panel key={b.head} title={b.head}>
              <ul className="flex flex-col gap-1.5 text-[15px] leading-relaxed">{b.lines.map(l => <li key={l}>{l}</li>)}</ul>
            </Panel>))}
        </div>
      )}
      {notes.map(n => <p key={n.head} className="max-w-[80ch] text-[15px] text-muted">{n.head}</p>)}
    </div>
  )
}
