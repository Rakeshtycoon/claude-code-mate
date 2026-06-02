import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { useSettings } from '../hooks/useSettings.js'
import { todayISO, formatDate, formatMoney, uid } from '../lib/format.js'
import { monthAchieved } from '../lib/totals.js'
import { useMemo, useState } from 'react'
import EditableList from './EditableList.jsx'
import TodoList from './TodoList.jsx'

// Every list on the daily page is a task list whose unfinished items can be
// carried forward to the next day.
const TASK_KEYS = [
  'todo',
  'yearlyGoal',
  'visits',
  'followups',
  'quotations',
  'operations',
  'business',
  'teamFollow',
  'otherFollow',
  'familyOther',
]

/** Collect not-done items from a day, grouped by list, with a total count. */
function pendingOf(day) {
  const lists = {}
  let count = 0
  for (const key of TASK_KEYS) {
    const items = (day?.lists?.[key] || []).filter((it) => !it.done)
    if (items.length) {
      lists[key] = items
      count += items.length
    }
  }
  return { lists, count }
}

/** Find the most recent earlier day that still has pending tasks. */
function findCarrySource(days, date) {
  const earlier = Object.keys(days)
    .filter((d) => d < date)
    .sort()
    .reverse()
  for (const d of earlier) {
    const { lists, count } = pendingOf(days[d])
    if (count > 0) return { date: d, lists, count }
  }
  return null
}

const LISTS = [
  { key: 'yearlyGoal', title: 'Action to Achieve My Yearly Goal' },
  { key: 'visits', title: 'Visit / One to One / Zoom Call' },
  { key: 'followups', title: 'Follow up & Reminder via Calls / Msg.' },
  { key: 'quotations', title: 'Quotation / Inquiry / Pending to Close' },
  { key: 'operations', title: 'Operation and Other Task' },
  { key: 'business', title: 'Business' },
  { key: 'teamFollow', title: 'Team Follow / Customer Follow' },
  { key: 'otherFollow', title: 'Other Follow' },
  { key: 'familyOther', title: 'Family / Other' },
]

function emptyDay() {
  return {
    mantras: {},
    month: { salesTarget: '', salesAchieved: '', collTarget: '', collAchieved: '' },
    today: { salesTarget: '', salesAchieved: '', collTarget: '', collAchieved: '' },
    lists: {},
  }
}

