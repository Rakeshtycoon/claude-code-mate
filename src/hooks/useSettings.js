import { useLocalStorage } from './useLocalStorage.js'
import { DEFAULT_SETTINGS } from '../lib/settings.js'

/**
 * Read app settings merged over the defaults, so newly added settings keys
 * always have a sensible value even for older stored data.
 * Returns [settings, setSettings] like useLocalStorage.
 */
export function useSettings() {
  const [raw, setRaw] = useLocalStorage('bd.settings', DEFAULT_SETTINGS)
  const settings = { ...DEFAULT_SETTINGS, ...raw }
  if (!Array.isArray(settings.mantras) || settings.mantras.length === 0) {
    settings.mantras = DEFAULT_SETTINGS.mantras
  }
  return [settings, setRaw]
}
