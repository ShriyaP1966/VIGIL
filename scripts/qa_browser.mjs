// Real-browser QA for the built frontend (headless Edge or Chrome over the DevTools protocol, no dependencies).
//
//   node scripts/qa_browser.mjs --dist frontend/dist --edge "<path to msedge.exe>" --profile <empty temp dir> [--backend http://127.0.0.1:8765]
//
// Without --backend the app runs in the hosted static-demo mode (the /api path answers 404, exactly like the static
// host). With --backend, /api/* is proxied to a running backend and the app runs in live mode.
// Checks: every route loads with no console error or uncaught exception, no horizontal scroll at 390 px and 1280 px,
// the main interactions work, the core workflow is reachable by keyboard alone with a visible focus ring, and a text
// contrast audit (WCAG AA 4.5:1, 3:1 for large text) finds no failing visible text. Exits 1 on any failure.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i > 0 ? process.argv[i + 1] : d; };
const dist = path.resolve(arg('dist', 'frontend/dist'));
const edgeExe = arg('edge');
const profile = arg('profile');
const backend = arg('backend', '');
const port = Number(arg('port', '9444'));
const MODE = backend ? 'live' : 'static';
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.csv': 'text/csv', '.svg': 'image/svg+xml', '.png': 'image/png' };

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://x');
  if (url.pathname.startsWith('/api/')) {
    if (!backend) { res.writeHead(404); return res.end('not found'); }
    try {
      const body = ['POST', 'PUT', 'DELETE'].includes(req.method) ? Buffer.concat(await req.toArray()) : undefined;
      const r = await fetch(backend + req.url, { method: req.method, headers: { 'content-type': req.headers['content-type'] || 'application/json' }, body: body?.length ? body : undefined });
      res.writeHead(r.status, { 'content-type': r.headers.get('content-type') || 'application/json' });
      return res.end(Buffer.from(await r.arrayBuffer()));
    } catch { res.writeHead(502); return res.end('bad gateway'); }
  }
  const file = path.join(dist, decodeURIComponent(url.pathname));
  if (url.pathname !== '/' && file.startsWith(dist) && fs.existsSync(file) && fs.statSync(file).isFile()) {
    res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream' });
    return fs.createReadStream(file).pipe(res);
  }
  if (/^\/(demo-data|assets)\//.test(url.pathname)) { res.writeHead(404); return res.end('not found'); }
  res.writeHead(200, { 'content-type': 'text/html' });
  fs.createReadStream(path.join(dist, 'index.html')).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}`;

const edge = spawn(edgeExe, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
let targets;
for (let i = 0; i < 80; i++) {
  try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (targets.some(t => t.type === 'page')) break; } catch {}
  await new Promise(r => setTimeout(r, 250));
}
const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map(); const events = [];
ws.addEventListener('message', e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } else if (m.method) events.push(m);
});
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 300)); return r.result.result.value; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const results = [];
const check = (name, ok, detail = '') => { results.push({ name, ok }); console.log(`${ok ? 'PASS' : 'FAIL'}  [${MODE}] ${name}${detail ? '  -> ' + detail : ''}`); };
const waitFor = async (expr, ms = 10000) => { const t = Date.now(); while (Date.now() - t < ms) { try { if (await ev(expr)) return true; } catch {} await sleep(150); } return false; };
const goto = async (p) => { events.length = 0; await send('Page.navigate', { url: base + p }); await sleep(300); await waitFor("document.readyState==='complete' && !!document.querySelector('#root > *')"); await sleep(900); };
const click = (sel) => ev(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); if(!e) return false; e.click(); return true;})()`);
const textOf = (sel) => ev(`document.querySelector(${JSON.stringify(sel)})?.innerText ?? null`);
const key = async (k, code = k) => { await send('Input.dispatchKeyEvent', { type: 'keyDown', key: k, code, windowsVirtualKeyCode: k === 'Tab' ? 9 : k === 'Enter' ? 13 : k === 'ArrowRight' ? 39 : k === 'Escape' ? 27 : 0 }); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code }); };
const problems = () => events.filter(e =>
  (e.method === 'Runtime.exceptionThrown') ||
  (e.method === 'Runtime.consoleAPICalled' && e.params.type === 'error') ||
  (e.method === 'Log.entryAdded' && e.params.entry.level === 'error' && !/api\/v1\/health/.test(e.params.entry.url || '') && !/health/.test(e.params.entry.text || '')))
  .map(e => JSON.stringify(e.params).slice(0, 200));
