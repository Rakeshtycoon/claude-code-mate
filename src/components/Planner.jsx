import { useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import EditableList from './EditableList.jsx'

function currentMonth() {
  return new Date().toISOString().slice(0, 7)
}

function monthLabel(ym) {
  const [y, m] = ym.split('-')
  return new Date(Number(y), Number(m) - 1, 1).toLocaleDateString(undefined, {
    month: 'long',
    year: 'numeric',
  })
}

// Shift a YYYY-MM string by a number of months (e.g. +1 = next month).
function addMonths(ym, delta) {
  const [y, m] = ym.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

// Build a Mon→Sun calendar grid for the given YYYY-MM.
function buildGrid(ym) {
  const [y, m] = ym.split('-').map(Number)
  const first = new Date(y, m - 1, 1)
  const daysInMonth = new Date(y, m, 0).getDate()
  const lead = (first.getDay() + 6) % 7
  const cells = []
  for (let i = 0; i < lead; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  while (cells.length % 7 !== 0) cells.push(null)
  return cells
}

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const SIZES = [
  { label: 'Small', value: 8 },
  { label: 'Medium', value: 10 },
  { label: 'Large', value: 12 },
  { label: 'X-Large', value: 14 },
]

const COLORS = ['#0f172a', '#2563eb', '#16a34a', '#dc2626', '#ea580c', '#7c3aed']

// New notes start black + small. Each note can override this on its own.
const DEFAULT_STYLE = { fontSize: 8, color: '#0f172a' }

export default function Planner() {
  const [month, setMonth] = useState(currentMonth())
  const [notes, setNotes] = useLocalStorage('bd.plannerNotes', {})
  const [nextPlans, setNextPlans] = useLocalStorage('bd.nextMonthPlans', {})
  // Per-day note styles: { [month]: { [day]: { fontSize, color } } }
  const [styles, setStyles] = useLocalStorage('bd.plannerNoteStyles', {})
  const [selectedDay, setSelectedDay] = useState(null)

  const grid = buildGrid(month)
  const nextMonth = addMonths(month, 1)
  const dayNotes = notes[month] || {}
  const monthStyles = styles[month] || {}

  function setDayNote(day, text) {
    setNotes({ ...notes, [month]: { ...dayNotes, [day]: text } })
  }

  // Actions planned for this month (added last month) — let them be ticked off.
  function toggleMonthPlan(id) {
    const list = nextPlans[month] || []
    setNextPlans({
      ...nextPlans,
      [month]: list.map((it) => (it.id === id ? { ...it, done: !it.done } : it)),
    })
  }

  function styleFor(day) {
    return monthStyles[day] || DEFAULT_STYLE
  }

  // Update only the selected day's style; other notes are untouched.
  function patchSelectedStyle(patch) {
    if (!selectedDay) return
    const current = monthStyles[selectedDay] || DEFAULT_STYLE
    setStyles({
      ...styles,
      [month]: { ...monthStyles, [selectedDay]: { ...current, ...patch } },
    })
  }

  function resetSelectedStyle() {
    if (!selectedDay) return
    const next = { ...monthStyles }
    delete next[selectedDay]
    setStyles({ ...styles, [month]: next })
  }

  function changeMonth(value) {
    setMonth(value)
    setSelectedDay(null)
  }

  const today = new Date()
  const todayKey = today.toISOString().slice(0, 7)
  const todayDate = today.getDate()
  const sel = selectedDay ? styleFor(selectedDay) : null

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Monthly Planner</h1>
          <p className="muted">A bird's-eye view of {monthLabel(month)}.</p>
        </div>
        <input type="month" value={month} onChange={(e) => changeMonth(e.target.value)} />
      </header>

      <div className="card planner-toolbar">
        {!selectedDay ? (
          <span className="muted">
            Tap a date’s note below, then change its size or colour here — only that note
            changes.
          </span>
        ) : (
          <>
            <span className="muted">
              Styling note for <strong>{monthLabel(month).split(' ')[0]} {selectedDay}</strong>:
            </span>
            <label className="toolbar-field">
              <span>Size</span>
              <select
                value={sel.fontSize}
                onChange={(e) => patchSelectedStyle({ fontSize: Number(e.target.value) })}
              >
                {SIZES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
            <span className="toolbar-field-label">Color</span>
            <div className="swatches">
              {COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  className={`swatch ${sel.color === c ? 'active' : ''}`}
                  style={{ background: c }}
                  title={c}
                  onClick={() => patchSelectedStyle({ color: c })}
                />
              ))}
              <input
                type="color"
                className="swatch-picker"
                value={sel.color}
                title="Custom colour"
                onChange={(e) => patchSelectedStyle({ color: e.target.value })}
              />
            </div>
            <button className="btn small" type="button" onClick={resetSelectedStyle}>
              Reset
            </button>
          </>
        )}
      </div>

      {/* This month's action plan — what you wrote last month under
          "My Planning for Next Month". Shown like a marked calendar square. */}
      <div className="card month-plan">
        <div className="month-plan-head">
          <span>📌 Action Plan — {monthLabel(month).split(' ')[0]}</span>
          <span className="muted">planned last month</span>
        </div>
        {(nextPlans[month] || []).length === 0 ? (
          <p className="muted month-plan-empty">
            Nothing planned for {monthLabel(month).split(' ')[0]} yet — open last month
            and add actions under “My Planning for Next Month”.
          </p>
        ) : (
          <ul className="checklist">
            {(nextPlans[month] || []).map((it) => (
              <li key={it.id} className={it.done ? 'done' : ''}>
                <input
                  type="checkbox"
                  checked={!!it.done}
                  onChange={() => toggleMonthPlan(it.id)}
                />
                <span className="checklist-text">{it.text}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <div className="calendar">
          {WEEKDAYS.map((w) => (
            <div key={w} className="cal-weekday">
              {w}
            </div>
          ))}
          {grid.map((day, i) => (
            <div
              key={i}
              className={`cal-cell ${day ? '' : 'empty'} ${
                month === todayKey && day === todayDate ? 'today' : ''
              } ${day && day === selectedDay ? 'selected' : ''}`}
            >
              {day && (
                <>
                  <span className="cal-date">{day}</span>
                  <textarea
                    className="cal-note"
                    style={{
                      fontSize: `${styleFor(day).fontSize}px`,
                      color: styleFor(day).color,
                    }}
                    value={dayNotes[day] || ''}
                    placeholder="…"
                    onFocus={() => setSelectedDay(day)}
                    onChange={(e) => setDayNote(day, e.target.value)}
                  />
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Stored under next month's key so it appears when you open that month. */}
      <EditableList
        title={`My Planning for ${monthLabel(nextMonth).split(' ')[0]} (Next Month)`}
        items={nextPlans[nextMonth] || []}
        onChange={(items) => setNextPlans({ ...nextPlans, [nextMonth]: items })}
        placeholder={`What action should you take in ${monthLabel(nextMonth).split(' ')[0]}?`}
      />
    </div>
  )
}
