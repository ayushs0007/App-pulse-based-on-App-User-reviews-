import { useEffect, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { api } from '../api'

export default function FeeExplainer({ week }) {
  const [data, setData] = useState(null)
  useEffect(() => { api.feeExplainer(week).then(setData) }, [week])
  if (!data) return <p className="text-gray-500">Loading…</p>

  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="col-span-2 bg-white rounded-2xl border border-gray-100 p-6">
        <h1 className="text-2xl font-bold">Fee Explainer</h1>
        <p className="text-sm text-gray-500 mt-1">
          Insight-driven explanation generated from {data.matched ?? 0} fee-related reviews this week.
        </p>
        <ol className="mt-5 space-y-3 list-decimal pl-5">
          {data.bullets?.map((b, i) => <li key={i} className="text-sm text-gray-700 leading-relaxed">{b}</li>)}
        </ol>
      </div>
      <div className="bg-white rounded-2xl border border-gray-100 p-6">
        <h2 className="font-semibold">Sources</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {data.sources?.map((s, i) => (
            <li key={i}>
              <a href={s.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline inline-flex items-center gap-1">
                <ExternalLink size={12} /> {s.title}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
