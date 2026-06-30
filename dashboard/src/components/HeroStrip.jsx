import { TrendingUp, TrendingDown, AlertTriangle, Languages } from 'lucide-react'

// Top-of-page status strip — the "what changed since last week" signal.
export default function HeroStrip({ data, anomalies }) {
  const lang = data.language_breakdown ?? {}
  const nonEnglish = (lang.hi ?? 0) + (lang.hinglish ?? 0)
  const total = (lang.en ?? 0) + nonEnglish
  const nonEnPct = total > 0 ? Math.round((nonEnglish / total) * 100) : 0

  const critical = (anomalies ?? []).filter(a => a.severity === 'CRITICAL').length
  const major = (anomalies ?? []).filter(a => a.severity === 'MAJOR').length
  const drops = (anomalies ?? []).filter(a => a.kind === 'drop').length
  const sentiment = data.sentiment ?? {}

  return (
    <div className="bg-gradient-to-r from-ink-900 to-ink-800 text-white rounded-2xl px-6 py-4 mb-4 flex items-center gap-8">
      <Stat
        label="Sentiment"
        value={`${sentiment.pos ?? 0}% positive`}
        delta={null}
        Icon={sentiment.pos >= 60 ? TrendingUp : TrendingDown}
        positive={sentiment.pos >= 60}
      />
      <Divider />
      <Stat
        label="Anomalies this week"
        value={String((critical + major + drops) || 0)}
        sub={`${critical + major} flagged · ${drops} resolved`}
        Icon={AlertTriangle}
        positive={critical + major === 0}
      />
      <Divider />
      <Stat
        label="Non-English reviews"
        value={`${nonEnPct}%`}
        sub={`${lang.hinglish ?? 0} Hinglish · ${lang.hi ?? 0} Hindi`}
        Icon={Languages}
        positive={true}
      />
    </div>
  )
}

function Divider() {
  return <span className="w-px h-10 bg-white/10" />
}

function Stat({ label, value, sub, Icon, positive }) {
  return (
    <div className="flex items-center gap-3">
      <Icon size={20} className={positive ? 'text-emerald-400' : 'text-amber-400'} />
      <div>
        <div className="text-[10px] uppercase tracking-widest text-white/50">{label}</div>
        <div className="text-lg font-semibold tabular-nums">{value}</div>
        {sub && <div className="text-[11px] text-white/60">{sub}</div>}
      </div>
    </div>
  )
}
