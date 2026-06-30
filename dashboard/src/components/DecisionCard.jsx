import { Target, ArrowRight, FileText, Send } from 'lucide-react'
import ConfidencePill from './ConfidencePill.jsx'
import { api } from '../api'
import { useState } from 'react'

const KIND_COPY = {
  spike:        { tag: 'SPIKE',     color: 'bg-red-50 text-red-700 border-red-200'         },
  emerging:     { tag: 'EMERGING',  color: 'bg-amber-50 text-amber-700 border-amber-200'   },
  size:         { tag: 'TOP THEME', color: 'bg-blue-50 text-blue-700 border-blue-200'      },
  'double-down':{ tag: 'DOUBLE DOWN', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  none:         { tag: '—',         color: 'bg-gray-100 text-gray-600 border-gray-200'    },
}

export default function DecisionCard({ decision, week }) {
  const [status, setStatus] = useState(null)
  if (!decision || !decision.move) return null
  const kind = KIND_COPY[decision.kind] ?? KIND_COPY.none

  async function spawn(gate) {
    setStatus('working…')
    try {
      const r = await api.approveGate(gate, week)
      setStatus(`done · ${gate}`)
      console.log(r)
    } catch (e) { setStatus(`error: ${e.message}`) }
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Target size={16} className="text-blue-600" />
          <h2 className="font-semibold">This Week's Move</h2>
        </div>
        <div className="flex items-center gap-1">
          <span className={`text-[10px] uppercase tracking-wider border px-1.5 py-0.5 rounded ${kind.color}`}>
            {kind.tag}
          </span>
          <ConfidencePill level={decision.confidence} n={decision.addressable} />
        </div>
      </div>

      <p className="text-base font-semibold text-ink-900 mt-3 leading-snug">
        📌 {decision.move}
      </p>

      <div className="mt-3 text-sm text-gray-700 bg-gray-50 border border-gray-100 rounded-lg p-3">
        <span className="font-semibold">Why:</span> {decision.why}
      </div>

      <div className="grid grid-cols-2 gap-3 mt-3 text-xs">
        <Tile label="Estimated impact" value={decision.impact} />
        <Tile label="Suggested owner" value={decision.owner} mono />
      </div>

      <div className="mt-4 flex items-center justify-between border-t pt-3">
        <span className="text-xs text-gray-500">
          {status ?? 'Ready to action — both gates require approval before any side-effect.'}
        </span>
        <div className="flex gap-2">
          <button onClick={() => spawn('doc')} className="text-xs border border-gray-200 px-3 py-1.5 rounded-lg flex items-center gap-1 hover:bg-gray-50">
            <FileText size={13} /> Append to Doc
          </button>
          <button onClick={() => spawn('email')} className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded-lg flex items-center gap-1 hover:bg-blue-700">
            <Send size={13} /> Create Draft <ArrowRight size={13} />
          </button>
        </div>
      </div>
    </div>
  )
}

function Tile({ label, value, mono }) {
  return (
    <div className="bg-gray-50 border border-gray-100 rounded-lg p-3">
      <div className="text-[10px] uppercase tracking-widest text-gray-400 mb-1">{label}</div>
      <div className={`text-sm text-gray-800 ${mono ? 'font-mono' : ''}`}>{value || '—'}</div>
    </div>
  )
}
