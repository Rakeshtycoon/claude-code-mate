// Lock APK signing to the committed keystore by injecting an explicit
// signingConfig into the Capacitor-generated android/app/build.gradle.
// This makes the signature identical for every build (so updates install
// over the top), instead of relying on the default ~/.android/debug.keystore
// which the runner may place elsewhere and regenerate each time.
import { copyFileSync, readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../', import.meta.url))
copyFileSync(root + 'ci/debug.keystore', root + 'android/app/diary.keystore')

const gradlePath = root + 'android/app/build.gradle'
let g = readFileSync(gradlePath, 'utf8')

if (g.includes('diary.keystore')) {
  console.log('signingConfig already present')
} else {
  const m = g.match(/(\n)([ \t]*)buildTypes\s*\{/)
  if (!m) throw new Error('Could not find buildTypes block in build.gradle')
  const i = m[2] // indentation
  const block =
    `${m[1]}${i}signingConfigs {\n` +
    `${i}    debug {\n` +
    `${i}        storeFile file('diary.keystore')\n` +
    `${i}        storePassword 'android'\n` +
    `${i}        keyAlias 'androiddebugkey'\n` +
    `${i}        keyPassword 'android'\n` +
    `${i}    }\n` +
    `${i}}\n` +
    `${i}buildTypes {`
  g = g.replace(/(\n)([ \t]*)buildTypes\s*\{/, block)
  writeFileSync(gradlePath, g)
  console.log('Injected explicit debug signingConfig -> diary.keystore')
}
