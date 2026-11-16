// Checks the browser port (src/api/relayEngine.ts) against outputs from the real Python backend.
// engine-ref.json was produced by running prototype/app/scoring.py on 8 patients and all 16 demo samples.
// Run: node scripts/check-engine.ts
import { readFileSync } from 'node:fs'
import { createEngine } from '../src/api/relayEngine.ts'

const data = JSON.parse(readFileSync(new URL('../src/data/relay.json', import.meta.url), 'utf8'))
const ref = JSON.parse(readFileSync(new URL('./engine-ref.json', import.meta.url), 'utf8'))
const E = createEngine(data)
let bad = 0, n = 0
const close = (a: number, b: number) => Math.abs(a - b) < 1e-9
const check = (what: string, got: unknown, want: unknown) => {
  n++
  const ok = typeof want === 'number' && typeof got === 'number' ? close(got, want) : JSON.stringify(got) === JSON.stringify(want)
  if (!ok) { bad++; console.log(`MISMATCH ${what}: got ${JSON.stringify(got)}, Python gives ${JSON.stringify(want)}`) }
}
ref.stage1.forEach((c: any, i: number) => {
  const r: any = E.stage1(c.intake)
  for (const k of Object.keys(c.out)) check(`patient ${i} ${k}`, r[k], c.out[k])
  check(`patient ${i} model parts`, r.model_parts.length, c.n_model_parts)
  check(`patient ${i} overlay`, r.overlay_parts, c.overlay)
})
for (const [sid, want] of Object.entries<any>(ref.ecg)) {
  const pc = data.pre.ecg[sid], d: any = E.ecgDelta(pc)
  for (const k of ['delta_raw', 'delta', 'note']) check(`${sid} ${k}`, d[k], want[k])
  check(`${sid} bed from Telemetry`, E.bedAfterEcg('Telemetry', pc), want.bed_from_telemetry)
  check(`${sid} bed from General ward`, E.bedAfterEcg('General ward', pc), want.bed_from_general)
}
for (const [sid, want] of Object.entries<any>(ref.cxr)) {
  const d: any = E.cxrDelta(data.pre.cxr[sid])
  for (const k of ['delta_raw', 'delta', 'note', 'p_normal']) check(`${sid} ${k}`, d[k], want[k])
}
console.log(bad ? `${bad} of ${n} checks failed` : `All ${n} checks match the Python backend`)
process.exit(bad ? 1 : 0)
