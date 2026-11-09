// Minimal CDP driver: launch chromium, load a URL, run a script, report console errors.
// usage: node cdp.mjs <url> <script-file-or-inline-js>
import { spawn } from 'node:child_process'
import { readFileSync } from 'node:fs'

const URL_ = process.argv[2] || 'http://127.0.0.1:18790/'
const SCRIPT = process.argv[3] || '1'
const PORT = 9333 + Math.floor(Math.random() * 400)

const chrome = spawn('chromium', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
  `--remote-debugging-port=${PORT}`, '--user-data-dir=/tmp/cdp-' + PORT, 'about:blank',
], { stdio: ['ignore', 'ignore', 'ignore'] })

const sleep = ms => new Promise(r => setTimeout(r, ms))

async function getWsUrl() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/list`)
      const j = await r.json()
      const page = j.find(t => t.type === 'page')
      if (page?.webSocketDebuggerUrl) return page.webSocketDebuggerUrl
    } catch {}
    await sleep(150)
  }
  throw new Error('no devtools target')
}

const ws = new WebSocket(await getWsUrl())
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej })

let id = 0
const pending = new Map()
const errors = []
const logs = []

ws.onmessage = ev => {
  const m = JSON.parse(ev.data)
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); return }
  if (m.method === 'Runtime.exceptionThrown') {
    const d = m.params.exceptionDetails
    errors.push((d.exception?.description || d.text || 'exception').split('\n')[0])
  }
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
    errors.push('console.error: ' + m.params.args.map(a => a.value ?? a.description ?? '').join(' '))
  }
  if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') {
    errors.push('log: ' + m.params.entry.text)
  }
}

const send = (method, params = {}) => new Promise(res => {
  const i = ++id
  pending.set(i, res)
  ws.send(JSON.stringify({ id: i, method, params }))
})

await send('Runtime.enable')
await send('Log.enable')
await send('Page.enable')
const VW=parseInt(process.env.VW||'0',10)
if(VW) await send('Emulation.setDeviceMetricsOverride',{width:VW,height:1200,deviceScaleFactor:1,mobile:false})
await send('Page.navigate', { url: URL_ })
await sleep(2500)

const code = SCRIPT.endsWith('.js') ? readFileSync(SCRIPT, 'utf8') : SCRIPT
const r = await send('Runtime.evaluate', {
  expression: `(async()=>{${code}})()`,
  awaitPromise: true, returnByValue: true,
})

const out = r.result?.result?.value
const exc = r.result?.exceptionDetails
console.log('=== RESULT ===')
console.log(typeof out === 'string' ? out : JSON.stringify(out, null, 1))
if (exc) console.log('=== EVAL EXCEPTION ===\n' + (exc.exception?.description || exc.text))
console.log('=== PAGE ERRORS (' + errors.length + ') ===')
for (const e of [...new Set(errors)]) console.log(' - ' + e)

ws.close()
chrome.kill('SIGKILL')
process.exit(0)
