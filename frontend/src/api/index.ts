// The one place that decides where data comes from.
//   VITE_API=browser   the Relay Triage scoring ported to the browser (default for production builds; no server)
//   VITE_API=relay     the Relay Triage Python backend in prototype/, via the dev proxy
//   VITE_API=mock      built-in mock with stub models (default for `npm run dev`)
//   VITE_API=contract  a backend that follows docs/CONTRACT.md at VITE_API_URL
import data from '../data/relay.json'
import { contractApi } from './http'
import { mockApi } from './mock'
import { relayApi, useBrowserEngine } from './relay'
import { createEngine } from './relayEngine'
import type { RelayData } from './relayEngine'
import type { Api } from './types'

const mode = import.meta.env.VITE_API ?? (import.meta.env.PROD ? 'browser' : 'mock')
export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const storage = (() => { try { return window.sessionStorage } catch { return undefined } })()
export const api: Api =
  mode === 'browser' ? useBrowserEngine(createEngine(data as unknown as RelayData, storage).call)
  : mode === 'relay' ? relayApi
  : mode === 'contract' ? contractApi(API_URL)
  : mockApi
export * from './types'