const overflow = `(()=>document.documentElement.scrollWidth - innerWidth)()`;

await send('Page.enable'); await send('Runtime.enable'); await send('Log.enable'); await send('Network.enable');

const ROUTES = ['/', '/incidents', '/incidents/new', '/incidents/1', '/graph', '/campaigns', '/campaigns/1', '/scenarios', '/simulated-call', '/reports', '/settings', '/nope'];

// ---------- every route: loads, no console errors, no horizontal scroll, has a heading ----------
for (const [w, h, tag] of [[1280, 800, 'desktop'], [390, 844, 'phone']]) {
  await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: w < 500 });
  for (const r of ROUTES) {
    await goto(r);
    const bad = problems();
    const o = await ev(overflow);
    const heading = await ev(`!!document.querySelector('main h1')`);
    const body = await ev(`document.body.innerText`);
    check(`${tag} ${r}: no console errors, no sideways scroll, has a heading`, bad.length === 0 && o <= 0 && heading, `${bad[0] || ''} overflow=${o} h1=${heading}`);
    if (r === '/nope') check(`${tag} /nope shows page not found`, /Page not found/.test(body));
  }
}
await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });

// ---------- Investigations ----------
await goto('/incidents');
const total = await ev(`document.querySelectorAll('ul[aria-label="Investigations"] > li').length`);
check('investigations: lists the cases', total >= 1, `${total}`);
await ev(`(()=>{const i=document.querySelector('input[type=search]'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,'customs'); i.dispatchEvent(new Event('input',{bubbles:true}));})()`);
await sleep(300);
const filtered = await ev(`document.querySelectorAll('ul[aria-label="Investigations"] > li').length`);
check('investigations: search narrows the list', filtered >= 1 && filtered < total, `${filtered} of ${total}`);
await ev(`(()=>{const i=document.querySelector('input[type=search]'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,'zzzz-no-match'); i.dispatchEvent(new Event('input',{bubbles:true}));})()`);
await sleep(300);
check('investigations: empty-search state offers to clear filters', /No investigation matches/.test(await ev('document.body.innerText')));
await click('main button.underline, main button[class*="underline"]'); await sleep(300);
check('investigations: clearing filters restores the list', (await ev(`document.querySelectorAll('ul[aria-label="Investigations"] > li').length`)) === total);
await ev(`[...document.querySelectorAll('button[aria-pressed]')].find(b=>/CRITICAL/.test(b.innerText))?.click()`); await sleep(300);
const crit = await ev(`document.querySelectorAll('ul[aria-label="Investigations"] > li').length`);
check('investigations: the risk-level filter works', crit < total, `${crit}`);

// ---------- Scenario Lab ----------
await goto('/scenarios');
check('scenario lab: lists scenarios', (await ev(`document.querySelectorAll('nav[aria-label="Scenarios"] button').length`)) >= 10);
await waitFor(`/Expected and actual/.test(document.body.innerText)`);
check('scenario lab: first scenario runs and shows expected vs actual', /Expected and actual/.test(await ev('document.body.innerText')));
const before = await ev(`document.querySelector('#rotation').value`);
await ev(`document.querySelector('#rotation').focus()`);
await key('ArrowRight'); await sleep(900);
const after = await ev(`document.querySelector('#rotation').value`);
check('scenario lab: the rotation slider moves from the keyboard and re-runs', before !== after, `${before} -> ${after}`);
await click('button:has(svg.lucide-rotate-ccw)'); await sleep(1200);
check('scenario lab: replay reports an identical, deterministic result', /Replay is identical/.test(await ev('document.body.innerText')));
await ev(`[...document.querySelectorAll('nav[aria-label="Scenarios"] button')].find(b=>/injection/i.test(b.innerText))?.click()`); await sleep(1500);
check('scenario lab: a non-rotation scenario disables the slider', await ev(`document.querySelector('#rotation').disabled`));

