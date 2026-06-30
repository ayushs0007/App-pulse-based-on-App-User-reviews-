import { useEffect, useState } from 'react'
import { X, Star } from 'lucide-react'
import { api } from '../api'

const LANG_PILLS = {
  en:      { label: 'EN',  color: 'bg-gray-100 text-gray-600' },
  hinglish:{ label: 'HING',color: 'bg-amber-50 text-amber-700' },
  hi:      { label: 'HI',  color: 'bg-pink-50 text-pink-700' },
}

export default function ThemeDrilldown({ clusterId, week, onClose }) {
  const [data, setData] = useState(null)
  const [lang, setLang] = useState(null)

  useEffect(() => {
    if (clusterId == null) return
    api.themeDrilldown(clusterId, week, lang).then(setData)
  }, [clusterId, week, lang])

  if (clusterId == null) return null

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-6">
      <div className="bg-white rounded-2xl shadow-xl max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        <div className="px-5 py-4 border-b flex items-center justify-between">
          <div>
            <h3 className="font-semibold">{data?.label ?? '…'}</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {data ? `${data.total_in_cluster} reviews in this theme` : 'Loading…'}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700"><X size={18} /></button>
        </div>

        <div className="px-5 py-2 border-b flex gap-2 text-xs">
          {[null, 'en', 'hinglish', 'hi'].map((opt) => (
            <button
              key={String(opt)}
              onClick={() => setLang(opt)}
              className={`px-2 py-1 rounded ${lang === opt ? 'bg-blue-600 text-white' : 'border border-gray-200 text-gray-600 hover:bg-gray-50'}`}
            >
              {opt ? LANG_PILLS[opt].label : 'All'}
            </button>
          ))}
        </div>

        <div className="px-5 py-4 overflow-y-auto flex-1">
          {data?.reviews?.map((r) => (
            <div key={r.id} className="border-b border-gray-50 py-3 last:border-b-0">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold">{r.user || 'Anonymous'}</span>
                <span className="flex gap-0.5">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <Star key={n} size={10} className={n <= (r.rating || 0) ? 'fill-amber-400 text-amber-400' : 'text-gray-200'} />
                  ))}
                </span>
                {r.lang && (
                  <span className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded ${LANG_PILLS[r.lang]?.color}`}>
                    {LANG_PILLS[r.lang]?.label}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-700 mt-1 leading-relaxed">{r.text}</p>
            </div>
          ))}
          {data?.reviews?.length === 0 && <p className="text-sm text-gray-500">No reviews in this filter.</p>}
        </div>
      </div>
    </div>
  )
}
