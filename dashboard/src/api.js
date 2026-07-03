// Thin wrapper around fetch. In dev, Vite proxies /api to Flask. In production
// (GitHub Pages build), there is no backend — we serve the bundled JSON that
// was committed under dashboard/public/data. STATIC mode does read-only.
const STATIC = import.meta.env.PROD
const BASE_URL = import.meta.env.BASE_URL || '/'

async function get(path) {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

const STATIC_DIR = `${BASE_URL}data/runs/`
async function loadRunFile(week) {
  const name = week ? `${week}.json` : 'latest.json'
  return get(`${STATIC_DIR}${name}`)
}

async function loadDrillFile(week) {
  const runIndex = await loadRunFile(null)
  const label = week || runIndex.week_label
  return get(`${STATIC_DIR}${label}.drill.json`)
}

async function staticRuns() {
  // The bundled site knows about at most the runs we shipped. Read latest
  // then the baseline it references — that's the visible history.
  const latest = await loadRunFile(null)
  const runs = [
    {
      week_label: latest.week_label,
      generated_at: latest.generated_at,
      total: latest.total,
      themes: latest.clusters.map((c) => c.label),
    },
  ]
  if (latest.baseline_week_label) {
    try {
      const b = await loadRunFile(latest.baseline_week_label)
      runs.push({
        week_label: b.week_label,
        generated_at: b.generated_at,
        total: b.total,
        themes: b.clusters.map((c) => c.label),
      })
    } catch { /* baseline may not be bundled */ }
  }
  return runs
}

async function staticEmailSnapshot(week) {
  const data = await loadRunFile(week)
  const pulse = data.pulse ?? {}
  const clusters = data.clusters ?? []
  const bullets = clusters.slice(0, 5).map((c) =>
    `<li><b>${c.label}</b> — ${c.size} reviews (avg ★${c.avg_rating.toFixed(1)})</li>`
  ).join('')
  const actions = (pulse.actions ?? []).map((a) =>
    `<li>[${a.priority}] ${a.text}</li>`
  ).join('')
  return {
    to: 'product-team@groww.in',
    subject: `Weekly Pulse — ${data.week_label}`,
    html: `<div style="font-family:-apple-system,Segoe UI,sans-serif">
  <h2>Weekly Pulse — ${data.week_label}</h2>
  <p>${pulse.summary ?? ''}</p>
  <h3>Top themes</h3><ul>${bullets}</ul>
  <h3>Strategic recommendation</h3><blockquote>${pulse.recommendation ?? ''}</blockquote>
  <h3>Prioritised actions</h3><ol>${actions}</ol>
</div>`,
  }
}

async function staticThemeDrilldown(id, week, lang) {
  const drill = await loadDrillFile(week)
  const cluster = drill.clusters.find((c) => c.id === id)
  if (!cluster) throw new Error('cluster not found')
  const idx = cluster.indices || []
  let items = idx.map((i) => drill.reviews[i]).filter(Boolean)
  if (lang) items = items.filter((r) => r.lang === lang)
  return {
    label: cluster.label,
    id: cluster.id,
    total_in_cluster: idx.length,
    reviews: items.slice(0, 50),
  }
}

export const api = STATIC
  ? {
      weekly: (week) => loadRunFile(week),
      runs: () => staticRuns(),
      feeExplainer: async (week) => (await loadRunFile(week)).fee ?? {},
      emailSnapshot: (week) => staticEmailSnapshot(week),
      anomalies: async (week) => (await loadRunFile(week)).anomalies ?? [],
      decision: async (week) => (await loadRunFile(week)).decision ?? {},
      themeDrilldown: (id, week, lang) => staticThemeDrilldown(id, week, lang),
      triggerRun: async () => ({ run_id: 'static-mode' }),
      approveGate: async () => ({ status: 'dry_run', reason: 'static build' }),
    }
  : {
      weekly: (week) => get(`/api/weekly${week ? `?week=${week}` : ''}`),
      runs: () => get('/api/runs'),
      feeExplainer: (week) => get(`/api/fee-explainer${week ? `?week=${week}` : ''}`),
      emailSnapshot: (week) => get(`/api/email-snapshot${week ? `?week=${week}` : ''}`),
      anomalies: (week) => get(`/api/anomalies${week ? `?week=${week}` : ''}`),
      decision: (week) => get(`/api/decision${week ? `?week=${week}` : ''}`),
      themeDrilldown: (id, week, lang) => {
        const params = new URLSearchParams()
        if (week) params.set('week', week)
        if (lang) params.set('lang', lang)
        const q = params.toString()
        return get(`/api/theme/${id}${q ? `?${q}` : ''}`)
      },
      triggerRun: (week) => post('/api/run', { week }),
      approveGate: (gate, week) => post('/api/mcp/approve', { gate, week }),
    }
