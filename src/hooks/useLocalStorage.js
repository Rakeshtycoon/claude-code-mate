import { useEffect, useState } from 'react'

/**
 * Persist a piece of React state in the browser's localStorage.
 * Reads the initial value once on mount and writes back on every change.
 *
 * @param {string} key      Storage key, namespaced per data type.
 * @param {*}      initial  Value used when nothing is stored yet.
 */
export function useLocalStorage(key, initial) {
  const [value, setValue] = useState(() => {
    try {
      const raw = localStorage.getItem(key)
      return raw !== null ? JSON.parse(raw) : initial
    } catch {
      return initial
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value))
    } catch {
      // Storage full or unavailable — fail silently, data stays in memory.
    }
  }, [key, value])

  return [value, setValue]
}
