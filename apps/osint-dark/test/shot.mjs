import { spawn } from 'node:child_process'
import { writeFileSync } from 'node:fs'
const URL_=process.argv[2], OUT=process.argv[3]||'/tmp/shot.png', CLICK=process.argv[4]||''
const PORT=9800+Math.floor(Math.random()*150)
const chrome=spawn('chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
  '--window-size=1500,2400',`--remote-debugging-port=${PORT}`,'--user-data-dir=/tmp/cdps-'+PORT,'about:blank'],{stdio:['ignore','ignore','ignore']})
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
let wsUrl
for(let i=0;i<60;i++){try{const j=await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();const p=j.find(t=>t.type==='page');if(p?.webSocketDebuggerUrl){wsUrl=p.webSocketDebuggerUrl;break}}catch{}await sleep(150)}
const ws=new WebSocket(wsUrl); await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j})
let id=0; const pend=new Map()
ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pend.has(m.id)){pend.get(m.id)(m);pend.delete(m.id)}}
const send=(method,params={})=>new Promise(res=>{const i=++id;pend.set(i,res);ws.send(JSON.stringify({id:i,method,params}))})
await send('Page.enable'); await send('Emulation.setDeviceMetricsOverride',{width:1500,height:2400,deviceScaleFactor:1,mobile:false})
await send('Page.navigate',{url:URL_}); await sleep(2500)
if(CLICK){await send('Runtime.evaluate',{expression:CLICK}); await sleep(1200)}
const r=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true})
writeFileSync(OUT,Buffer.from(r.result.data,'base64'))
console.log('wrote',OUT)
ws.close(); chrome.kill('SIGKILL'); process.exit(0)
