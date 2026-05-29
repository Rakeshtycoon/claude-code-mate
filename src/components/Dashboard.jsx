import { useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { todayISO, formatMoney } from '../lib/format.js'
import { QuoteRotator, Slideshow } from './Inspiration.jsx'

const GOAL_CATS = ['business', 'finance', 'family', 'health', 'pa', 'crazy']

export default function Dashboard({ onNavigate }) {
  const [slideshow, setSlideshow] = useState(false)
  const [profile] = useLocalStorage('bd.profile', {})
  const [goals] = useLocalStorage('bd.goals', {})
  const [days] = useLocalStorage('bd.days', {})
  const [plans] = useLocalStorage('bd.monthlyPlans', {})

  const date = todayISO()
  const day = days[date]
  const month = date.slice(0, 7)
  const plan = plans[month]

  // Goal status counts.
  let total = 0
  let done = 0
  for (const cat of GOAL_CATS) {
    for (const g of goals[cat] || []) {
      total++
      if (g.status === 'ok') done++
    }
  }

  // Today's mantras + tasks.
  const mantrasDone = day ? Object.values(day.mantras || {}).filter(Boolean).length : 0
  const taskCount = day
    ? Object.values(day.lists || {}).reduce((n, arr) => n + (arr?.length || 0), 0)
    : 0
  const tasksDone = day
    ? Object.values(day.lists || {}).reduce(
        (n, arr) => n + (arr || []).filter((t) => t.done).length,
        0
      )
    : 0

  const greeting = (() => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 17) return 'Good afternoon'
    return 'Good evening'
  })()

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>
            {greeting}
            {profile.name ? `, ${profile.name.split(' ')[0]}` : ''} 👋
          </h1>
          <p className="muted">
            {new Date().toLocaleDateString(undefined, {
              weekday: 'long',
              month: 'long',
              day: 'numeric',
              year: 'numeric',
            })}
          </p>
        </div>
      </header>

      {profile.vision && (
        <div className="card vision-card">
          <span className="vision-label">Vision</span>
          <p>{profile.vision}</p>
        </div>
      )}

      <QuoteRotator onOpen={() => setSlideshow(true)} />
      {slideshow && <Slideshow onClose={() => setSlideshow(false)} />}

      <div className="stat-grid">
        <button className="card stat clickable" onClick={() => onNavigate('daily')}>
          <span className="stat-label">Morning Mantras today</span>
          <span className="stat-value">{mantrasDone}/8</span>
        </button>
        <button className="card stat clickable" onClick={() => onNavigate('daily')}>
          <span className="stat-label">Today's tasks</span>
          <span className="stat-value">
            {tasksDone}/{taskCount}
          </span>
        </button>
        <button className="card stat clickable income" onClick={() => onNavigate('goals')}>
          <span className="stat-label">Goals completed</span>
          <span className="stat-value">
            {done}/{total}
          </span>
        </button>
        <button className="card stat clickable" onClick={() => onNavigate('monthly')}>
          <span className="stat-label">Month sales target</span>
          <span className="stat-value">
            {plan?.target?.sales ? formatMoney(plan.target.sales) : '—'}
          </span>
        </button>
      </div>

      <div className="card quick-links">
        <h3 className="list-title">Jump back in</h3>
        <div className="link-row">
          <button className="btn" onClick={() => onNavigate('daily')}>
            📔 Today's page
          </button>
          <button className="btn" onClick={() => onNavigate('goals')}>
            🎯 Review goals
          </button>
          <button className="btn" onClick={() => onNavigate('monthly')}>
            📈 Monthly plan
          </button>
          <button className="btn" onClick={() => onNavigate('planner')}>
            🗓️ Planner
          </button>
        </div>
      </div>
    </div>
  )
}
