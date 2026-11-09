const RED='rgb(229, 72, 77)';
const R={redText:[],checked:0};
const audit=(sel,label)=>{const e=document.querySelector(sel);if(!e)return;
  R.checked++;const c=getComputedStyle(e).color;if(c===RED)R.redText.push(label+' ('+sel+')')};
// people view
audit('#people .person .pn','roster name');
audit('#people .person .pm','roster meta');
audit('#people .person .ps','roster snippet');
audit('#view-people .card h2','people heading');
// profile
await loadPeople();
document.querySelector('#people .person').click(); await new Promise(r=>setTimeout(r,300));
audit('.pname','profile name');audit('.prole','profile role');audit('.psummary','profile summary');
audit('#profile-body .card h2','section heading');audit('#profile-body .drow .dv','row value');
audit('#profile-body .drow .dl','row label');audit('#agentdossier .md-h1','md h1');
audit('#agentdossier .md-h2','md h2');audit('#agentdossier p','md paragraph');
audit('#profile-body a','link');
// run view
document.getElementById('tab-run').click(); await new Promise(r=>setTimeout(r,200));
audit('#view-run .card h2','run heading');audit('#hints .hrow','hint label');
audit('#telemetry .trow','telemetry label');
R.checkedCount=R.checked;
return JSON.stringify(R,null,1);
