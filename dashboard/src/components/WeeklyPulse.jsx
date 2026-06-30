import { useState } from 'react'
import { Calendar, CheckCircle2, Mail, Star, TrendingUp, ChevronRight, ArrowUpRight, ArrowDownRight, Sparkles } from 'lucide-react'
import EmailModal from './EmailModal.jsx'
import HeroStrip from './HeroStrip.jsx'
import DecisionCard from './DecisionCard.jsx'
import AnomalyInbox from './AnomalyInbox.jsx'
import ConfidencePill from './ConfidencePill.jsx'
import ThemeDrilldown from './ThemeDrilldown.jsx'

const SEVERITY_COLORS = {
  CRITICAL: 'bg-red-100 text-red-700 border-red-200',
  MAJOR:    'bg-orange-100 text-orange-700 border-orange-200',
  INFO:     'bg-emerald-100 text-emerald-700 border-emerald-200',
}

const CLUSTER_BAR = ['bg-red-400', 'bg-emerald-400', 'bg-amber-400', 'bg-blue-400', 'bg-purple-400']

export default function WeeklyPulse({ data }) {
  const [showEmail, setShowEmail] = useState(false)
  const [drillId, setDrillId] = useState(null)
  const {
    week_label, total, sentiment, avg_rating,
    clusters = [], pulse = {}, feedback = [],
    anomalies = [], decision = {}, language_breakdown = {},
  } = data
  const maxSize = Math.max(1, ...clusters.map(c => c.size))
  const weekRange = formatWeekRange(week_label)

  return (
    <>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-ink-900">Weekly review — {week_label}</h1>
          <div className="mt-3 flex gap-2 items-center">
            <span className="inline-flex items-center gap-1 text-emerald-700 bg-emerald-50 border border-emerald-200 text-xs px-3 py-1 rounded-full">
              <CheckCircle2 size={14} /> Completed
            </span>
            {data.baseline_week_label && (
              <span className="text-xs text-gray-500">vs. baseline {data.baseline_week_label}</span>
            )}
            <button
              onClick={() => setShowEmail(true)}
              className="inline-flex items-center gap-1 text-blue-700 bg-blue-50 border border-blue-200 text-xs px-3 py-1 rounded-full hover:bg-blue-100"
            >
              <Mail size={14} /> View Email Snapshot
            </button>
          </div>
        </div>
        <div className="inline-flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700">
          <Calendar size={16} className="text-gray-400" />
          {weekRange}
        </div>
      </div>

      {/* NEW: Hero strip — what changed since last week */}
      <HeroStrip data={data} anomalies={anomalies} />

      {/* NEW: Decision card + Anomaly inbox row */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <DecisionCard decision={decision} week={week_label} />
        <AnomalyInbox anomalies={anomalies} />
      </div>

      {/* Stat trio */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <Card>
          <p className="text-[11px] tracking-widest text-gray-400 uppercase">Total Reviews</p>
          <div className="text-4xl font-extrabold mt-3 tabular-nums">{total}</div>
          <p className="mt-3 text-sm text-emerald-600 flex items-center gap-1">
            <TrendingUp size={14} /> Analyzed this week
          </p>
        </Card>

        <Card>
          <p className="text-[11px] tracking-widest text-gray-400 uppercase">Sentiment</p>
          <div className="flex gap-8 mt-3">
            <SentimentBlock pct={sentiment.neg} label="NEG" color="text-red-500" />
            <SentimentBlock pct={sentiment.neu} label="NEU" color="text-amber-500" />
            <SentimentBlock pct={sentiment.pos} label="POS" color="text-emerald-500" />
          </div>
          <div className="mt-3 h-2 rounded-full overflow-hidden flex">
            <div className="bar-grad-neg" style={{ width: `${sentiment.neg}%` }} />
            <div className="bar-grad-neu" style={{ width: `${sentiment.neu}%` }} />
            <div className="bar-grad-pos" style={{ width: `${sentiment.pos}%` }} />
          </div>
        </Card>

        <Card>
          <p className="text-[11px] tracking-widest text-gray-400 uppercase">Avg Rating (Sentiment)</p>
          <div className="mt-3 flex items-end gap-2">
            <div className="text-4xl font-extrabold tabular-nums">{avg_rating}</div>
            <Stars score={avg_rating} />
          </div>
          <p className="mt-3 text-xs text-gray-500">
            EN {language_breakdown.en ?? 0} · Hinglish {language_breakdown.hinglish ?? 0} · Hindi {language_breakdown.hi ?? 0}
          </p>
        </Card>
      </div>

      {/* Theme Clusters — now with WoW deltas + confidence pills + drilldown */}
      <Card className="mb-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="w-1 h-4 bg-blue-500 rounded" />
            <h2 className="font-semibold">Theme Clusters</h2>
            <span className="text-[10px] tracking-widest text-gray-400 bg-gray-50 px-2 py-0.5 rounded-full">
              with WoW delta · click to drill in
            </span>
          </div>
          <span className="text-[10px] tracking-widest text-blue-500 bg-blue-50 px-2 py-0.5 rounded-full">Top 5</span>
        </div>
        <ol className="space-y-3">
          {clusters.slice(0, 5).map((c, i) => (
            <li key={`${c.id}-${i}`}>
              <button
                onClick={() => setDrillId(c.id)}
                className="w-full text-left flex items-center gap-3 text-sm hover:bg-gray-50 -mx-2 px-2 py-1 rounded transition"
              >
                <span className="text-gray-400 w-3">{i + 1}</span>
                <span className="flex-1 font-medium text-gray-800">{c.label}</span>
                <WowBadge cluster={c} />
                <ConfidencePill level={c.confidence} n={c.size} />
                <span className="font-semibold tabular-nums w-12 text-right">{c.size}</span>
                <ChevronRight size={14} className="text-gray-300" />
              </button>
              <div className="ml-6 h-1 mt-1 rounded-full bg-gray-100 overflow-hidden">
                <div className={`h-full ${CLUSTER_BAR[i % CLUSTER_BAR.length]}`} style={{ width: `${(c.size / maxSize) * 100}%` }} />
              </div>
            </li>
          ))}
        </ol>
      </Card>

      {/* Summary + Feedback row */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <div className="flex items-center gap-2">
            <span className="w-1 h-4 bg-emerald-500 rounded" />
            <h2 className="font-semibold">Weekly Pulse Summary</h2>
          </div>
          <p className="mt-3 text-sm text-gray-700 leading-relaxed">{pulse.summary}</p>
          {pulse.actions?.length > 0 && (
            <div className="mt-4">
              <p className="text-[10px] uppercase tracking-widest text-gray-400 mb-2">Next-up actions</p>
              <ul className="space-y-1.5">
                {pulse.actions.map((a, i) => (
                  <li key={i} className="text-xs text-gray-600 flex items-center gap-2">
                    <span className={`text-[9px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded ${a.priority === 'HIGH' ? 'bg-red-100 text-red-700' : a.priority === 'MED' ? 'bg-orange-100 text-orange-700' : 'bg-emerald-100 text-emerald-700'}`}>
                      {a.priority}
                    </span>
                    {a.text}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>

        <Card>
          <h2 className="font-semibold mb-3">Representative Feedback</h2>
          <ul className="space-y-3">
            {feedback.map((f, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="w-9 h-9 rounded-full bg-gray-100 text-gray-600 text-xs font-semibold flex items-center justify-center">
                  {f.initials}
                </span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-semibold">{f.user}</span>
                    <span className={`text-[10px] uppercase tracking-wider border px-1.5 py-0.5 rounded ${SEVERITY_COLORS[f.severity]}`}>
                      {f.severity}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 mt-1 line-clamp-2">"{f.text}"</p>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {showEmail && <EmailModal week={week_label} onClose={() => setShowEmail(false)} />}
      {drillId !== null && <ThemeDrilldown clusterId={drillId} week={week_label} onClose={() => setDrillId(null)} />}
    </>
  )
}

function WowBadge({ cluster }) {
  const kind = cluster.wow_kind
  const pct = cluster.wow_pct
  if (kind === 'emerging') {
    return (
      <span className="text-[10px] uppercase tracking-wider border bg-amber-50 text-amber-700 border-amber-200 px-1.5 py-0.5 rounded flex items-center gap-0.5">
        <Sparkles size={10} /> NEW
      </span>
    )
  }
  if (kind === 'spike' && typeof pct === 'number') {
    return (
      <span className="text-[10px] uppercase tracking-wider border bg-red-50 text-red-700 border-red-200 px-1.5 py-0.5 rounded flex items-center gap-0.5">
        <ArrowUpRight size={10} /> +{pct}%
      </span>
    )
  }
  if (kind === 'drop' && typeof pct === 'number') {
    return (
      <span className="text-[10px] uppercase tracking-wider border bg-emerald-50 text-emerald-700 border-emerald-200 px-1.5 py-0.5 rounded flex items-center gap-0.5">
        <ArrowDownRight size={10} /> {pct}%
      </span>
    )
  }
  if (typeof pct === 'number') {
    const sign = pct >= 0 ? '+' : ''
    return (
      <span className="text-[10px] uppercase tracking-wider border bg-gray-50 text-gray-500 border-gray-200 px-1.5 py-0.5 rounded">
        {sign}{pct}%
      </span>
    )
  }
  return null
}

function Card({ children, className = '' }) {
  return <div className={`bg-white rounded-2xl border border-gray-100 p-5 shadow-sm ${className}`}>{children}</div>
}
function SentimentBlock({ pct, label, color }) {
  return (
    <div className="flex flex-col">
      <span className={`text-3xl font-extrabold ${color}`}>{pct}%</span>
      <span className="text-[10px] tracking-widest text-gray-400 uppercase mt-1">{label}</span>
    </div>
  )
}
function Stars({ score }) {
  return (
    <div className="flex gap-0.5 pb-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star key={n} size={12} className={n <= Math.round(score) ? 'fill-amber-400 text-amber-400' : 'text-gray-200'} />
      ))}
    </div>
  )
}
function formatWeekRange(label) {
  if (!label) return ''
  const m = /^(\d{4})-W(\d{2})$/.exec(label)
  if (!m) return label
  const [, y, w] = m
  const year = parseInt(y, 10)
  const week = parseInt(w, 10)
  const jan4 = new Date(Date.UTC(year, 0, 4))
  const dayOfWeek = jan4.getUTCDay() || 7
  const monday = new Date(jan4)
  monday.setUTCDate(jan4.getUTCDate() - dayOfWeek + 1 + (week - 1) * 7)
  const sunday = new Date(monday)
  sunday.setUTCDate(monday.getUTCDate() + 6)
  const fmt = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return `${fmt(monday)} – ${fmt(sunday)}, ${year}`
}
