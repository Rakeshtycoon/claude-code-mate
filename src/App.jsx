import { useEffect, useState } from 'react'
import Dashboard from './components/Dashboard.jsx'
import Profile from './components/Profile.jsx'
import Goals from './components/Goals.jsx'
import Daily from './components/Daily.jsx'
import Monthly from './components/Monthly.jsx'
import Planner from './components/Planner.jsx'
import Lists from './components/Lists.jsx'
import Graphs from './components/Graphs.jsx'
import Backup from './components/Backup.jsx'
import { runDailyAutoBackup } from './lib/autobackup.js'
import { useReminders } from './hooks/useReminders.js'

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'daily', label: 'Daily', icon: '📔' },
  { id: 'goals', label: 'Goals', icon: '🎯' },
  { id: 'monthly', label: 'Monthly', icon: '📈' },
  { id: 'planner', label: 'Planner', icon: '🗓️' },
  { id: 'lists', label: 'Lists', icon: '📝' },
  { id: 'graphs', label: 'Graphs', icon: '📉' },
  { id: 'profile', label: 'Profile', icon: '🧑‍💼' },
  { id: 'backup', label: 'Backup', icon: '💾' },
]

const VIEWS = {
  dashboard: (nav) => <Dashboard onNavigate={nav} />,
  daily: () => <Daily />,
  goals: () => <Goals />,
  monthly: () => <Monthly />,
  planner: () => <Planner />,
  lists: () => <Lists />,
  graphs: (nav) => <Graphs onNavigate={nav} />,
  profile: () => <Profile />,
  backup: () => <Backup />,
}

export default function App() {
  const [view, setView] = useState('dashboard')
  const [menuOpen, setMenuOpen] = useState(false)

  // Schedule reminders for timed To-Do tasks (while the app is open).
  useReminders()

  // Once per day, the first time the app opens, take an automatic backup.
  useEffect(() => {
    runDailyAutoBackup()
  }, [])

  function go(id) {
    setView(id)
    setMenuOpen(false)
  }

  return (
    <div className="app">
      <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
        <div className="brand">
          <span className="brand-mark">PA</span>
          <div>
            <div className="brand-name">Business Diary</div>
            <div className="brand-sub">I am my word.</div>
          </div>
        </div>
        <nav>
          {NAV.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${view === item.id ? 'active' : ''}`}
              onClick={() => go(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">Saved locally in your browser.</div>
      </aside>

      <div className="main-col">
        <div className="topbar">
          <button className="menu-btn" onClick={() => setMenuOpen((o) => !o)}>
            ☰
          </button>
          <span className="topbar-title">
            {NAV.find((n) => n.id === view)?.label}
          </span>
        </div>
        <main className="content">{VIEWS[view](go)}</main>
      </div>
    </div>
  )
}
