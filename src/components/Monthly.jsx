import { useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { formatMoney } from '../lib/format.js'
import { monthAchieved } from '../lib/totals.js'
import EditableList from './EditableList.jsx'

function currentMonth() {
  return new Date().toISOString().slice(0, 7) // YYYY-MM
}

function monthLabel(ym) {
  const [y, m] = ym.split('-')
  return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric',
  })
}

// Same month, one year earlier (e.g. "2026-05" -> "2025-05").
function lastYearMonth(ym) {
  const [y, m] = ym.split('-')
  return `${Number(y) - 1}-${m}`
}

function pct(achieved, target) {
  const a = Number(achieved)
  const t = Number(target)
  if (!t) return null
  return Math.round((a / t) * 100)
}

function emptyPlan() {
  return {
    comparison: '',
    target: { sales: '', collection: '', profit: '', other: '' },
    noAction: [],
  }
}

// Target / Achieved metrics.
const PLAN_METRICS = [
  { field: 'sales', label: 'Sales' },
  { field: 'collection', label: 'Collection' },
  { field: 'profit', label: 'Profit' },
  { field: 'other', label: 'Other' },
]

// Last Year figures (the actuals recorded for that month a year ago).
const LAST_YEAR_METRICS = [
  { field: 'sales', label: 'Sales' },
  { field: 'collection', label: 'Collection' },
  { field: 'profit', label: 'Profit' },
  { field: 'purchase', label: 'Purchase' },
  { field: 'expense', label: 'Expense' },
  { field: 'other', label: 'Other' },
]

function MoneyRow({ label, value, onChange }) {
  return (
    <label className="field">
      <span>{label}</span>
      <span className="rupee">
        <input type="number" value={value} onChange={(e) => onChange(e.target.value)} />
      </span>
    </label>
  )
}

function PlanTab() {
  const [plans, setPlans] = useLocalStorage('bd.monthlyPlans', {})
  // Actual figures per month, keyed by absolute YYYY-MM and shared across years.
  const [actuals, setActuals] = useLocalStorage('bd.monthlyActuals', {})
  // Daily entries — the Achieved totals are rolled up from these.
  const [days] = useLocalStorage('bd.days', {})
  const [month, setMonth] = useState(currentMonth())
  const [editLastYear, setEditLastYear] = useState(false)
  const plan = plans[month] || emptyPlan()

  // "Last Year" is the same month one year ago — read from the shared store.
  const lastYearKey = lastYearMonth(month)
  const lastYearData = actuals[lastYearKey] || {}

  function update(next) {
    setPlans({ ...plans, [month]: next })
  }
  const setGroup = (group, field, value) =>
    update({ ...plan, [group]: { ...plan[group], [field]: value } })

  // Edits to Last Year write back to that month's actuals record.
  function setLastYearField(field, value) {
    setActuals({
      ...actuals,
      [lastYearKey]: { ...lastYearData, [field]: value },
    })
  }

  // Achieved is the sum of each day's achieved Sales/Collection this month.
  const ach = monthAchieved(days, month)
  const achievedPct = pct(ach.sales, plan.target.sales)
  const collectionPct = pct(ach.collection, plan.target.collection)

  return (
    <div>
      <div className="list-head">
        <h2>My Monthly Plan — {monthLabel(month)}</h2>
        <input
          type="month"
          value={month}
          onChange={(e) => {
            setMonth(e.target.value)
            setEditLastYear(false)
          }}
        />
      </div>

      <div className="grid-2">
        <div className="card form">
          <div className="list-head-row">
            <h3 className="list-title">Last Year — {monthLabel(lastYearKey)}</h3>
            <button className="btn small" type="button" onClick={() => setEditLastYear((v) => !v)}>
              {editLastYear ? '✓ Done' : 'Edit'}
            </button>
          </div>

          {editLastYear
            ? LAST_YEAR_METRICS.map(({ field, label }) => (
                <MoneyRow
                  key={field}
                  label={label}
                  value={lastYearData[field] || ''}
                  onChange={(v) => setLastYearField(field, v)}
                />
              ))
            : LAST_YEAR_METRICS.map(({ field, label }) => (
                <div key={field} className="readonly-row">
                  <span>{label}</span>
                  <strong>{lastYearData[field] ? formatMoney(lastYearData[field]) : '—'}</strong>
                </div>
              ))}

          <p className="small-note">
            {editLastYear
              ? `Saving to ${monthLabel(lastYearKey)} — these become last-year figures everywhere.`
              : `Auto-filled from ${monthLabel(lastYearKey)}. Tap Edit to adjust.`}
          </p>
        </div>

        <div className="card form">
          <h3 className="list-title">
            Target <span className="head-note">— Sales is shared with Yearly Plan</span>
          </h3>
          {PLAN_METRICS.map(({ field, label }) => (
            <MoneyRow
              key={field}
              label={label}
              value={plan.target[field] || ''}
              onChange={(v) => setGroup('target', field, v)}
            />
          ))}
          <label className="field" style={{ marginTop: 14 }}>
            <span>Comparison</span>
            <div className="toggle">
              {['Growth', 'Same', 'De Growth'].map((c) => (
                <button
                  key={c}
                  type="button"
                  className={plan.comparison === c ? 'active' : ''}
                  onClick={() => update({ ...plan, comparison: c })}
                >
                  {c}
                </button>
              ))}
            </div>
          </label>
        </div>
      </div>

      <div className="card form">
        <h3 className="list-title">
          Achieved <span className="head-note">— auto from Daily</span>
        </h3>
        <div className="grid-2">
          <div>
            <div className="readonly-row">
              <span>Achieved Sales</span>
              <strong>{ach.sales ? formatMoney(ach.sales) : '—'}</strong>
            </div>
            <div className="achieved-pct">
              Sales achieved
              <strong>{achievedPct === null ? ' —' : ` ${achievedPct}%`}</strong>
            </div>
          </div>
          <div>
            <div className="readonly-row">
              <span>Achieved Collection</span>
              <strong>{ach.collection ? formatMoney(ach.collection) : '—'}</strong>
            </div>
            <div className="achieved-pct">
              Collection achieved
              <strong>{collectionPct === null ? ' —' : ` ${collectionPct}%`}</strong>
            </div>
          </div>
        </div>
        <p className="small-note">
          Adds up each day’s achieved Sales &amp; Collection from the Daily page.
        </p>
      </div>

      <EditableList
        title="I did not take any action to achieve the goal"
        items={plan.noAction || []}
        onChange={(items) => update({ ...plan, noAction: items })}
        placeholder="What got in the way?"
      />
    </div>
  )
}

