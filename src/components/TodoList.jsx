import { useState } from 'react'
import { uid } from '../lib/format.js'
import TimeInput from './TimeInput.jsx'

/**
 * Today's To-Do list with an optional time per task. Setting a time schedules
 * a reminder (see useReminders); the time is just left blank to skip it.
 *
 * @param {object}   props
 * @param {Array}    props.items
 * @param {Function} props.onChange
 * @param {string}   props.notifyState     Notification.permission value.
 * @param {Function} props.onEnableNotify  Ask the browser for permission.
 */
export default function TodoList({ items = [], onChange, notifyState, onEnableNotify }) {
  const [text, setText] = useState('')
  const [time, setTime] = useState('')

  function add(e) {
    e.preventDefault()
    const value = text.trim()
    if (!value) return
    onChange([...items, { id: uid(), text: value, done: false, time: time || '' }])
    setText('')
    setTime('')
  }

  function toggle(id) {
    onChange(items.map((it) => (it.id === id ? { ...it, done: !it.done } : it)))
  }

  function remove(id) {
    onChange(items.filter((it) => it.id !== id))
  }

  function setItemTime(id, t) {
    onChange(items.map((it) => (it.id === id ? { ...it, time: t } : it)))
  }

  const hasTimed = items.some((it) => it.time && !it.done)

  return (
    <section className="list-card">
      <div className="list-head-row">
        <h3 className="list-title">📝 આજના કામ / To-Do</h3>
        {hasTimed && notifyState !== 'granted' && notifyState !== 'unsupported' && (
          <button className="btn small" type="button" onClick={onEnableNotify}>
            🔔 Enable reminders
          </button>
        )}
      </div>

      <ul className="checklist">
        {items.map((it) => (
          <li key={it.id} className={it.done ? 'done' : ''}>
            <input type="checkbox" checked={!!it.done} onChange={() => toggle(it.id)} />
            <span className="checklist-text">{it.text}</span>
            <TimeInput value={it.time || ''} onChange={(t) => setItemTime(it.id, t)} />
            <button className="icon-btn" title="Remove" onClick={() => remove(it.id)}>
              ✕
            </button>
          </li>
        ))}
        {items.length === 0 && <li className="checklist-empty">Nothing yet.</li>}
      </ul>

      <form className="inline-add" onSubmit={add}>
        <input
          type="text"
          className="todo-text"
          value={text}
          placeholder="આજે શું કરવાનું છે? લખો…"
          onChange={(e) => setText(e.target.value)}
        />
        <TimeInput value={time} onChange={setTime} />
        <button className="btn small" type="submit">
          Add
        </button>
      </form>

      {hasTimed && notifyState === 'denied' && (
        <p className="small-note">
          Reminders are blocked in your browser settings — allow notifications for
          this page to get time alerts (works while the app is open).
        </p>
      )}
      {hasTimed && (
        <p className="small-note">
          ⏰ Time set — you’ll get a reminder while the app is open. Carrying a task
          to the next day drops its time.
        </p>
      )}
    </section>
  )
}
