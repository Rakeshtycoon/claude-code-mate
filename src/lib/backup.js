// Backup & restore for Business Diary.
//
// All app data lives in localStorage under the "bd." prefix. A backup is a
// single JSON file containing every such key, which the user can save to their
// phone or upload to Google Drive, then import again on any device.

export const BACKUP_PREFIX = 'bd.'
export const BACKUP_VERSION = 1
export const APP_ID = 'business-diary'

/** Read every bd.* key from localStorage into a plain object. */
export function collectData() {
  const data = {}
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (!key || !key.startsWith(BACKUP_PREFIX)) continue
    const raw = localStorage.getItem(key)
    try {
      data[key] = JSON.parse(raw)
    } catch {
      data[key] = raw
    }
  }
  return data
}

/** Build the backup envelope (metadata + data). */
export function buildBackup() {
  return {
    app: APP_ID,
    version: BACKUP_VERSION,
    exportedAt: new Date().toISOString(),
    data: collectData(),
  }
}

/** Trigger a download of the backup as a .json file. Returns the backup object. */
export function downloadBackup() {
  const backup = buildBackup()
  const blob = new Blob([JSON.stringify(backup, null, 2)], {
    type: 'application/json',
  })
  const url = URL.createObjectURL(blob)
  const stamp = new Date().toISOString().slice(0, 10)
  const a = document.createElement('a')
  a.href = url
  a.download = `business-diary-backup-${stamp}.json`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
  return backup
}

/** Parse and validate backup text. Throws a friendly error if invalid. */
export function parseBackup(text) {
  let parsed
  try {
    parsed = JSON.parse(text)
  } catch {
    throw new Error('This file is not valid JSON. Please pick a backup file.')
  }
  if (
    !parsed ||
    typeof parsed !== 'object' ||
    parsed.app !== APP_ID ||
    typeof parsed.data !== 'object'
  ) {
    throw new Error('This is not a Business Diary backup file.')
  }
  return parsed
}

/** Remove every bd.* key from localStorage. */
function clearData() {
  const keys = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key && key.startsWith(BACKUP_PREFIX)) keys.push(key)
  }
  keys.forEach((k) => localStorage.removeItem(k))
}

/**
 * Restore a parsed backup into localStorage.
 * @param {object}  parsed         Result of parseBackup().
 * @param {object}  [opts]
 * @param {boolean} [opts.merge]   Keep existing data and overlay the backup
 *                                 (default false → replace everything).
 */
export function restoreBackup(parsed, { merge = false } = {}) {
  if (!merge) clearData()
  for (const [key, value] of Object.entries(parsed.data)) {
    if (!key.startsWith(BACKUP_PREFIX)) continue
    localStorage.setItem(key, JSON.stringify(value))
  }
}

/** Friendly counts so the user can see what a backup contains. */
export function summarize(data) {
  const count = (key) => (Array.isArray(data[key]) ? data[key].length : 0)
  const goals = data['bd.goals'] || {}
  const goalCount = Object.values(goals).reduce(
    (n, arr) => n + (Array.isArray(arr) ? arr.length : 0),
    0
  )
  return {
    days: Object.keys(data['bd.days'] || {}).length,
    goals: goalCount,
    rituals: count('bd.rituals'),
    quotes: count('bd.quotes'),
    bucket: count('bd.bucket'),
    monthlyPlans: Object.keys(data['bd.monthlyPlans'] || {}).length,
  }
}
