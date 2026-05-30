import { useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { todayISO, formatMoney, compactNumber } from '../lib/format.js'
import { QuoteRotator, Slideshow } from './Inspiration.jsx'
import BarChart from './charts/BarChart.jsx'
import DonutChart from './charts/DonutChart.jsx'

const GOAL_STATUS = [
  { key: 'toStart', name: 'To Start', color: '#9ca3af' },
  { key: 'ok', name: 'OK', color: '#16a34a' },
  { key: 'delay', name: 'Delay', color: '#d97706' },
  { key: 'stuck', name: 'Stuck', color: '#dc2626' },
  { key: 'cancel', name: 'Cancel', color: '#64748b' },
]

const GOAL_CATS = [
  { key: 'business', label: 'Business' },
  { key: 'finance', label: 'Finance' },
  { key: 'family', label: 'Family' },
  { key: 'health', label: 'Health' },
  { key: 'pa', label: 'PA' },
  { key: 'crazy', label: 'Crazy' },
]

const num = (v) => Number(v) || 0

export default function Dashboard({ onNavigate }) {
  const [slideshow, setSlideshow] = useState(false)
  const [profile] = useLocalStorage('bd.profile', {})
  const [goals] = useLocalStorage('bd.goals', {})
  const [days] = useLocalStorage('bd.days', {})
  const [plans] = useLocalStorage('bd.monthlyPlans', {})
  const [salesAnalysis] = useLocalStorage('bd.salesAnalysis', {})

  const date = todayISO()
  const day = days[date]
  const month = date.slice(0, 7)
  const plan = plans[month]

  // Goal status counts + per-category progress for the chart.
  let total = 0
  let done = 0
  const goalsByCat = GOAL_CATS.map((cat) => {
    const list = goals[cat.key] || []
    const ok = list.filter((g) => g.status === 'ok').length
    total += list.length
    done += ok
    return { label: cat.label, ok, total: list.length }
  })

  // Monthly comparison: This Year vs Last Year vs Target (sales & profit).
  const monthlyData = [
    {
      label: 'Sales',
      bars: [
        { name: 'Last Year', value: num(plan?.lastYear?.sales), color: '#94a3b8' },
        { name: 'This Year', value: num(plan?.thisYear?.sales), color: '#2563eb' },
        { name: 'Target', value: num(plan?.target?.sales), color: '#fbbf24' },
      ],
    },
    {
      label: 'Profit',
      bars: [
        { name: 'Last Year', value: num(plan?.lastYear?.profit), color: '#94a3b8' },
        { name: 'This Year', value: num(plan?.thisYear?.profit), color: '#2563eb' },
        { name: 'Target', value: num(plan?.target?.profit), color: '#fbbf24' },
      ],
    },
  ]

  // Daily comparison: Sales Target vs Achieved over the last 7 days.
  const last7 = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const key = d.toISOString().slice(0, 10)
    const dd = days[key]
    last7.push({
      label: String(d.getDate()),
      bars: [
        { name: 'Target', value: num(dd?.today?.salesTarget), color: '#93c5fd' },
        { name: 'Achieved', value: num(dd?.today?.salesAchieved), color: '#ea580c' },
      ],
    })
  }

  // Daily comparison: Collection Target vs Achieved over the last 7 days.
  const collection7 = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const dd = days[d.toISOString().slice(0, 10)]
    collection7.push({
      label: String(d.getDate()),
      bars: [
        { name: 'Target', value: num(dd?.today?.collTarget), color: '#a7f3d0' },
        { name: 'Achieved', value: num(dd?.today?.collAchieved), color: '#0d9488' },
      ],
    })
  }

  // Sales Analysis: 12 months (financial year Apr→Mar) Target vs Achieved.
  const fyYear = new Date().getFullYear()
  const salesYearData = []
  for (let i = 0; i < 12; i++) {
    const m = (3 + i) % 12
    const y = 3 + i < 12 ? fyYear : fyYear + 1
    const row = salesAnalysis[`${y}-${String(m + 1).padStart(2, '0')}`] || {}
    salesYearData.push({
      label: new Date(y, m, 1).toLocaleDateString(undefined, { month: 'short' }),
      bars: [
        { name: 'Target', value: num(row.target), color: '#93c5fd' },
        { name: 'Achieved', value: num(row.achieved), color: '#16a34a' },
      ],
    })
  }

  // Goals status breakdown for the donut.
  const statusCounts = {}
  for (const cat of GOAL_CATS) {
    for (const g of goals[cat.key] || []) {
      statusCounts[g.status] = (statusCounts[g.status] || 0) + 1
    }
  }
  const donutData = GOAL_STATUS.map((s) => ({
    name: s.name,
    value: statusCounts[s.key] || 0,
    color: s.color,
  })).filter((d) => d.value > 0)

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

      <section className="card">
        <div className="chart-head">
          <h3 className="list-title">📈 Monthly comparison — {new Date().toLocaleDateString(undefined, { month: 'long' })}</h3>
          <button className="btn small" onClick={() => onNavigate('monthly')}>
            Edit
          </button>
        </div>
        <BarChart data={monthlyData} format={compactNumber} />
      </section>

      <section className="card">
        <div className="chart-head">
          <h3 className="list-title">📊 Sales Analysis — 12 months (Target vs Achieved)</h3>
          <button className="btn small" onClick={() => onNavigate('monthly')}>
            Edit
          </button>
        </div>
        <BarChart data={salesYearData} format={compactNumber} scrollable />
      </section>

      <section className="card">
        <div className="chart-head">
          <h3 className="list-title">🎯 Goals progress by category</h3>
          <button className="btn small" onClick={() => onNavigate('goals')}>
            Edit
          </button>
        </div>
        {total === 0 ? (
          <p className="chart-empty">No goals yet — add some in the Goals tab.</p>
        ) : (
          <div className="goal-progress">
            {goalsByCat.map((c) => {
              const pct = c.total ? Math.round((c.ok / c.total) * 100) : 0
              return (
                <div key={c.label} className="gp-row">
                  <span className="gp-label">{c.label}</span>
                  <span className="gp-track">
                    <span className="gp-fill" style={{ width: `${pct}%` }} />
                  </span>
                  <span className="gp-count">
                    {c.ok}/{c.total}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </section>

      <section className="card">
        <div className="chart-head">
          <h3 className="list-title">🍩 Goals by status</h3>
          <button className="btn small" onClick={() => onNavigate('goals')}>
            Edit
          </button>
        </div>
        <DonutChart data={donutData} centerLabel="goals" />
      </section>

      <section className="card">
        <div className="chart-head">
          <h3 className="list-title">📅 Daily sales — Target vs Achieved (last 7 days)</h3>
          <button className="btn small" onClick={() => onNavigate('daily')}>
            Edit
          </button>
        </div>
        <BarChart data={last7} format={compactNumber} />
      </section>

      <section className="card">
        <div className="chart-head">
          <h3 className="list-title">💵 Daily collection — Target vs Achieved (last 7 days)</h3>
          <button className="btn small" onClick={() => onNavigate('daily')}>
            Edit
          </button>
        </div>
        <BarChart data={collection7} format={compactNumber} />
      </section>

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
