import { useEffect, useState } from 'react'
import Dashboard from './components/Dashboard.jsx'
import Profile from './components/Profile.jsx'
import Goals from './components/Goals.jsx'
import Daily from './components/Daily.jsx'
import Expenses from './components/Expenses.jsx'
import Monthly from './components/Monthly.jsx'
import Planner from './components/Planner.jsx'
import Lists from './components/Lists.jsx'
import Graphs from './components/Graphs.jsx'
import Backup from './components/Backup.jsx'
import Settings from './components/Settings.jsx'
import DeveloperMessage from './components/DeveloperMessage.jsx'
import { runDailyAutoBackup } from './lib/autobackup.js'
import { useReminders } from './hooks/useReminders.js'
import { useLocalStorage } from './hooks/useLocalStorage.js'
import { useSettings } from './hooks/useSettings.js'
import { accentColor, isLightColor, readableAccent } from './lib/settings.js'

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'daily', label: 'Daily', icon: '📔' },
  { id: 'expenses', label: 'Personal Expense', icon: '💰' },
  { id: 'monthly', label: 'Monthly', icon: '📈' },
  { id: 'goals', label: 'Goals', icon: '🎯' },
  { id: 'graphs', label: 'Graphs', icon: '📉' },
  { id: 'planner', label: 'Planner', icon: '🗓️' },
  { id: 'lists', label: 'Lists', icon: '📝' },
  { id: 'profile', label: 'Profile', icon: '🧑‍💼' },
  { id: 'backup', label: 'Backup', icon: '💾' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
]

const VIEWS = {
  dashboard: (nav) => <Dashboard onNavigate={nav} />,
  daily: () => <Daily />,
  expenses: () => <Expenses />,
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
  const [devOpen, setDevOpen] = useState(false)
  const [profile] = useLocalStorage('bd.profile', {})
  const [quotes] = useLocalStorage('bd.quotes', [])
  const [bucket] = useLocalStorage('bd.bucket', [])
  const [settings] = useSettings()

  // Schedule reminders for timed To-Do tasks (while the app is open).
  useReminders()

  // Apply the chosen accent colour. The sidebar shows the true colour (with
  // auto dark/light text), while headings use a readable, darker-if-light shade.
  useEffect(() => {
    const raw = accentColor(settings.accent)
    const light = isLightColor(raw)
    const root = document.documentElement.style
    root.setProperty('--pa-blue', readableAccent(raw))
    root.setProperty('--sidebar-bg', raw)
    root.setProperty('--side-text', light ? 'rgba(15,23,42,0.88)' : '#e2e8f0')
    root.setProperty('--side-strong', light ? '#0f172a' : '#ffffff')
    root.setProperty('--side-muted', light ? 'rgba(15,23,42,0.62)' : '#c7d2fe')
    root.setProperty('--side-hover', light ? 'rgba(0,0,0,0.08)' : 'rgba(255,255,255,0.10)')
    root.setProperty('--side-active-text', light ? '#0f172a' : readableAccent(raw))
  }, [settings.accent])

  // Once per day, the first time the app opens, take an automatic backup.
  useEffect(() => {
    runDailyAutoBackup()
  }, [])

  // Feed the Android home-screen widget: empowering quotes + bucket-list
  // lines and the on/off flag, via Capacitor Preferences (SharedPreferences).
  useEffect(() => {
    const Cap = typeof window !== 'undefined' ? window.Capacitor : undefined
    if (!Cap?.isNativePlatform?.()) return
    const P = Cap.Plugins?.Preferences
    if (!P) return
    const lines = []
    for (const q of quotes || []) {
      const t = (q.text || '').trim()
      if (t) lines.push(t)
    }
    for (const b of bucket || []) {
      const t = (b.text || '').trim()
      if (t) lines.push(t)
    }
    P.set({ key: 'widgetLines', value: JSON.stringify(lines) })
    P.set({ key: 'widgetEnabled', value: settings.widget ? 'true' : 'false' })
  }, [quotes, bucket, settings.widget])

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
            <img className="brand-photo brand-logo" src={`${import.meta.env.BASE_URL}icon.svg`} alt="" />
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
        <button className="sidebar-foot dev-link" type="button" onClick={() => setDevOpen(true)}>
          💬 Developer’s Message
        </button>
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

      {devOpen && <DeveloperMessage onClose={() => setDevOpen(false)} />}
    </div>
  )
}
