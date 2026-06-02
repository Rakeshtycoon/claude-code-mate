import { useState } from 'react'
import { uid } from '../lib/format.js'

/**
 * Today's To-Do list — a simple add / check / remove list.
 *
 * @param {object}   props
 * @param {Array}    props.items
 * @param {Function} props.onChange
 */
export default function TodoList({ items = [], onChange }) {
  const [text, setText] = useState('')

  function add(e) {
    e.preventDefault()
    const value = text.trim()
    if (!value) return
    onChange([...items, { id: uid(), text: value, done: false }])
    setText('')
  }

  function toggle(id) {
    onChange(items.map((it) => (it.id === id ? { ...it, done: !it.done } : it)))
  }

  function remove(id) {
    onChange(items.filter((it) => it.id !== id))
  }

  return (
    <section className="list-card">
      <div className="list-head-row">
        <h3 className="list-title">📝 આજના કામ / To-Do</h3>
      </div>

      <ul className="checklist">
        {items.map((it) => (
          <li key={it.id} className={it.done ? 'done' : ''}>
            <input type="checkbox" checked={!!it.done} onChange={() => toggle(it.id)} />
            <span className="checklist-text">{it.text}</span>
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
        <button className="btn small" type="submit">
          Add
        </button>
      </form>
    </section>
  )
}
