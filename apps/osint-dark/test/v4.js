const R={};
await loadPeople();
const row=[...document.querySelectorAll('#people .person')].find(e=>e.dataset.k==='Ryan Trimburger');
R.rosterMeta=row.querySelector('.pm').textContent;
row.click(); await new Promise(r=>setTimeout(r,400));
R.sections=[...document.querySelectorAll('#profile-body .card h2')].map(h=>h.textContent.replace(/\s+/g,' ').trim());
R.question=document.querySelector('.qblock')?.textContent.replace(/\s+/g,' ').trim().slice(0,120);
R.coverage={items:document.querySelectorAll('.covitem').length,
  done:document.querySelectorAll('.covitem.done').length,
  partial:document.querySelectorAll('.covitem.partial').length,
  gap:document.querySelectorAll('.covitem.gap').length};
R.pivots=document.querySelectorAll('.pivot').length;
R.ledgerRows=document.querySelectorAll('#profile-body table tbody tr').length;
R.probes=document.querySelectorAll('.probe').length;
R.negatives=document.querySelectorAll('.neg').length;
R.gaps=document.querySelectorAll('.gap').length;
// queue a probe
const pb=document.querySelector('.probe button');
if(pb){pb.click(); await new Promise(r=>setTimeout(r,500)); R.probeQueued={label:pb.textContent,disabled:pb.disabled,flash:document.getElementById('flash').textContent}}
// global ledger view
document.getElementById('tab-ledger').click(); await new Promise(r=>setTimeout(r,300));
R.ledgerView={visible:getComputedStyle(document.getElementById('view-ledger')).display,
  rows:document.querySelectorAll('#ledgerbody tbody tr').length,
  count:document.getElementById('ledger-count').textContent,
  subjects:document.querySelectorAll('#ledger-subject option').length,
  layers:document.querySelectorAll('#ledger-layer option').length};
// filter by layer
const ls=document.getElementById('ledger-layer'); ls.value='domain'; ls.onchange();
await new Promise(r=>setTimeout(r,200));
R.filtered={rows:document.querySelectorAll('#ledgerbody tbody tr').length,count:document.getElementById('ledger-count').textContent};
return JSON.stringify(R,null,1);
