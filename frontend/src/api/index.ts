// The one place that decides where data comes from.
//   VITE_API=mock      built-in mock with stub models (default)
//   VITE_API=relay     the Relay Triage backend in prototype/ (real models), via the dev proxy
//   VITE_API=contract  a backend that follows docs/CONTRACT.md at VITE_API_URL
import { contractApi } from './http'
import { mockApi } from './mock'
import { relayApi } from './relay'
import type { Api } from './types'

const mode = import.meta.env.VITE_API ?? 'mock'
export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const api: Api = mode === 'relay' ? relayApi : mode === 'contract' ? contractApi(API_URL) : mockApi
export * from './types'
