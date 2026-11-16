// Shapes copied from docs/CONTRACT.md (A6). Change only with the whole team.

// Ids for complaints, injuries and bed types come from the backend (see Api.options), so they are plain strings.
export type Complaint = string
export type Injury = string
export type BedType = string
export type Status = 'en_route' | 'waiting' | 'bed_requested' | 'in_bed'
export type Avpu = 'A' | 'C' | 'V' | 'P' | 'U'

export interface Vitals {
  time: string
  source: 'ambulance' | 'triage' | 'er'
  resp_rate?: number
  spo2?: number
  on_oxygen?: boolean
  sbp?: number
  dbp?: number
  heart_rate?: number
  temp_c?: number
  avpu?: Avpu
  gcs?: number
  pain?: number
  glucose_mg_dl?: number
  rhythm?: string
}

export interface EcgResult {
  abnormal_prob: number
  abnormal: boolean
  threshold: number
  model: string
  note: string
  /** Per-class probabilities, when the model reports more than normal/abnormal. */
  classes?: Record<string, number>
  /** What this result did to the score, in the backend's own words. */
  effect?: string
}

export interface XrayResult {
  findings: Record<string, number>
  flagged: string[]
  thresholds: Record<string, number>
  model: string
  note: string
  effect?: string
}

export interface Review { type: 'ecg' | 'xray'; normal: boolean; by: string; time: string }

export interface PatientRecord {
  id: string
  demo: boolean
  name: string
  age: number
  sex: 'M' | 'F'
  complaint_category: Complaint
  complaint_text: string
  onset_time: string
  history: string
  medications: string
  allergies: string
  injuries: Injury[]
  treatments: { time: string; what: string }[]
  vitals: Vitals[]
  esi: number | null
  arrival_time: string | null
  status: Status
  ecg: { record_id: string; result: EcgResult; time: string } | null
  xray: { image_id: string; result: XrayResult; time: string } | null
  reviews: Review[]
  bed_request: { bed_type: BedType; confirmed_by: string; time: string } | null
}

export interface News2 {
  value: number
  band: 'low' | 'medium' | 'high'
  complete: boolean
  present: number
  trend: 'up' | 'down' | 'flat' | null
  previous: number | null
  parts: Record<string, number | null>
}

export interface Alert {
  kind: 'protocol' | 'deterioration'
  level: 'warning' | 'critical'
  message: string
  due_at: string | null
}

/** A backend-specific explanation of the score, shown instead of the contract's A + B + C strip. */
export interface Strip {
  title: string
  formula: string
  cells: { name: string; value: string; tone?: 'low' | 'medium' | 'high'; sub?: string; lines: string[]; note?: string }[]
}

export interface FindingItem { source: 'ecg' | 'xray' | 'injury'; label: string; points: number }

export interface PatientView {
  patient: PatientRecord
  scores: {
    admission: { probability: number; stage: 'ambulance' | 'triage'; model?: string; top_reasons: { label: string; direction: 'up' | 'down' }[] }
    news2: News2
    findings: { points: number; items: FindingItem[] }
    parts: { A: number; B: number; C: number }
    priority: number
    wait_minutes: number
    queue_rank_score: number
    /** Points added for waiting, when the backend expresses it in score points. */
    wait_bonus: number | null
    strip?: Strip
  }
  bed_type: { suggested: BedType; reason: string }
  alerts: Alert[]
  pending: string[]
  handoff: { mist: string; sbar: string }
  history?: { time: string; text: string; score: number }[]
}

export interface IntakeForm {
  name: string
  age: number
  sex: 'M' | 'F'
  complaint_category: Complaint
  complaint_text: string
  onset_time: string
  history: string
  medications: string
  allergies: string
  injuries: Injury[]
  treatments: { time: string; what: string }[]
  vitals: Vitals[]
  ecg_record_id?: string
}

export interface DemoAssets {
  ecgs: { id: string; label: string; truth?: string[] }[]
  xrays: { id: string; label: string; image_url?: string; truth?: string[] }[]
  /** Set when a model cannot run on this machine; the text says why. */
  unavailable?: { ecg?: string; xray?: string }
}

export interface Options {
  complaints: { id: string; label: string }[]
  injuries: { id: string; label: string; points?: number }[]
  beds: { id: string; label: string }[]
  /** When present the rhythm field is a fixed list instead of free text. */
  rhythms?: { id: string; label: string }[]
  scoreName: string
  injuryNote: string
}

export interface Capabilities { repeatVitals: boolean; triage: boolean; review: boolean; ambulanceEcg: boolean; avpu: boolean; glucose: boolean }

export interface ModelMetric { name: string; dataset: string; result: string; note: string }

export interface Api {
  /** Short label shown in the header so nobody mistakes mock data for the real models. */
  source: { label: string; mock: boolean }
  can: Capabilities
  options(): Promise<Options>
  board(): Promise<PatientView[]>
  patient(id: string): Promise<PatientView>
  create(form: IntakeForm): Promise<PatientView>
  /** Score preview before sending. Not every backend has it. */
  preview?(form: IntakeForm): Promise<PatientView>
  arrive(id: string): Promise<PatientView>
  addVitals(id: string, v: Vitals): Promise<PatientView>
  triage(id: string, esi: number, v: Vitals): Promise<PatientView>
  ecg(id: string, recordId: string): Promise<PatientView>
  xray(id: string, imageId: string): Promise<PatientView>
  review(id: string, type: 'ecg' | 'xray', normal: boolean, by: string): Promise<PatientView>
  bedRequest(id: string, bedType: BedType, by: string): Promise<PatientView>
  rules(): Promise<string>
  metrics(): Promise<ModelMetric[]>
  assets(): Promise<DemoAssets>
  reset(): Promise<void>
  /** Lead II of a demo ECG, 10 seconds, for drawing the trace. */
  ecgTrace?(recordId: string): Promise<number[]>
}
