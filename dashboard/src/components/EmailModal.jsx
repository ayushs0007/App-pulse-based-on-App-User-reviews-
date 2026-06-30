import { useEffect, useState } from 'react'
import { X, Send, FileText } from 'lucide-react'
import { api } from '../api'

export default function EmailModal({ week, onClose }) {
  const [snap, setSnap] = useState(null)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    api.emailSnapshot(week).then(setSnap)
  }, [week])

  async function approve(gate) {
    setStatus('working')
    try {
      const res = await api.approveGate(gate, week)
      setStatus(`done: ${gate}`)
      console.log(res)
    } catch (e) {
      setStatus(`error: ${e.message}`)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-6">
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full overflow-hidden">
        <div className="px-5 py-4 border-b flex items-center justify-between">
          <h3 className="font-semibold">Email Snapshot</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700"><X size={18} /></button>
        </div>
        {snap && (
          <div className="px-5 py-4 max-h-[60vh] overflow-y-auto">
            <p className="text-xs text-gray-500">To: <span className="text-gray-700">{snap.to}</span></p>
            <p className="text-xs text-gray-500">Subject: <span className="text-gray-700">{snap.subject}</span></p>
            <hr className="my-3" />
            <div className="prose prose-sm" dangerouslySetInnerHTML={{ __html: snap.html }} />
          </div>
        )}
        <div className="px-5 py-3 border-t bg-gray-50 flex items-center justify-between">
          <span className="text-xs text-gray-500">
            {status ?? 'Both gates require explicit approval before any side-effect.'}
          </span>
          <div className="flex gap-2">
            <button onClick={() => approve('doc')} className="text-xs bg-white border border-gray-200 px-3 py-1.5 rounded-lg flex items-center gap-1 hover:bg-gray-50">
              <FileText size={14} /> Append to Doc
            </button>
            <button onClick={() => approve('email')} className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded-lg flex items-center gap-1 hover:bg-blue-700">
              <Send size={14} /> Create Gmail Draft
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
