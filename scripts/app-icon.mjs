// Produce a 1024x1024 PNG from public/icon.svg for @capacitor/assets to turn
// into Android launcher icons. Run in CI (where sharp is installed).
import sharp from 'sharp'
import { readFileSync, mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const svg = readFileSync(new URL('../public/icon.svg', import.meta.url))
const dir = new URL('../assets/', import.meta.url)
mkdirSync(fileURLToPath(dir), { recursive: true })

await sharp(svg, { density: 512 })
  .resize(1024, 1024, { fit: 'cover' })
  .flatten({ background: '#ffffff' })
  .png()
  .toFile(fileURLToPath(new URL('icon.png', dir)))

console.log('wrote assets/icon.png (1024px)')
