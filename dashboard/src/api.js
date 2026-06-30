// Thin wrapper around fetch. The Vite dev server proxies /api to Flask.
const BASE = '/api'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  weekly: (week) => get(`/weekly${week ? `?week=${week}` : ''}`),
  runs: () => get('/runs'),
  feeExplainer: (week) => get(`/fee-explainer${week ? `?week=${week}` : ''}`),
  emailSnapshot: (week) => get(`/email-snapshot${week ? `?week=${week}` : ''}`),
  anomalies: (week) => get(`/anomalies${week ? `?week=${week}` : ''}`),
  decision: (week) => get(`/decision${week ? `?week=${week}` : ''}`),
  themeDrilldown: (id, week, lang) => {
    const params = new URLSearchParams()
    if (week) params.set('week', week)
    if (lang) params.set('lang', lang)
    const q = params.toString()
    return get(`/theme/${id}${q ? `?${q}` : ''}`)
  },
  triggerRun: (week) => post('/run', { week }),
  approveGate: (gate, week) => post('/mcp/approve', { gate, week }),
}