// ---------- Simulated call ----------
await goto('/simulated-call');
check('simulated call: shows the simulation disclaimer', /does not intercept or listen to real calls/.test(await ev('document.body.innerText')));
await click('button:has(svg.lucide-skip-forward)'); await sleep(900);
await click('button:has(svg.lucide-skip-forward)'); await sleep(900);
await click('button:has(svg.lucide-skip-forward)'); await sleep(900);
const lit = await ev(`document.querySelectorAll('#sim-stages ~ ol li.border-accent-primary, section[aria-labelledby="sim-stages"] li.border-accent-primary').length`);
check('simulated call: stages light up as turns arrive', lit >= 2, `${lit} stages lit after 3 turns`);
check('simulated call: risk meter and guidance in English and Hindi', await ev(`!!document.querySelector('[role=meter]') && !!document.querySelector('ul[lang=hi] li') && !!document.querySelector('ul[lang=en] li')`));
await ev(`(()=>{const s=document.querySelector('select'); const set=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set; set.call(s,'injection_attempt'); s.dispatchEvent(new Event('change',{bubbles:true}));})()`); await sleep(500);
await ev(`[...document.querySelectorAll('select')][1].value='2'; [...document.querySelectorAll('select')][1].dispatchEvent(new Event('change',{bubbles:true}))`);
await click('button:has(svg.lucide-play)');
check('simulated call: playback runs to the end by itself', await waitFor(`/script finished/.test(document.body.innerText)`, 30000));
check('simulated call: the injection attempt fires the safety badge', /Manipulation attempt detected and ignored/.test(await ev('document.body.innerText')));
check('simulated call: no console errors during playback', problems().length === 0, problems()[0] || '');

// ---------- Reports ----------
await goto('/reports');
await waitFor(`/1. Observed facts/.test(document.body.innerText)`);
check('reports: five separate sections are shown', await ev(`['1. Observed facts','2. Model inferences','3. Analyst actions','4. Counter-evidence','5. Limitations'].every(t=>document.body.innerText.includes(t))`));
await ev(`window.__dl=[]; HTMLAnchorElement.prototype.click=function(){ window.__dl.push(this.download); }; URL.createObjectURL=()=>'blob:x';`);
await click('button:has(svg.lucide-file-json)'); await sleep(600);
await click('button:has(svg.lucide-file-spreadsheet)'); await sleep(800);
const dl = await ev('window.__dl');
const rid = await ev(`document.querySelector('main select').value`);       // the case the page selected first
check('reports: JSON and CSV downloads are produced', dl.includes(`vigil_report_incident_${rid}.json`) && dl.includes(`vigil_report_incident_${rid}.csv`), JSON.stringify(dl));
check('reports: a success toast is announced', new RegExp(`Saved vigil_report_incident_${rid}`).test(await ev('document.body.innerText')));

// ---------- keyboard-only workflow (reseed first in live mode is not needed: static data is always present) ----------
if (MODE === 'static') {
  await goto('/');
  await ev(`document.body.focus(); document.activeElement.blur()`);
  let reached = false;
  for (let i = 0; i < 25 && !reached; i++) {
    await key('Tab');
    reached = await ev(`document.activeElement?.getAttribute('href')==='/incidents' && document.activeElement.closest('#app-sidebar')!==null`);
  }
  check('keyboard: Tab reaches the Investigations link in the sidebar', reached);
  const ring = await ev(`(()=>{const s=getComputedStyle(document.activeElement); return s.boxShadow!=='none' || s.outlineStyle!=='none'})()`);
  check('keyboard: the focused link has a visible focus ring', ring);
  await key('Enter'); await sleep(900);
  check('keyboard: Enter opens the Investigations page', (await ev('location.pathname')) === '/incidents');
  let inList = false;
  for (let i = 0; i < 30 && !inList; i++) { await key('Tab'); inList = await ev(`!!document.activeElement?.closest('ul[aria-label="Investigations"]')`); }
  check('keyboard: Tab reaches a case in the list', inList);
  await key('Enter'); await sleep(1200);
  check('keyboard: Enter opens that case', /^\/incidents\/\d+$/.test(await ev('location.pathname')));
  await goto('/graph?assoc=1'); await sleep(800);
  check('keyboard: the evidence inspector opens from a link and Escape closes it', await ev(`!!document.querySelector('aside[aria-label="Evidence inspector"]')`));
  await key('Escape'); await sleep(600);
  check('keyboard: Escape closes the inspector', await ev(`!document.querySelector('aside[aria-label="Evidence inspector"]')`));
}

