// App-wide settings, stored under bd.settings. Anything configurable by the
// user (instead of hardcoded) has its default here.

export const DEFAULT_MANTRAS = [
  'Prayer / Gratitude',
  'Yoga / Walk / Exercise',
  'Affirmation',
  'Learn / Read',
  'Sharing',
  'Sales Report PA App',
  'Task Sheet Post in Group',
  'Growth Action',
]

// Accent colour presets — applied to --pa-blue at runtime.
export const ACCENTS = [
  { key: 'blue', label: 'Blue', color: '#1e3a8a' },
  { key: 'teal', label: 'Teal', color: '#0f766e' },
  { key: 'purple', label: 'Purple', color: '#6d28d9' },
  { key: 'green', label: 'Green', color: '#15803d' },
  { key: 'maroon', label: 'Maroon', color: '#9f1239' },
]

export function accentColor(key) {
  return (ACCENTS.find((a) => a.key === key) || ACCENTS[0]).color
}

export const DEFAULT_SETTINGS = {
  mantras: DEFAULT_MANTRAS,
  fyStartMonth: 4, // 1–12; April = start of the financial year by default
  accent: 'blue',
}
