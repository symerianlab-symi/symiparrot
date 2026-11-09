const R={};
await loadPeople();
const row=[...document.querySelectorAll('#people .person')].find(e=>e.dataset.k==='Ryan Trimburger');
row.click(); await new Promise(r=>setTimeout(r,400));
R.sections=[...document.querySelectorAll('#profile-body .card h2')].map(h=>h.textContent.replace(/\s+/g,' ').trim());
R.header={name:document.querySelector('.pname')?.textContent,
  role:document.querySelector('.prole')?.textContent,
  meta:document.querySelector('.pmeta')?.textContent.replace(/\s+/g,' ').trim(),
  summary:!!document.querySelector('.psummary')};
R.rows=document.querySelectorAll('#profile-body .drow').length;
R.clickable=document.querySelectorAll('#profile-body .drow.clickable').length;
// expand the first clickable row
const first=document.querySelector('#profile-body .drow.clickable');
const pid=first.dataset.x;
first.click(); await new Promise(r=>setTimeout(r,150));
R.expand={panelId:pid,visible:document.getElementById(pid).style.display,
  content:document.getElementById(pid).textContent.replace(/\s+/g,' ').trim().slice(0,90),
  rowOpen:first.classList.contains('open')};
first.click(); await new Promise(r=>setTimeout(r,100));
R.collapse={visible:document.getElementById(pid).style.display};
// confidence panel
const conf=document.querySelector('#profile-head .conf');
if(conf){conf.click();await new Promise(r=>setTimeout(r,150));
  R.confPanel={visible:document.getElementById('confpanel').style.display,
    text:document.getElementById('confpanel').textContent.replace(/\s+/g,' ').trim().slice(0,80)}}
// raw toggle
const rt=document.getElementById('rawtoggle');
rt.click(); await new Promise(r=>setTimeout(r,100));
R.rawToggle={display:document.getElementById('rawjson').style.display,label:rt.textContent};
// COLOR AUDIT: is any body text red?
const RED='rgb(229, 72, 77)';
const check=sel=>{const e=document.querySelector(sel);return e?getComputedStyle(e).color:'MISSING'};
R.colors={bodyText:check('#profile-body .drow .dv'),heading:check('#profile-body .card h2'),
  mdH1:check('#agentdossier .md-h1'),mdH2:check('#agentdossier .md-h2'),
  link:check('#profile-body a'),name:check('.pname'),label:check('#profile-body .drow .dl')};
R.redText=[];
for(const sel of ['#profile-body .drow .dv','#profile-body .card h2','#agentdossier .md-h1','#agentdossier .md-h2','#profile-body a','.pname','#profile-body .drow .dl','.psummary','.prole']){
  const c=check(sel); if(c===RED) R.redText.push(sel);
}
return JSON.stringify(R,null,1);
