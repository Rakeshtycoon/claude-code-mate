/**
 * A 12-hour time picker (hour 1–12, minute, AM/PM) that stores its value as a
 * 24-hour "HH:MM" string (or "" when unset). Leaving the hour on "--" clears it.
 *
 * @param {object}   props
 * @param {string}   props.value     "HH:MM" (24-hour) or "".
 * @param {Function} props.onChange  Receives the new "HH:MM" string or "".
 */
function parse(value) {
  if (!value) return { h: '', m: '00', ap: 'AM' }
  const [H, M] = String(value).split(':').map(Number)
  const ap = H >= 12 ? 'PM' : 'AM'
  let h = H % 12
  if (h === 0) h = 12
  return { h: String(h), m: String(M).padStart(2, '0'), ap }
}

function to24(h, m, ap) {
  let H = Number(h) % 12
  if (ap === 'PM') H += 12
  return `${String(H).padStart(2, '0')}:${m}`
}

export default function TimeInput({ value, onChange }) {
  const { h, m, ap } = parse(value)

  function update(nh, nm, nap) {
    if (!nh) {
      onChange('')
      return
    }
    onChange(to24(nh, nm || '00', nap || 'AM'))
  }

  return (
    <span className="time-input">
      <select value={h} aria-label="Hour" onChange={(e) => update(e.target.value, m, ap)}>
        <option value="">--</option>
        {Array.from({ length: 12 }, (_, i) => i + 1).map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
      <span className="time-colon">:</span>
      <select
        value={m}
        aria-label="Minute"
        disabled={!h}
        onChange={(e) => update(h, e.target.value, ap)}
      >
        {Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0')).map((mm) => (
          <option key={mm} value={mm}>
            {mm}
          </option>
        ))}
      </select>
      <select
        value={ap}
        aria-label="AM or PM"
        disabled={!h}
        onChange={(e) => update(h, m, e.target.value)}
      >
        <option value="AM">AM</option>
        <option value="PM">PM</option>
      </select>
      {h && (
        <button
          type="button"
          className="icon-btn"
          title="Clear time"
          onClick={() => onChange('')}
        >
          ✕
        </button>
      )}
    </span>
  )
}
