const STYLES = {
  HIGH: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  MED:  'bg-amber-50 text-amber-700 border-amber-200',
  LOW:  'bg-gray-100 text-gray-600 border-gray-200',
}

export default function ConfidencePill({ level, n }) {
  if (!level) return null
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] uppercase tracking-wider border px-1.5 py-0.5 rounded ${STYLES[level] ?? STYLES.LOW}`}>
      {level}{typeof n === 'number' ? ` · n=${n}` : ''}
    </span>
  )
}
