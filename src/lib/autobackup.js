// Automatic backup for Business Diary.
//
// A browser page can only run while it is open, so true scheduled background
// backup (e.g. at 6am while closed) is not possible without a server. Instead
// we back up automatically the first time the app is opened each day — which
// for a morning-planning habit effectively means "once every morning".
//
// Two layers:
//   1. Daily in-browser snapshots (works in every browser) — silent restore
//      points kept under the bdsys.* namespace so they are never themselves
//      exported.
//   2. Optional auto-save to a real file via the File System Access API
//      (Chrome / Edge / Android). Once the user picks a file, the app writes
//      to it automatically each day without prompting again.

import { buildBackup, collectData, APP_ID, BACKUP_VERSION } from './backup.js'

const SNAP_KEY = 'bdsys.snapshots'
const LAST_FILE_KEY = 'bdsys.lastFileBackup'
const MAX_SNAPSHOTS = 14

export function todayKey() {
  return new Date().toISOString().slice(0, 10)
}

/* ---------- In-browser daily snapshots ---------- */

export function getSnapshots() {
  try {
    const raw = localStorage.getItem(SNAP_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function setSnapshots(list) {
  localStorage.setItem(SNAP_KEY, JSON.stringify(list.slice(0, MAX_SNAPSHOTS)))
}

export function addSnapshot(kind = 'auto') {
  const snap = {
    id: Date.now().toString(36),
    at: new Date().toISOString(),
    kind,
    data: collectData(),
  }
  const list = getSnapshots()
  setSnapshots([snap, ...list])
  return snap
}

/** Create today's snapshot if one hasn't been made yet today. */
export function maybeDailySnapshot() {
  const list = getSnapshots()
  const last = list[0]
  if (!last || last.at.slice(0, 10) < todayKey()) {
    addSnapshot('auto')
    return true
  }
  return false
}

export function deleteSnapshot(id) {
  setSnapshots(getSnapshots().filter((s) => s.id !== id))
}

/** Wrap a snapshot's data so it can be fed to restoreBackup(). */
export function snapshotAsBackup(snap) {
  return { app: APP_ID, version: BACKUP_VERSION, exportedAt: snap.at, data: snap.data }
}

/* ---------- File System Access API auto-save ---------- */

export function fileApiSupported() {
  return typeof window !== 'undefined' && 'showSaveFilePicker' in window
}

const IDB_NAME = 'bd-autobackup'
const IDB_STORE = 'handles'
const HANDLE_KEY = 'backupFile'

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, 1)
    req.onupgradeneeded = () => req.result.createObjectStore(IDB_STORE)
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function idbPut(value) {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, 'readwrite')
    tx.objectStore(IDB_STORE).put(value, HANDLE_KEY)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

async function idbGet() {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, 'readonly')
    const req = tx.objectStore(IDB_STORE).get(HANDLE_KEY)
    req.onsuccess = () => resolve(req.result || null)
    req.onerror = () => reject(req.error)
  })
}

async function idbDelete() {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_STORE, 'readwrite')
    tx.objectStore(IDB_STORE).delete(HANDLE_KEY)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function loadHandle() {
  if (!fileApiSupported()) return null
  try {
    return await idbGet()
  } catch {
    return null
  }
}

async function ensurePermission(handle, request) {
  const opts = { mode: 'readwrite' }
  if ((await handle.queryPermission(opts)) === 'granted') return true
  if (request && (await handle.requestPermission(opts)) === 'granted') return true
  return false
}

/** Ask the user to choose/create a backup file, and remember it. */
export async function setupFileBackup() {
  const handle = await window.showSaveFilePicker({
    suggestedName: 'business-diary-backup.json',
    types: [
      {
        description: 'Business Diary backup',
        accept: { 'application/json': ['.json'] },
      },
    ],
  })
  await idbPut(handle)
  await writeToHandle(handle)
  localStorage.setItem(LAST_FILE_KEY, todayKey())
  return handle
}

export async function writeToHandle(handle) {
  const writable = await handle.createWritable()
  await writable.write(JSON.stringify(buildBackup(), null, 2))
  await writable.close()
}

export async function disableFileBackup() {
  await idbDelete()
  localStorage.removeItem(LAST_FILE_KEY)
}

/** Status used by the UI. */
export async function fileBackupStatus() {
  if (!fileApiSupported()) return { supported: false }
  const handle = await loadHandle()
  if (!handle) return { supported: true, enabled: false }
  const granted = (await handle.queryPermission({ mode: 'readwrite' })) === 'granted'
  return {
    supported: true,
    enabled: true,
    granted,
    name: handle.name,
    lastBackup: localStorage.getItem(LAST_FILE_KEY) || null,
  }
}

/** Force a write right now (re-prompts for permission if needed). */
export async function backupToFileNow() {
  const handle = await loadHandle()
  if (!handle) throw new Error('Auto-backup file is not set up yet.')
  if (!(await ensurePermission(handle, true))) {
    throw new Error('Permission to write the backup file was not granted.')
  }
  await writeToHandle(handle)
  localStorage.setItem(LAST_FILE_KEY, todayKey())
}

/* ---------- Daily runner (called once on app load) ---------- */

export async function runDailyAutoBackup() {
  const snapped = maybeDailySnapshot()
  let fileWritten = false
  try {
    if (fileApiSupported()) {
      const handle = await loadHandle()
      // Silent path only: write if permission is already granted (no prompt
      // without a user gesture) and we haven't written today yet.
      if (handle && (await ensurePermission(handle, false))) {
        if (localStorage.getItem(LAST_FILE_KEY) !== todayKey()) {
          await writeToHandle(handle)
          localStorage.setItem(LAST_FILE_KEY, todayKey())
          fileWritten = true
        }
      }
    }
  } catch {
    // Never let auto-backup break the app.
  }
  return { snapped, fileWritten }
}
