export default function RunHistory({ runs, onPick }) {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Run History</h1>
      <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-[10px] uppercase tracking-widest text-gray-500">
            <tr>
              <th className="text-left px-4 py-3">Week</th>
              <th className="text-left px-4 py-3">Generated</th>
              <th className="text-left px-4 py-3">Reviews</th>
              <th className="text-left px-4 py-3">Top theme</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.week_label} className="border-t border-gray-100">
                <td className="px-4 py-3 font-semibold">{r.week_label}</td>
                <td className="px-4 py-3 text-gray-500">{new Date(r.generated_at).toLocaleString()}</td>
                <td className="px-4 py-3 tabular-nums">{r.total}</td>
                <td className="px-4 py-3 text-gray-700">{r.themes[0]}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => onPick(r.week_label)} className="text-xs text-blue-600 hover:underline">Open</button>
                </td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr><td colSpan="5" className="px-4 py-6 text-center text-gray-500">No runs yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
