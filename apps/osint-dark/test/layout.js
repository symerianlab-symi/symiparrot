const R={};
await loadPeople();
document.querySelector('#people .person').click(); await new Promise(r=>setTimeout(r,400));
const g=document.querySelector('#profile-body .pgrid');
R.grid=g?{cols:getComputedStyle(g).gridTemplateColumns,width:Math.round(g.getBoundingClientRect().width)}:'none';
R.overflow={docW:document.documentElement.scrollWidth,winW:window.innerWidth,
  horizontal:document.documentElement.scrollWidth>window.innerWidth+2};
const cards=[...document.querySelectorAll('#profile-body .card')];
R.cardCount=cards.length;
R.cardWidths=[...new Set(cards.map(c=>Math.round(c.getBoundingClientRect().width)))];
R.headerH=Math.round(document.querySelector('#profile-head .card').getBoundingClientRect().height);
R.firstRowH=Math.round(document.querySelector('#profile-body .drow').getBoundingClientRect().height);
// expand a panel and confirm it does not overflow
const row=document.querySelector('#profile-body .drow.clickable');
row.click(); await new Promise(r=>setTimeout(r,200));
const p=document.getElementById(row.dataset.x);
R.panel={w:Math.round(p.getBoundingClientRect().width),overflowX:p.scrollWidth>p.clientWidth+2};
R.afterExpandOverflow=document.documentElement.scrollWidth>window.innerWidth+2;
// narrow viewport check
return JSON.stringify(R,null,1);
