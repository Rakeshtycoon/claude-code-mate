// Small formatting + id helpers shared across the app.

export function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

export function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

export function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

const currency = new Intl.NumberFormat(undefined, {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 2,
})

export function formatMoney(amount) {
  const n = Number(amount) || 0
  return currency.format(n)
}

// Format a 24-hour "HH:MM" string as 12-hour with AM/PM, e.g. "14:05" -> "2:05 PM".
export function formatTime12(value) {
  if (!value) return ''
  const [H, M] = String(value).split(':').map(Number)
  if (Number.isNaN(H) || Number.isNaN(M)) return ''
  const ap = H >= 12 ? 'PM' : 'AM'
  let h = H % 12
  if (h === 0) h = 12
  return `${h}:${String(M).padStart(2, '0')} ${ap}`
}

// Compact number for chart labels: 1500 -> "1.5k", 2300000 -> "2.3M".
export function compactNumber(value) {
  const n = Number(value) || 0
  const abs = Math.abs(n)
  if (abs >= 1e7) return (n / 1e7).toFixed(1).replace(/\.0$/, '') + 'Cr'
  if (abs >= 1e5) return (n / 1e5).toFixed(1).replace(/\.0$/, '') + 'L'
  if (abs >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'k'
  return String(Math.round(n))
}
