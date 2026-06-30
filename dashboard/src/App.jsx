import { useEffect, useState } from 'react'
import { api } from './api'
import Sidebar from './components/Sidebar.jsx'
import WeeklyPulse from './components/WeeklyPulse.jsx'
import FeeExplainer from './components/FeeExplainer.jsx'
import RunHistory from './components/RunHistory.jsx'
import Settings from './components/Settings.jsx'

export default function App() {
  const [tab, setTab] = useState('pulse')
  const [data, setData] = useState(null)
  const [runs, setRuns] = useState([])
  const [week, setWeek] = useState(null)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([api.weekly(week), api.runs()])
      .then(([d, r]) => { setData(d); setRuns(r); setErr(null) })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [week])

  return (
    <div className="flex min-h-screen">
      <Sidebar
        tab={tab}
        setTab={setTab}
        weeks={runs}
        currentWeek={week ?? data?.week_label}
        onWeekChange={setWeek}
      />
      <main className="flex-1 px-10 py-8 overflow-y-auto">
        {loading && <p className="text-gray-500">Loading…</p>}
        {err && (
          <div className="bg-red-50 border border-red-200 text-red-800 rounded-xl p-4">
            <p className="font-semibold">Could not load data.</p>
            <p className="text-sm mt-1">{err}</p>
            <p className="text-sm mt-2">
              Run the pipeline once to seed data:{' '}
              <code className="bg-red-100 px-1 rounded">python -m pipeline.run_weekly</code>
            </p>
          </div>
        )}
        {!loading && !err && data && (
          <>
            {tab === 'pulse' && <WeeklyPulse data={data} />}
            {tab === 'fee'   && <FeeExplainer week={data.week_label} />}
            {tab === 'runs'  && <RunHistory runs={runs} onPick={setWeek} />}
            {tab === 'settings' && <Settings />}
          </>
        )}
      </main>
    </div>
  )
}
