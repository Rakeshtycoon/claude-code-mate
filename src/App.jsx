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
import Settings from './components/Settings.jsx'
import { runDailyAutoBackup } from './lib/autobackup.js'
import { useReminders } from './hooks/useReminders.js'
import { useLocalStorage } from './hooks/useLocalStorage.js'
import { useSettings } from './hooks/useSettings.js'
import { accentColor } from './lib/settings.js'

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
  { id: 'settings', label: 'Settings', icon: '⚙️' },
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
  settings: () => <Settings />,
}

export default function App() {
  const [view, setView] = useState('dashboard')
  const [menuOpen, setMenuOpen] = useState(false)
  const [profile] = useLocalStorage('bd.profile', {})
  const [settings] = useSettings()

  // Schedule reminders for timed To-Do tasks (while the app is open).
  useReminders()

  // Apply the chosen accent colour to the whole app.
  useEffect(() => {
    document.documentElement.style.setProperty('--pa-blue', accentColor(settings.accent))
  }, [settings.accent])

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
          {profile.photo ? (
            <img className="brand-photo" src={profile.photo} alt="" />
          ) : (
            <span className="brand-mark">PA</span>
          )}
          <div>
            <div className="brand-name">{profile.name || 'Business Diary'}</div>
            <div className="brand-sub">{profile.name ? 'Business Diary' : 'I am my word.'}</div>
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
