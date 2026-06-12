// Copy the native home-screen widget into the Capacitor-generated Android
// project and register its <receiver> in AndroidManifest.xml.
// Run in CI after `npx cap add android`.
import { copyFileSync, mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('../', import.meta.url))
const src = root + 'native/android/'
const main = root + 'android/app/src/main/'
const pkgDir = main + 'java/com/bharattech/businessdiary/'

function put(from, toDir, file) {
  mkdirSync(toDir, { recursive: true })
  copyFileSync(src + from, toDir + file)
  console.log('copied', file)
}

put('java/DiaryWidget.java', pkgDir, 'DiaryWidget.java')
put('res/layout/widget_dev.xml', main + 'res/layout/', 'widget_dev.xml')
put('res/drawable/widget_bg.xml', main + 'res/drawable/', 'widget_bg.xml')
put('res/xml/diary_widget_info.xml', main + 'res/xml/', 'diary_widget_info.xml')

const manifestPath = main + 'AndroidManifest.xml'
let manifest = readFileSync(manifestPath, 'utf8')

if (!manifest.includes('.DiaryWidget')) {
  const receiver = `
        <receiver
            android:name=".DiaryWidget"
            android:exported="true">
            <intent-filter>
                <action android:name="android.appwidget.action.APPWIDGET_UPDATE" />
                <action android:name="com.bharattech.businessdiary.WIDGET_NEXT" />
            </intent-filter>
            <meta-data
                android:name="android.appwidget.provider"
                android:resource="@xml/diary_widget_info" />
        </receiver>
    </application>`
  manifest = manifest.replace('</application>', receiver)
  writeFileSync(manifestPath, manifest)
  console.log('registered DiaryWidget in AndroidManifest.xml')
} else {
  console.log('DiaryWidget already registered')
}

if (!existsSync(pkgDir + 'DiaryWidget.java')) {
  throw new Error('Widget Java was not placed — check the package path')
}
