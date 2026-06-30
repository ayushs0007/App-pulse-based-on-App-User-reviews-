import { AlertCircle, Sparkles, CheckCircle2, ArrowDown } from 'lucide-react'

const KIND_META = {
  spike:    { Icon: AlertCircle,  color: 'text-red-500',     bar: 'bg-red-100' },
  emerging: { Icon: Sparkles,     color: 'text-amber-500',   bar: 'bg-amber-100' },
  drop:     { Icon: ArrowDown,    color: 'text-emerald-500', bar: 'bg-emerald-100' },
  resolved: { Icon: CheckCircle2, color: 'text-emerald-500', bar: 'bg-emerald-100' },
}

const SEV_BADGE = {
  CRITICAL: 'bg-red-100 text-red-700 border-red-200',
  MAJOR:    'bg-orange-100 text-orange-700 border-orange-200',
  INFO:     'bg-emerald-100 text-emerald-700 border-emerald-200',
}

export default function AnomalyInbox({ anomalies }) {
  const list = anomalies ?? []
  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold">Anomaly Inbox</h2>
        <span className="text-[10px] tracking-widest text-gray-400 bg-gray-50 px-2 py-0.5 rounded-full">
          {list.length} signals
        </span>
      </div>
      {list.length === 0 ? (
        <p className="text-sm text-gray-500">No notable changes vs last week. 🙌</p>
      ) : (
        <ul className="space-y-2">
          {list.slice(0, 6).map((a, i) => {
            const meta = KIND_META[a.kind] ?? KIND_META.spike
            const { Icon } = meta
            return (
              <li key={i} className="flex items-start gap-3 group">
                <span className={`mt-0.5 ${meta.color}`}><Icon size={16} /></span>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-gray-800">{a.label}</span>
                    <span className={`text-[9px] uppercase tracking-wider border px-1.5 py-0.5 rounded ${SEV_BADGE[a.severity]}`}>
                      {a.severity}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 mt-0.5">{a.note}</p>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