function SalesTab() {
  const [rows, setRows] = useLocalStorage('bd.salesAnalysis', {})
  // Sales Target is shared with the Monthly Plan — set it here once a year and
  // it reflects into Monthly Plan → Target → Sales for each month.
  const [plans, setPlans] = useLocalStorage('bd.monthlyPlans', {})
  // Last Year column is auto-filled from the shared actuals store (the same
  // figures edited in the Monthly Plan "Last Year" section).
  const [actuals] = useLocalStorage('bd.monthlyActuals', {})
  // Achieved is rolled up from the Daily page, same as Monthly Plan → Achieved.
  const [days] = useLocalStorage('bd.days', {})
  const [year, setYear] = useState(new Date().getFullYear())

  // April (year) → March (year+1), matching the diary's financial-year layout.
  const months = []
  for (let i = 0; i < 12; i++) {
    const m = (3 + i) % 12
    const y = 3 + i < 12 ? year : year + 1
    months.push({ key: `${y}-${String(m + 1).padStart(2, '0')}`, m, y })
  }

  function setCell(key, field, value) {
    const row = rows[key] || { remark: '' }
    setRows({ ...rows, [key]: { ...row, [field]: value } })
  }

  // Writes to the Monthly Plan target so both tabs stay in sync.
  function setTargetSales(key, value) {
    const plan = plans[key] || emptyPlan()
    setPlans({ ...plans, [key]: { ...plan, target: { ...plan.target, sales: value } } })
  }

  return (
    <div>
      <div className="list-head">
        <h2>Yearly Plan — April {year} to March {year + 1}</h2>
        <input
          type="number"
          className="search"
          style={{ width: 110 }}
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
        />
      </div>
      <div className="card" style={{ overflowX: 'auto' }}>
        <table className="table sales-table">
          <thead>
            <tr>
              <th>Month</th>
              <th className="right">Last Year</th>
              <th className="right">Sales Target</th>
              <th className="right">Achieved</th>
              <th className="right">%</th>
              <th>Remark</th>
            </tr>
          </thead>
          <tbody>
            {months.map(({ key, m, y }) => {
              const row = rows[key] || {}
              const targetSales = plans[key]?.target?.sales || ''
              const achievedSales = monthAchieved(days, key).sales
              const p = pct(achievedSales, targetSales)
              const lastYearSales = actuals[lastYearMonth(key)]?.sales
              return (
                <tr key={key}>
                  <td>{new Date(y, m, 1).toLocaleDateString(undefined, { month: 'short', year: 'numeric' })}</td>
                  <td className="right"><span className="cell-ro">{lastYearSales ? formatMoney(lastYearSales) : '—'}</span></td>
                  <td><span className="rupee"><input type="number" value={targetSales} onChange={(e) => setTargetSales(key, e.target.value)} /></span></td>
                  <td className="right"><span className="cell-ro">{achievedSales ? formatMoney(achievedSales) : '—'}</span></td>
                  <td className="right">{p === null ? '—' : `${p}%`}</td>
                  <td><input type="text" value={row.remark || ''} onChange={(e) => setCell(key, 'remark', e.target.value)} /></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="small-note">
        Last Year is auto-filled from a year ago. Sales Target set here reflects into
        Monthly Plan → Target → Sales. Achieved &amp; % come automatically from the
        Daily page (not editable).
      </p>
    </div>
  )
}

export default function Monthly() {
  const [tab, setTab] = useState('plan')
  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Monthly</h1>
          <p className="muted">Plan the month, then track sales across the year.</p>
        </div>
        <div className="toggle">
          <button className={tab === 'plan' ? 'active' : ''} onClick={() => setTab('plan')}>
            Monthly Plan
          </button>
          <button className={tab === 'sales' ? 'active' : ''} onClick={() => setTab('sales')}>
            Yearly Plan
          </button>
        </div>
      </header>
      {tab === 'plan' ? <PlanTab /> : <SalesTab />}
    </div>
  )
}
