export default function Settings() {
  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-bold mb-4">Settings</h1>
      <div className="bg-white rounded-2xl border border-gray-100 p-6 text-sm">
        <p className="text-gray-700">
          Environment variables live in <code>.env</code> at the repo root.
          Restart the API server after editing.
        </p>
        <ul className="mt-3 list-disc pl-5 text-gray-600 space-y-1">
          <li><code>GROQ_API_KEY</code> — LLM summarization key (optional; fallback used otherwise).</li>
          <li><code>GOOGLE_DOC_ID</code> — target Google Doc for the MCP append gate.</li>
          <li><code>GMAIL_TO</code> — recipient address for the Gmail draft gate.</li>
        </ul>
      </div>
    </div>
  )
}
