import { spawn } from 'node:child_process'
const URL_=process.argv[2], PORT=9700+Math.floor(Math.random()*200)
const chrome=spawn('chromium',['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',`--remote-debugging-port=${PORT}`,'--user-data-dir=/tmp/cdpn-'+PORT,'about:blank'],{stdio:['ignore','ignore','ignore']})
const sleep=ms=>new Promise(r=>setTimeout(r,ms))
let wsUrl
for(let i=0;i<60;i++){try{const j=await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();const p=j.find(t=>t.type==='page');if(p?.webSocketDebuggerUrl){wsUrl=p.webSocketDebuggerUrl;break}}catch{}await sleep(150)}
const ws=new WebSocket(wsUrl); await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j})
let id=0; const pend=new Map(); const bad=[]
ws.onmessage=ev=>{const m=JSON.parse(ev.data)
  if(m.id&&pend.has(m.id)){pend.get(m.id)(m);pend.delete(m.id);return}
  if(m.method==='Network.responseReceived'){const r=m.params.response;if(r.status>=400)bad.push(r.status+' '+r.url.slice(0,120))}}
const send=(method,params={})=>new Promise(res=>{const i=++id;pend.set(i,res);ws.send(JSON.stringify({id:i,method,params}))})
await send('Network.enable'); await send('Page.enable')
await send('Page.navigate',{url:URL_}); await sleep(3000)
// click the person to exercise profile view
await send('Runtime.evaluate',{expression:`document.querySelector('#people .person')?.click()`})
await sleep(1500)
console.log('=== FAILED REQUESTS ===')
console.log(bad.length?[...new Set(bad)].join('\n'):'(none)')
ws.close(); chrome.kill('SIGKILL'); process.exit(0)
