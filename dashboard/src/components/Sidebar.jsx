import { BarChart3, FileText, History, Settings as SettingsIcon, ChevronLeft, User, ChevronDown } from 'lucide-react'

const TABS = [
  { id: 'pulse',    label: 'Weekly Pulse',   Icon: BarChart3 },
  { id: 'fee',      label: 'Fee Explainer',  Icon: FileText },
  { id: 'runs',     label: 'Run History',    Icon: History },
  { id: 'settings', label: 'Settings',       Icon: SettingsIcon },
]

export default function Sidebar({ tab, setTab, weeks, currentWeek, onWeekChange }) {
  return (
    <aside className="w-64 bg-[#0e1729] text-white flex flex-col">
      <div className="px-6 pt-8 pb-10 flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-groww-500 flex items-center justify-center font-bold text-ink-900">G</div>
        <div className="text-xl font-semibold">Groww</div>
      </div>

      <nav className="flex-1 px-3 space-y-1">
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm transition ${
              tab === id ? 'bg-white/10 text-white' : 'text-white/70 hover:bg-white/5'
            }`}
          >
            <Icon size={18} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div className="px-3 pb-2">
        <div className="px-4 pb-1 text-[10px] tracking-widest text-white/40 uppercase">Review Week</div>
        <div className="relative">
          <select
            value={currentWeek ?? ''}
            onChange={(e) => onWeekChange(e.target.value)}
            className="appearance-none w-full bg-white/5 border border-white/10 text-sm rounded-lg px-4 py-2.5 pr-9 focus:outline-none"
          >
            {weeks.length === 0 && currentWeek && (
              <option value={currentWeek}>{currentWeek}</option>
            )}
            {weeks.map((w) => (
              <option key={w.week_label} value={w.week_label}>{w.week_label}</option>
            ))}
          </select>
          <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-white/50 pointer-events-none" />
        </div>
      </div>

      <div className="border-t border-white/10 px-3 py-3">
        <button className="w-full flex items-center gap-2 text-xs text-white/60 hover:text-white px-3 py-2">
          <ChevronLeft size={14} /> Collapse
        </button>
        <div className="px-3 py-2 flex items-center gap-3 text-sm text-white/80">
          <User size={16} /> Profile
        </div>
      </div>
    </aside>
  )
}
