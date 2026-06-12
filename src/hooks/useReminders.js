import { useEffect, useRef } from 'react'
import { useLocalStorage } from './useLocalStorage.js'
import { todayISO, formatTime12 } from '../lib/format.js'

/**
 * Fire a browser notification at the time set on today's To-Do tasks.
 *
 * Note: a web page can only do this while it is open (the timers run in the
 * tab). Reminders for tasks whose time has already passed are skipped, and a
 * task only fires once per session. Real background reminders need the APK.
 */
export function useReminders() {
  const [days] = useLocalStorage('bd.days', {})
  const fired = useRef(new Set())

  useEffect(() => {
    if (typeof window === 'undefined' || !('Notification' in window)) return

    const today = todayISO()
    const todos = days[today]?.lists?.todo || []
    const now = Date.now()
    const timers = []

    for (const t of todos) {
      if (!t.time || t.done) continue
      const [h, m] = String(t.time).split(':').map(Number)
      if (Number.isNaN(h) || Number.isNaN(m)) continue

      const when = new Date()
      when.setHours(h, m, 0, 0)
      const delay = when.getTime() - now
      const key = `${today}|${t.id}|${t.time}`
      if (delay < 0 || fired.current.has(key)) continue

      timers.push(
        setTimeout(() => {
          fired.current.add(key)
          if (Notification.permission === 'granted') {
            try {
              new Notification('Business Diary — To-Do', {
                body: `🕐 ${formatTime12(t.time)}  —  ${t.text}`,
              })
            } catch {
              // Some browsers require notifications via a service worker; ignore.
            }
          }
        }, delay)
      )
    }

    return () => timers.forEach(clearTimeout)
  }, [days])
}
