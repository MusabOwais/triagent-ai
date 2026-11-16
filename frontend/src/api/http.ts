// Client for a backend that follows docs/CONTRACT.md (A6) exactly.
import { BED_LABEL, COMPLAINTS, INJURIES } from './rules'
import type { Api, PatientView } from './types'

export function contractApi(base: string): Api {
  const call = async <T,>(path: string, body?: unknown, method = body === undefined ? 'GET' : 'POST'): Promise<T> => {
    const r = await fetch(base + path, {
      method, headers: { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (!r.ok) {
      const j = await r.json().catch(() => ({}))
      throw new Error(typeof j.detail === 'string' ? j.detail : `The server answered ${r.status}.`)
    }
    return r.json()
  }
  const post = (path: string, body: unknown = {}) => call<PatientView>(path, body, 'POST')
  return {
    source: { label: `Live backend · ${base.replace(/^https?:\/\//, '')}`, mock: false },
    can: { repeatVitals: true, triage: true, review: true, ambulanceEcg: true, avpu: true, glucose: true },
    options: async () => ({
      complaints: COMPLAINTS, injuries: INJURIES, scoreName: 'Bed priority',
      beds: Object.entries(BED_LABEL).map(([id, label]) => ({ id, label })),
      injuryNote: 'Draft points — clinician review needed',
    }),
    board: () => call('/board'),
    patient: id => call(`/patients/${id}`),
    create: f => post('/patients', f),
    arrive: id => post(`/patients/${id}/arrive`),
    addVitals: (id, v) => post(`/patients/${id}/vitals`, v),
    triage: (id, esi, vitals) => post(`/patients/${id}/triage`, { esi, vitals }),
    ecg: (id, record_id) => post(`/patients/${id}/ecg`, { record_id }),
    xray: (id, image_id) => post(`/patients/${id}/xray`, { image_id }),
    review: (id, type, normal, by) => post(`/patients/${id}/review`, { type, normal, by }),
    bedRequest: (id, bed_type, confirmed_by) => post(`/patients/${id}/bed-request`, { bed_type, confirmed_by }),
    rules: async () => { const r = await fetch(base + '/rules'); return r.text() },
    metrics: () => call('/metrics'),
    assets: () => call('/demo/assets'),
    reset: async () => { await call('/demo/reset', {}, 'POST') },
  }
}
