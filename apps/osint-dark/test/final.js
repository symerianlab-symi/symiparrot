const vis=id=>{const e=document.getElementById(id);return e?getComputedStyle(e).display:'MISSING'};
const R={pass:[],fail:[]};
const ok=(n,c)=>{(c?R.pass:R.fail).push(n)};
// 1 boot
ok('boot: people view visible', vis('view-people')==='block');
ok('boot: badge READY', document.getElementById('mode').textContent==='READY');
// 2 roster
const rows=[...document.querySelectorAll('#people .person')];
ok('roster: has rows', rows.length>0);
ok('roster: rows have tabindex', rows.every(r=>r.getAttribute('tabindex')==='0'));
// 3 profile
rows[0].click(); await new Promise(r=>setTimeout(r,300));
ok('profile: visible after click', vis('view-profile')==='block');
ok('profile: people hidden', vis('view-people')==='none');
ok('profile: dossier rendered', document.getElementById('agentdossier').textContent.length>100);
ok('profile: markdown headings', document.querySelectorAll('#agentdossier .md-h1,#agentdossier .md-h2').length>0);
ok('profile: raw json present', document.getElementById('rawjson').textContent.length>50);
ok('profile: rerun buttons', document.querySelectorAll('#profile-head [data-rerun]').length===3);
// 4 back
document.getElementById('b-back').click(); await new Promise(r=>setTimeout(r,300));
ok('back: people visible', vis('view-people')==='block');
// 5 tabs
document.getElementById('tab-run').click(); await new Promise(r=>setTimeout(r,150));
ok('tab: run visible', vis('view-run')==='block');
ok('tab: people hidden', vis('view-people')==='none');
document.getElementById('tab-people').click(); await new Promise(r=>setTimeout(r,150));
ok('tab: people back', vis('view-people')==='block');
// 6 hints form
document.getElementById('tab-run').click();
ok('hints: 5 fields', document.querySelectorAll('#hints input').length===5);
ok('hints: apply button', !!document.getElementById('h-apply'));
// 7 new session keeps DOM
document.getElementById('b-new').click(); await new Promise(r=>setTimeout(r,200));
ok('new: views intact', !!document.getElementById('view-people')&&!!document.getElementById('view-run')&&!!document.getElementById('view-profile'));
ok('new: people visible', vis('view-people')==='block');
// 8 none match
document.getElementById('subject').value='QA Subject';
document.getElementById('b-none').click(); await new Promise(r=>setTimeout(r,400));
ok('none: badge NONE', document.getElementById('mode').textContent==='NONE');
// 9 save
document.getElementById('b-save').click(); await new Promise(r=>setTimeout(r,400));
ok('save: session listed', document.querySelectorAll('#sessions .ses').length>0);
// 10 ghost when empty
PEOPLE={}; peoplePaint();
ok('ghost: shows when empty', vis('ghost')==='flex');
await loadPeople();
ok('ghost: hides when populated', vis('ghost')==='none');
// 11 md5
ok('md5: known vector', md5('abc')==='900150983cd24fb0d6963f7d28e17f72');
// 12 markdown
const h=mdToHtml('# T\n## S\n- a\n- b\n**x** `y` https://e.com');
ok('md: h1', h.includes('md-h1'));
ok('md: list', h.includes('<ul>')&&h.includes('<li>'));
ok('md: bold', h.includes('<b>x</b>'));
ok('md: code', h.includes('<code>y</code>'));
ok('md: link', h.includes('<a href="https://e.com"'));
// 13 no error strip
ok('errors: strip hidden', getComputedStyle(document.getElementById('jserr')).display==='none');
return JSON.stringify({passed:R.pass.length,failed:R.fail.length,failures:R.fail},null,1);
