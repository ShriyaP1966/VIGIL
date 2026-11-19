// Final check of the DEPLOYED site (default: the live Vercel demo) in headless Edge/Chrome, no dependencies:
// deep links and refresh, mobile layout (no sideways scroll, drawer closed by default), the synthetic-data labelling,
// no console errors on any route, and the static-first behaviour (the site works with no backend).
//
//   node scripts/check_deployed.mjs --edge "<msedge.exe>" --profile <empty temp dir> [--url https://vigil-demo-eta.vercel.app]
// This does NOT replace a check from a real phone on cellular data in a private window (done by the owner).
import { spawn } from 'node:child_process';

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i > 0 ? process.argv[i + 1] : d; };
const base = arg('url', 'https://vigil-demo-eta.vercel.app').replace(/\/$/, '');
const edgeExe = arg('edge'); const profile = arg('profile'); const port = Number(arg('port', '9666'));

const edge = spawn(edgeExe, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
let targets;
for (let i = 0; i < 80; i++) {
  try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (targets.some(t => t.type === 'page')) break; } catch {}
  await new Promise(r => setTimeout(r, 250));
}
const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map(); const events = [];
ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } else if (m.method) events.push(m); });
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 200)); return r.result.result.value; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const waitFor = async (expr, ms = 15000) => { const t = Date.now(); while (Date.now() - t < ms) { try { if (await ev(expr)) return true; } catch {} await sleep(200); } return false; };
const goto = async (p) => { events.length = 0; await send('Page.navigate', { url: base + p }); await sleep(400); await waitFor("document.readyState==='complete' && !!document.querySelector('#root > *')"); await sleep(1200); };
const results = [];
const check = (name, ok, detail = '') => { results.push(ok); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  -> ' + detail : ''}`); };
const problems = () => events.filter(e => e.method === 'Runtime.exceptionThrown' || (e.method === 'Runtime.consoleAPICalled' && e.params.type === 'error') ||
  (e.method === 'Log.entryAdded' && e.params.entry.level === 'error' && !/health/.test((e.params.entry.url || '') + (e.params.entry.text || '')))).map(e => JSON.stringify(e.params).slice(0, 160));
const overflow = `(()=>document.documentElement.scrollWidth - innerWidth)()`;

await send('Page.enable'); await send('Runtime.enable'); await send('Log.enable'); await send('Network.enable');
console.log(`Checking ${base}\n`);

const ROUTES = ['/', '/incidents', '/incidents/new', '/incidents/1', '/graph', '/campaigns', '/campaigns/1', '/scenarios', '/simulated-call', '/reports', '/settings', '/nope'];
for (const [w, h, tag, mobile] of [[1280, 800, 'desktop', false], [390, 844, 'phone 390px', true]]) {
  await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile });
  for (const r of ROUTES) {
    await goto(r);
    await waitFor(`!!document.querySelector('main h1')`, 10000);      // the graph page is a lazily loaded chunk
    const bad = problems(), o = await ev(overflow), h1 = await ev(`!!document.querySelector('main h1')`);
    check(`${tag} ${r}: loads, no console error, no sideways scroll, has a heading`, bad.length === 0 && o <= 0 && h1, `${bad[0] || ''} overflow=${o}`);
  }
  await goto('/');
  const badge = await ev(`document.querySelector('header').innerText.replace(/\\s+/g,' ')`);
  check(`${tag}: the top bar labels the data as synthetic`, /synthetic/i.test(badge), badge);
  check(`${tag}: the overview carries the synthetic-data notice`, /Synthetic data:/.test(await ev('document.body.innerText')));
}
// mobile drawer
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
await goto('/incidents');
const vis = (sel) => `(()=>{const e=document.querySelector('${sel}'); if(!e) return false; const s=getComputedStyle(e); const r=e.getBoundingClientRect(); return s.visibility!=='hidden' && r.right>0 && r.left<innerWidth;})()`;
check('phone: the navigation drawer is closed by default', !(await ev(vis('#app-sidebar'))));
await ev(`document.querySelector('button[aria-label="Open navigation menu"]').click()`); await sleep(500);
check('phone: the hamburger opens the drawer', await ev(vis('#app-sidebar')));
await ev(`document.querySelector('#app-sidebar a[href="/graph"]').click()`); await sleep(700);
check('phone: tapping a link navigates and closes the drawer', (await ev('location.pathname')) === '/graph' && !(await ev(vis('#app-sidebar'))));

// deep links and refresh keep the page
await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
for (const [p, expect] of [['/campaigns/1', /Playbook alignment|Campaign/i], ['/incidents/1', /Digital Arrest|Tactic/i], ['/scenarios', /Scenario Lab/], ['/simulated-call', /Simulation/], ['/reports', /Investigation Reports/], ['/graph?assoc=1', /Evidence|OBSERVED/i]]) {
  await goto(p); await send('Page.reload'); await sleep(1800);
  const where = await ev('location.pathname + location.search');
  check(`deep link ${p} survives a refresh`, where === p && expect.test(await ev('document.body.innerText')), where);
}
// content and static-first behaviour
await goto('/simulated-call');
check('simulated call shows the "does not intercept or listen to real calls" notice', /does not intercept or listen to real calls/.test(await ev('document.body.innerText')));
const health = await ev(`fetch('/api/v1/health').then(r => r.status).catch(() => 0)`);
check('no backend is needed: /api/v1/health is not served, yet every page works from precomputed data', health === 404, `status ${health}`);
const data = await ev(`Promise.all(['incidents.json','scenarios.json','simulations.json','report_1.csv'].map(f => fetch('/demo-data/'+f).then(r => r.status)))`);
check('precomputed data files are served', data.every(s => s === 200), JSON.stringify(data));

const failed = results.filter(r => !r).length;
console.log(`\n${results.length - failed}/${results.length} checks passed against ${base}`);
await send('Browser.close').catch(() => {});
ws.close();
setTimeout(() => process.exit(failed ? 1 : 0), 300);
