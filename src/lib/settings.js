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

// Accent colour presets — applied to --pa-blue at runtime. A mix of deep and
// lighter/brighter shades; the sidebar text auto-adapts for light ones.
export const ACCENTS = [
  { key: 'blue', label: 'Blue', color: '#1e3a8a' },
  { key: 'indigo', label: 'Indigo', color: '#4338ca' },
  { key: 'violet', label: 'Violet', color: '#6d28d9' },
  { key: 'purple', label: 'Purple', color: '#9333ea' },
  { key: 'pink', label: 'Pink', color: '#be185d' },
  { key: 'rose', label: 'Rose', color: '#e11d48' },
  { key: 'maroon', label: 'Maroon', color: '#9f1239' },
  { key: 'orange', label: 'Orange', color: '#ea580c' },
  { key: 'amber', label: 'Amber', color: '#d97706' },
  { key: 'teal', label: 'Teal', color: '#0f766e' },
  { key: 'emerald', label: 'Emerald', color: '#059669' },
  { key: 'green', label: 'Green', color: '#15803d' },
  { key: 'sky', label: 'Sky', color: '#0284c7' },
  { key: 'cyan', label: 'Cyan', color: '#0891b2' },
  { key: 'slate', label: 'Slate', color: '#475569' },
  // Lighter options — sidebar switches to dark text automatically.
  { key: 'skylight', label: 'Light Blue', color: '#38bdf8' },
  { key: 'minty', label: 'Mint', color: '#34d399' },
  { key: 'sun', label: 'Sun', color: '#fbbf24' },
  { key: 'coral', label: 'Coral', color: '#fb7185' },
  { key: 'lavender', label: 'Lavender', color: '#a78bfa' },
]

export function accentColor(key) {
  return (ACCENTS.find((a) => a.key === key) || ACCENTS[0]).color
}

function rgb(hex) {
  const h = hex.replace('#', '')
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ]
}

function luminance(hex) {
  const [r, g, b] = rgb(hex)
  return 0.299 * r + 0.587 * g + 0.114 * b // 0–255
}

// True when a colour is light enough to need dark text on top of it.
export function isLightColor(hex) {
  return luminance(hex) > 150
}

// A version of the colour dark enough to read as heading text on white.
export function readableAccent(hex) {
  if (!isLightColor(hex)) return hex
  const [r, g, b] = rgb(hex).map((c) => Math.round(c * 0.55))
  return '#' + [r, g, b].map((c) => c.toString(16).padStart(2, '0')).join('')
}

export const DEFAULT_SETTINGS = {
  mantras: DEFAULT_MANTRAS,
  fyStartMonth: 4, // 1–12; April = start of the financial year by default
  accent: 'blue',
  widget: true, // home-screen widget (Android app)
}