function shiftDate(iso, days) {
  const d = new Date(iso)
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

function TargetTable({ label, data, onChange, readOnly = false, hint }) {
  function set(field, value) {
    onChange({ ...data, [field]: value })
  }
  const cell = (field) =>
    readOnly ? (
      <span className="target-ro">{data[field] ? formatMoney(data[field]) : '—'}</span>
    ) : (
      <span className="rupee">
        <input type="number" value={data[field]} onChange={(e) => set(field, e.target.value)} />
      </span>
    )
  return (
    <div className="target-block">
      <div className="target-title">{label}</div>
      <table className="target-table">
        <thead>
          <tr>
            <th></th>
            <th>Target</th>
            <th>Achieved</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>Sales</th>
            <td>{cell('salesTarget')}</td>
            <td>{cell('salesAchieved')}</td>
          </tr>
          <tr>
            <th>Collection</th>
            <td>{cell('collTarget')}</td>
            <td>{cell('collAchieved')}</td>
          </tr>
        </tbody>
      </table>
      {hint && <p className="small-note">{hint}</p>}
    </div>
  )
}

export default function Daily() {
  const [days, setDays] = useLocalStorage('bd.days', {})
  const [plans] = useLocalStorage('bd.monthlyPlans', {})
  const [settings] = useSettings()
  const MANTRAS = settings.mantras
  const [date, setDate] = useState(todayISO())
  const [notifyState, setNotifyState] = useState(
    typeof Notification !== 'undefined' ? Notification.permission : 'unsupported'
  )

  function enableNotify() {
    if (typeof Notification !== 'undefined') {
      Notification.requestPermission().then((p) => setNotifyState(p))
    }
  }

  const day = days[date] || emptyDay()

  // The "Month" block is derived, not edited: target from the Monthly plan,
  // achieved rolled up from each day's "Today" achieved in the same month.
  const ym = date.slice(0, 7)
  const monthAch = monthAchieved(days, ym)
  const monthData = {
    salesTarget: plans[ym]?.target?.sales || '',
    salesAchieved: monthAch.sales || '',
    collTarget: plans[ym]?.target?.collection || '',
    collAchieved: monthAch.collection || '',
  }

  function updateDay(next) {
    setDays({ ...days, [date]: next })
  }

  function toggleMantra(m) {
    updateDay({ ...day, mantras: { ...day.mantras, [m]: !day.mantras[m] } })
  }

  function setList(key, items) {
    updateDay({ ...day, lists: { ...day.lists, [key]: items } })
  }

  // Pending tasks from an earlier day, offered for carry-forward. Only on the
  // day being viewed, only when viewing today, and only until answered once.
  const carrySource = useMemo(() => {
    if (date !== todayISO()) return null
    if (days[date]?.carryAsked) return null
    return findCarrySource(days, date)
  }, [days, date])

  function carryForward() {
    if (!carrySource) return
    const nextLists = { ...day.lists }
    for (const [key, items] of Object.entries(carrySource.lists)) {
      const copies = items.map((it) => ({ id: uid(), text: it.text, done: false }))
      nextLists[key] = [...(nextLists[key] || []), ...copies]
    }
    updateDay({ ...day, lists: nextLists, carryAsked: true })
  }

  function dismissCarry() {
    updateDay({ ...day, carryAsked: true })
  }

  const weekday = new Date(date).toLocaleDateString(undefined, { weekday: 'long' })
  const dateLabel = new Date(date).toLocaleDateString(undefined, {
    month: 'long',
    day: 'numeric',
  })
  const mantrasDone = MANTRAS.filter((m) => day.mantras[m]).length

  return (
    <div>
      <header className="page-head daily-head">
        <div>
          <h1>{dateLabel}</h1>
          <p className="muted">{weekday}</p>
        </div>
        <div className="date-nav">
          <button className="btn" onClick={() => setDate(shiftDate(date, -1))}>
            ‹
          </button>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <button className="btn" onClick={() => setDate(shiftDate(date, 1))}>
            ›
          </button>
          <button className="btn" onClick={() => setDate(todayISO())}>
            Today
          </button>
        </div>
      </header>

      {carrySource && (
        <div className="carry-banner">
          <div className="carry-text">
            <strong>{carrySource.count}</strong> કામ {formatDate(carrySource.date)} ના
            બાકી છે. આજે carry forward કરવા?
            <span className="muted"> ({carrySource.count} pending task(s))</span>
          </div>
          <div className="carry-actions">
            <button className="btn primary" onClick={carryForward}>
              હા, આજે લાવો
            </button>
            <button className="btn" onClick={dismissCarry}>
              ના
            </button>
          </div>
        </div>
      )}

      <div className="todo-feature">
        <TodoList
          items={day.lists.todo || []}
          onChange={(items) => setList('todo', items)}
          notifyState={notifyState}
          onEnableNotify={enableNotify}
        />
      </div>

      <section className="card">
        <div className="section-bar">
          Morning Mantras{' '}
          <span className="muted">
            {mantrasDone}/{MANTRAS.length}
          </span>
        </div>
        <div className="mantras">
          {MANTRAS.map((m) => (
            <label key={m} className={`mantra ${day.mantras[m] ? 'on' : ''}`}>
              <input
                type="checkbox"
                checked={!!day.mantras[m]}
                onChange={() => toggleMantra(m)}
              />
              {m}
            </label>
          ))}
        </div>
      </section>

      <div className="grid-2">
        <div className="card">
          <TargetTable
            label="Month"
            readOnly
            data={monthData}
            hint="Target comes from Monthly. Achieved adds up each day’s achieved below."
          />
        </div>
        <div className="card">
          <TargetTable
            label="Today"
            data={day.today}
            onChange={(today) => updateDay({ ...day, today })}
          />
        </div>
      </div>

      <div className="grid-2">
        {LISTS.map((l) => (
          <EditableList
            key={l.key}
            title={l.title}
            items={day.lists[l.key] || []}
            onChange={(items) => setList(l.key, items)}
            placeholder="Add…"
          />
        ))}
      </div>
    </div>
  )
}