// ---------- contrast audit (WCAG AA) ----------
const AUDIT = `(()=>{
  const parse = c => { const m = c.match(/rgba?\\(([^)]+)\\)/); if(!m) return null; const p=m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return {r:p[0],g:p[1],b:p[2],a:p[3]===undefined?1:p[3]}; };
  const over = (top, bot) => ({ r: top.r*top.a+bot.r*(1-top.a), g: top.g*top.a+bot.g*(1-top.a), b: top.b*top.a+bot.b*(1-top.a), a: 1 });
  const lum = c => { const f=v=>{v/=255; return v<=0.03928? v/12.92 : Math.pow((v+0.055)/1.055,2.4)}; return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b); };
  const bgOf = el => { const stack=[]; for(let e=el;e;e=e.parentElement){ const c=parse(getComputedStyle(e).backgroundColor); if(c&&c.a>0) stack.push(c); if(c&&c.a===1) break; } let acc={r:255,g:255,b:255,a:1}; for(let i=stack.length-1;i>=0;i--) acc=over(stack[i],acc); return acc; };
  const bad=[]; const seen=new Set();
  const walker=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for(let n; (n=walker.nextNode());){
    const t=n.textContent.trim(); const el=n.parentElement; if(!t||!el||seen.has(el)) continue; seen.add(el);
    const cs=getComputedStyle(el); const r=el.getBoundingClientRect();
    if(cs.visibility==='hidden'||cs.display==='none'||+cs.opacity===0||r.width===0||r.height===0) continue;
    if(el.closest('[aria-hidden=true], .sr-only, [disabled], option')) continue;
    let fg=parse(cs.color); if(!fg) continue; let o=1; for(let e=el;e;e=e.parentElement){ o*=+getComputedStyle(e).opacity; }
    const bg=bgOf(el); fg=over({...fg,a:fg.a*o}, bg);
    const L1=lum(fg), L2=lum(bg); const ratio=(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
    const px=parseFloat(cs.fontSize); const bold=parseInt(cs.fontWeight)>=700; const large = px>=24 || (px>=18.66&&bold);
    if(ratio < (large?3:4.5)) bad.push({ratio:+ratio.toFixed(2), text:t.slice(0,40), cls:(el.className||'').toString().slice(0,60)});
  }
  return bad; })()`;
const auditRoutes = ['/', '/incidents', '/graph', '/campaigns', '/scenarios', '/simulated-call', '/reports', '/settings', '/incidents/1'];
let contrastFailures = 0; const sample = []; const distinct = new Set();
for (const r of auditRoutes) {
  await goto(r);
  if (r === '/simulated-call') { await click('button:has(svg.lucide-skip-forward)'); await sleep(800); await click('button:has(svg.lucide-skip-forward)'); await sleep(800); }
  const bad = await ev(AUDIT);
  contrastFailures += bad.length; for (const b of bad) distinct.add(b.ratio + ' ' + b.cls.split(' ').filter(c => /^(text-|bg-)/.test(c)).join(' '));
  for (const b of bad.slice(0, 3)) sample.push(`${r} ${b.ratio}:1 "${b.text}" ${b.cls}`);
}
if (distinct.size) console.log('  failing combinations (ratio, classes):\n   ' + [...distinct].slice(0, 25).join('\n   '));
check('contrast: no visible text below WCAG AA on the main pages', contrastFailures === 0, contrastFailures ? `${contrastFailures} elements; e.g. ${sample.slice(0, 6).join(' | ')}` : '');

// ---------- Settings (last: in live mode it erases the data on purpose) ----------
await goto('/settings');
const disabled = await ev(`[...document.querySelectorAll('button')].find(b=>/Clear all local data/.test(b.innerText))?.disabled`);
if (MODE === 'static') {
  check('settings: clearing data is disabled in the hosted demo, with an explanation', disabled === true && /stores no data/.test(await ev('document.body.innerText')));
} else {
  check('settings: clear data is available in live mode', disabled === false);
  await ev(`[...document.querySelectorAll('button')].find(b=>/Clear all local data/.test(b.innerText)).click()`); await sleep(300);
  check('settings: a confirmation step comes first', /Erase everything now/.test(await ev('document.body.innerText')));
  await ev(`[...document.querySelectorAll('button')].find(b=>/Yes, erase all data/.test(b.innerText)).click()`); await sleep(1200);
  check('settings: erasing shows a success toast', /All local investigation records were erased/.test(await ev('document.body.innerText')));
  await goto('/incidents');
  check('settings: the investigations list is empty afterwards', /No investigations yet/.test(await ev('document.body.innerText')));
}


const failed = results.filter(r => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed (${MODE} mode)`);
await send('Browser.close').catch(() => {});
server.close(); ws.close();
setTimeout(() => process.exit(failed ? 1 : 0), 500);
