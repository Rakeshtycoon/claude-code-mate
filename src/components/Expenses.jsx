import { useState } from 'react'
import { useLocalStorage } from '../hooks/useLocalStorage.js'
import { todayISO, formatMoney, formatDate, uid } from '../lib/format.js'

function shiftDate(iso, days) {
  const d = new Date(iso)
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

export default function Expenses() {
  const [all, setAll] = useLocalStorage('bd.expenses', {})
  const [date, setDate] = useState(todayISO())
  const [amount, setAmount] = useState('')
  const [note, setNote] = useState('')

  const list = all[date] || []
  const dayTotal = list.reduce((n, e) => n + (Number(e.amount) || 0), 0)

  const ym = date.slice(0, 7)
  let monthTotal = 0
  for (const [d, items] of Object.entries(all)) {
    if (d.slice(0, 7) !== ym) continue
    for (const e of items) monthTotal += Number(e.amount) || 0
  }

  function add(e) {
    e.preventDefault()
    const amt = Number(amount)
    if (!amt) return
    setAll({ ...all, [date]: [...list, { id: uid(), amount: amt, note: note.trim() }] })
    setAmount('')
    setNote('')
  }

  function remove(id) {
    setAll({ ...all, [date]: list.filter((e) => e.id !== id) })
  }

  const dateLabel = new Date(date).toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  })

  return (
    <div>
      <header className="page-head daily-head">
        <div>
          <h1>Personal Expense</h1>
          <p className="muted">{dateLabel}</p>
        </div>
        <div className="date-nav">
          <button className="btn" onClick={() => setDate(shiftDate(date, -1))}>‹</button>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <button className="btn" onClick={() => setDate(shiftDate(date, 1))}>›</button>
          <button className="btn" onClick={() => setDate(todayISO())}>Today</button>
        </div>
      </header>

      <div className="exp-totals">
        <div className="card stat">
          <span className="stat-label">Today's expense</span>
          <span className="stat-value">{formatMoney(dayTotal)}</span>
        </div>
        <div className="card stat">
          <span className="stat-label">
            {new Date(date).toLocaleDateString(undefined, { month: 'long' })} total
          </span>
          <span className="stat-value">{formatMoney(monthTotal)}</span>
        </div>
      </div>

      <section className="card">
        <h3 className="list-title">Expenses on {formatDate(date)}</h3>

        <ul className="expense-list">
          {list.map((e) => (
            <li key={e.id}>
              <span className="exp-note">{e.note || 'Expense'}</span>
              <span className="exp-amt">{formatMoney(e.amount)}</span>
              <button className="icon-btn" title="Remove" onClick={() => remove(e.id)}>✕</button>
            </li>
          ))}
          {list.length === 0 && <li className="checklist-empty">No expenses added.</li>}
        </ul>

        <form className="inline-add exp-add" onSubmit={add}>
          <span className="rupee">
            <input
              type="number"
              className="exp-amount-input"
              value={amount}
              placeholder="Amount"
              onChange={(e) => setAmount(e.target.value)}
            />
          </span>
          <input
            type="text"
            value={note}
            placeholder="What was it for? (optional)"
            onChange={(e) => setNote(e.target.value)}
          />
          <button className="btn small" type="submit">Add</button>
        </form>
      </section>
    </div>
  )
}
