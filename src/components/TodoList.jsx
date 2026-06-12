import { useState } from 'react'
import { uid } from '../lib/format.js'

// Task categories shown in the add dropdown. Business is the default.
const CATEGORIES = ['Business', 'Family', 'Team Members']

function catClass(cat) {
  if (cat === 'Family') return 'family'
  if (cat === 'Team Members') return 'team'
  return 'business'
}

/**
 * Today's To-Do list — add / check / remove, with a category per task
 * (Business / Family / Team Members). The chosen category stays selected
 * until changed, and starts on Business each time the app opens.
 *
 * @param {object}   props
 * @param {Array}    props.items
 * @param {Function} props.onChange
 */
export default function TodoList({ items = [], onChange }) {
  const [text, setText] = useState('')
  const [category, setCategory] = useState('Business')

  function add(e) {
    e.preventDefault()
    const value = text.trim()
    if (!value) return
    onChange([...items, { id: uid(), text: value, done: false, category }])
    setText('')
    // category is intentionally kept, so several tasks can share it.
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
        <h3 className="list-title">📝 To-Do</h3>
      </div>

      <ul className="checklist">
        {items.map((it) => (
          <li key={it.id} className={it.done ? 'done' : ''}>
            <input type="checkbox" checked={!!it.done} onChange={() => toggle(it.id)} />
            <span className="checklist-text">{it.text}</span>
            {it.category && (
              <span className={`todo-cat ${catClass(it.category)}`}>{it.category}</span>
            )}
            <button className="icon-btn" title="Remove" onClick={() => remove(it.id)}>
              ✕
            </button>
          </li>
        ))}
        {items.length === 0 && <li className="checklist-empty">Nothing yet.</li>}
      </ul>

      <form className="inline-add" onSubmit={add}>
        <select
          className="todo-cat-select"
          value={category}
          aria-label="Category"
          onChange={(e) => setCategory(e.target.value)}
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <input
          type="text"
          className="todo-text"
          value={text}
          placeholder="What do you need to do today?"
          onChange={(e) => setText(e.target.value)}
        />
        <button className="btn small" type="submit">
          Add
        </button>
      </form>
    </section>
  )
}
