import { useCallback, useSyncExternalStore } from 'react'

/**
 * Persist React state in the browser's localStorage, with an in-memory cache
 * shared across all hook instances for the same key.
 *
 * Why the cache: when a phone opens the app as a loose `file://` file, the
 * browser often blocks localStorage. The module-level cache keeps data alive
 * while the app is open (so switching screens never loses it) and also keeps
 * every component using the same key in sync. localStorage is still used for
 * real persistence whenever the browser allows it (served over http/https or
 * inside the packaged app).
 *
 * @param {string} key      Storage key, namespaced per data type.
 * @param {*}      initial  Value used when nothing is stored yet.
 */

// key -> current value (survives component unmounts)
const cache = new Map()
// key -> Set<listener>
const listeners = new Map()

function ensureLoaded(key, initial) {
  if (cache.has(key)) return
  let value = initial
  try {
    const raw = localStorage.getItem(key)
    if (raw !== null) value = JSON.parse(raw)
  } catch {
    // Storage unavailable — fall back to the initial value.
  }
  cache.set(key, value)
}

function emit(key) {
  const subs = listeners.get(key)
  if (subs) subs.forEach((cb) => cb())
}

export function useLocalStorage(key, initial) {
  ensureLoaded(key, initial)

  const subscribe = useCallback(
    (cb) => {
      let subs = listeners.get(key)
      if (!subs) {
        subs = new Set()
        listeners.set(key, subs)
      }
      subs.add(cb)
      return () => subs.delete(cb)
    },
    [key]
  )

  const getSnapshot = useCallback(() => cache.get(key), [key])

  const value = useSyncExternalStore(subscribe, getSnapshot, getSnapshot)

  const setValue = useCallback(
    (next) => {
      const prev = cache.get(key)
      const resolved = typeof next === 'function' ? next(prev) : next
      if (resolved === prev) return
      cache.set(key, resolved)
      try {
        localStorage.setItem(key, JSON.stringify(resolved))
      } catch {
        // Blocked (e.g. file:// on mobile) — value still lives in the cache.
      }
      emit(key)
    },
    [key]
  )

  return [value, setValue]
}
