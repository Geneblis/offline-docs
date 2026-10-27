(()=>{'use strict';
const $=s=>document.querySelector(s),$$=s=>Array.from(document.querySelectorAll(s));
const pages=$$('.doc-page');const links=$$('.nav-item');const toc=$('#toc-items');const dialog=$('#search-overlay');const input=$('#search-input');const results=$('#search-results');
let activePage=pages[0];let selection=0;let hits=[];
function navigate(id,scroll=true){
  const target=document.getElementById(id);if(!target)return;
  const page=target.classList.contains('doc-page')?target:target.closest('.doc-page');if(!page)return;
  pages.forEach(p=>{p.hidden=p!==page});activePage=page;
  links.forEach(a=>{const on=a.dataset.page===page.id;a.classList.toggle('active',on);if(on)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});
  buildToc(page);document.body.classList.remove('nav-open');
  if(location.hash!=='#'+encodeURIComponent(id)){try{history.replaceState(null,'','#'+encodeURIComponent(id))}catch{location.hash=encodeURIComponent(id)}}
  if(scroll){if(page===target)window.scrollTo({top:0,behavior:'instant'});else requestAnimationFrame(()=>target.scrollIntoView({block:'start',behavior:'instant'}))}
  document.title=(page.dataset.title||'Documentation')+' · '+document.documentElement.dataset.siteTitle;
}
function buildToc(page){
  toc.textContent='';const hs=Array.from(page.querySelectorAll('h2,h3,h4'));
  if(!hs.length){toc.innerHTML='<li class="toc-placeholder">No sections</li>';return}
  hs.forEach(h=>{const li=document.createElement('li');const a=document.createElement('a');a.href='#'+encodeURIComponent(h.id);a.textContent=h.textContent;a.className=h.tagName==='H3'?'sub':h.tagName==='H4'?'deep':'';a.addEventListener('click',e=>{e.preventDefault();navigate(h.id)});li.append(a);toc.append(li)})
}
function navigateHash(){let id='';try{id=decodeURIComponent(location.hash.slice(1))}catch{};if(!document.getElementById(id))id=pages[0].id;navigate(id,false);if(id!==pages[0].id)requestAnimationFrame(()=>document.getElementById(id)?.scrollIntoView({block:'start'}))}
links.forEach(a=>a.addEventListener('click',e=>{e.preventDefault();navigate(a.dataset.page)}));
document.addEventListener('click',e=>{const a=e.target.closest('a[href^="#"]');if(!a||a.classList.contains('nav-item')||a.closest('.toc'))return;const id=decodeURIComponent(a.getAttribute('href').slice(1));if(document.getElementById(id)){e.preventDefault();navigate(id)}});
window.addEventListener('hashchange',navigateHash);
const toggle=$('#theme-toggle');function applyTheme(t){document.documentElement.dataset.theme=t;toggle.setAttribute('aria-label',t==='dark'?'Switch to light theme':'Switch to dark theme');try{localStorage.setItem('offline-docs-theme',t)}catch{}}
try{applyTheme(localStorage.getItem('offline-docs-theme')||'dark')}catch{applyTheme('dark')}
toggle.addEventListener('click',()=>applyTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
$('#menu-toggle').addEventListener('click',()=>document.body.classList.toggle('nav-open'));
const database=[];
pages.forEach(page=>{
  const title=page.dataset.title||page.id;const body=page.textContent.replace(/\s+/g,' ').trim();
  database.push({page:page.id,id:page.id,title,sub:'Page',text:body.slice(0,40000)});
  page.querySelectorAll('h2,h3,h4').forEach(h=>{let text='';let n=h.nextElementSibling;let depth=Number(h.tagName[1]);while(n&&!( /^H[1-6]$/.test(n.tagName)&&Number(n.tagName[1])<=depth)){text+=' '+n.textContent;n=n.nextElementSibling;if(text.length>4000)break}database.push({page:page.id,id:h.id,title:h.textContent.trim(),sub:title,text:text.trim()})})
});
function score(record,q){const s=q.toLowerCase(),title=record.title.toLowerCase(),desc=record.sub.toLowerCase(),body=record.text.toLowerCase();if(title===s)return 1000;if(title.startsWith(s))return 180;if(title.includes(s))return 120;if(desc.includes(s))return 65;if(body.includes(s))return 12;const terms=s.split(/\s+/).filter(Boolean);if(terms.length>1&&terms.every(w=>(title+' '+desc+' '+body).includes(w)))return 5;return 0}
function render(){const query=input.value.trim();results.textContent='';selection=0;hits=[];if(!query){const empty=document.createElement('div');empty.className='search-empty';empty.textContent='Search titles, functions and documentation content.';results.append(empty);return}
  hits=database.map(x=>({...x,score:score(x,query)})).filter(x=>x.score>0).sort((a,b)=>b.score-a.score).slice(0,35);
  if(!hits.length){const none=document.createElement('div');none.className='search-empty';none.textContent='No results found.';results.append(none);return}
  hits.forEach((x,i)=>{const a=document.createElement('a');a.href='#'+encodeURIComponent(x.id);a.className='result'+(i===0?' selected':'');a.setAttribute('role','option');const t=document.createElement('div');t.className='result-title';t.textContent=x.title;const d=document.createElement('div');d.className='result-meta';d.textContent=x.sub+(x.text?' · '+x.text.slice(0,125):'');a.append(t,d);a.addEventListener('click',e=>{e.preventDefault();close();navigate(x.id)});results.append(a)})
}
function open(){dialog.hidden=false;input.value='';render();setTimeout(()=>input.focus(),0)}function close(){dialog.hidden=true;input.value=''}
$('#open-search').addEventListener('click',open);$('#search-close').addEventListener('click',close);dialog.addEventListener('click',e=>{if(e.target===dialog)close()});input.addEventListener('input',render);
function highlight(){results.querySelectorAll('.result').forEach((x,i)=>x.classList.toggle('selected',i===selection));results.querySelector('.result.selected')?.scrollIntoView({block:'nearest'})}
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();dialog.hidden?open():close()}else if(e.key==='Escape'&&!dialog.hidden){close()}else if(!dialog.hidden&&e.key==='ArrowDown'){e.preventDefault();selection=Math.min(hits.length-1,selection+1);highlight()}else if(!dialog.hidden&&e.key==='ArrowUp'){e.preventDefault();selection=Math.max(0,selection-1);highlight()}else if(!dialog.hidden&&e.key==='Enter'&&hits.length){e.preventDefault();const id=hits[selection].id;close();navigate(id)}});
navigateHash();
})();
