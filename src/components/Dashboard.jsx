import { useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { useSettings } from '../hooks/useSettings.js'
import { todayISO, formatMoney, compactNumber } from '../lib/format.js'
import { monthAchieved } from '../lib/totals.js'
import { QuoteRotator, Slideshow } from './Inspiration.jsx'
import ProgressRing from './charts/ProgressRing.jsx'
import BarChart from './charts/BarChart.jsx'

const rupee = (v) => `₹${compactNumber(v)}`

const GOAL_CATS = ['business', 'finance', 'family', 'health', 'pa', 'crazy']

function lastYearMonth(ym) {
  const [y, m] = ym.split('-')
  return `${Number(y) - 1}-${m}`
}

const num = (v) => Number(v) || 0
const pct = (a, t) => (num(t) ? Math.round((num(a) / num(t)) * 100) : null)

export default function Dashboard({ onNavigate }) {
  const [slideshow, setSlideshow] = useState(false)
  const [profile] = useLocalStorage('bd.profile', {})
  const [goals] = useLocalStorage('bd.goals', {})
  const [days] = useLocalStorage('bd.days', {})
  const [plans] = useLocalStorage('bd.monthlyPlans', {})
  const [actuals] = useLocalStorage('bd.monthlyActuals', {})
  const [expenses] = useLocalStorage('bd.expenses', {})
  const [settings] = useSettings()

  const date = todayISO()
  const day = days[date]
  const month = date.slice(0, 7)
  const plan = plans[month]

  // This-month performance, rolled up from the Daily page.
  const ach = monthAchieved(days, month)
  const salesTarget = plan?.target?.sales
  const collTarget = plan?.target?.collection
  const salesPct = pct(ach.sales, salesTarget)
  const collPct = pct(ach.collection, collTarget)
  const lastYearSales = actuals[lastYearMonth(month)]?.sales
  const growth =
    num(lastYearSales) && num(ach.sales)
      ? Math.round(((num(ach.sales) - num(lastYearSales)) / num(lastYearSales)) * 100)
      : null
  const monthName = new Date().toLocaleDateString(undefined, { month: 'long' })

  // This month's total personal expense.
  let monthExpense = 0
  for (const [d, items] of Object.entries(expenses)) {
    if (d.slice(0, 7) !== month) continue
    for (const e of items || []) monthExpense += num(e.amount)
  }

  // Last 7 days of achieved sales, as daily bars.
  const sales7 = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const iso = d.toISOString().slice(0, 10)
    const value = num(days[iso]?.today?.salesAchieved)
    sales7.push({
      label: String(d.getDate()),
      bars: [{ name: 'Sales', value, color: '#ea580c' }],
      value,
    })
  }
  const sales7Total = sales7.reduce((n, p) => n + p.value, 0)

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

      <button className="card month-progress clickable" onClick={() => onNavigate('monthly')}>
        <div className="mp-head">
          <h3 className="list-title">This month — {monthName}</h3>
          <div className="mp-pills">
            {growth !== null && (
              <span className={growth >= 0 ? 'growth-up' : 'growth-down'}>
                {growth >= 0 ? '▲' : '▼'} {Math.abs(growth)}% vs last year
              </span>
            )}
            <span className="mp-pending">⏳ {taskCount - tasksDone} pending today</span>
          </div>
        </div>

        <div className="month-rings">
          <div className="ring-block">
            <ProgressRing pct={salesPct} color="var(--pa-orange)" />
            <span className="ring-cap">Sales</span>
            <span className="ring-fig">
              {formatMoney(ach.sales)} / {salesTarget ? formatMoney(salesTarget) : '—'}
            </span>
          </div>
          <div className="ring-block">
            <ProgressRing pct={collPct} color="var(--green)" />
            <span className="ring-cap">Collection</span>
            <span className="ring-fig">
              {formatMoney(ach.collection)} / {collTarget ? formatMoney(collTarget) : '—'}
            </span>
          </div>
        </div>
      </button>

      <button className="card trend-card clickable" onClick={() => onNavigate('graphs')}>
        <div className="mp-head">
          <h3 className="list-title">Last 7 days — Sales</h3>
          <span className="trend-total">₹{compactNumber(sales7Total)} total</span>
        </div>
        <BarChart data={sales7} format={rupee} />
      </button>

      <div className="stat-grid">
        <button className="card stat clickable" onClick={() => onNavigate('daily')}>
          <span className="stat-label">Morning Mantras today</span>
          <span className="stat-value">{mantrasDone}/{settings.mantras.length}</span>
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
        <button className="card stat clickable" onClick={() => onNavigate('expenses')}>
          <span className="stat-label">Month personal expense</span>
          <span className="stat-value">{formatMoney(monthExpense)}</span>
        </button>
      </div>

    </div>
  )
}
