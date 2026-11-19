// Captures the README screenshots from a running site (the live Vercel demo by default) with headless Edge/Chrome
// over the DevTools protocol, no dependencies. Synthetic data only. Each image is kept under 200 KB (PNG when it fits,
// otherwise JPEG at a lower quality).
//
//   node scripts/capture_screenshots.mjs --edge "<msedge.exe>" --profile <empty temp dir> [--url https://vigil-demo-eta.vercel.app] [--out docs/screenshots]
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const arg = (n, d) => { const i = process.argv.indexOf(`--${n}`); return i > 0 ? process.argv[i + 1] : d; };
const base = arg('url', 'https://vigil-demo-eta.vercel.app').replace(/\/$/, '');
const out = path.resolve(arg('out', 'docs/screenshots'));
const edgeExe = arg('edge'); const profile = arg('profile'); const port = Number(arg('port', '9555'));
const MAX = 200_000;
fs.mkdirSync(out, { recursive: true });

const edge = spawn(edgeExe, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--no-first-run', '--disable-gpu', 'about:blank'], { stdio: 'ignore' });
let targets;
for (let i = 0; i < 80; i++) {
  try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (targets.some(t => t.type === 'page')) break; } catch {}
  await new Promise(r => setTimeout(r, 250));
}
const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const pending = new Map();
ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 200)); return r.result.result.value; };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const waitFor = async (expr, ms = 15000) => { const t = Date.now(); while (Date.now() - t < ms) { try { if (await ev(expr)) return true; } catch {} await sleep(200); } return false; };
const goto = async (p) => { await send('Page.navigate', { url: base + p }); await sleep(400); await waitFor("document.readyState==='complete' && !!document.querySelector('#root > *')"); await sleep(1500); };
const click = (sel) => ev(`(()=>{const e=document.querySelector(${JSON.stringify(sel)}); if(!e) return false; e.click(); return true;})()`);

async function shoot(name, w, h, mobile = false) {
  await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile });
  await sleep(400);
  let png = Buffer.from((await send('Page.captureScreenshot', { format: 'png' })).result.data, 'base64');
  let file = `${name}.png`;
  if (png.length > MAX) {
    for (const q of [85, 75, 65, 55]) {
      const jpg = Buffer.from((await send('Page.captureScreenshot', { format: 'jpeg', quality: q })).result.data, 'base64');
      png = jpg; file = `${name}.jpg`;
      if (jpg.length <= MAX) break;
    }
  }
  fs.writeFileSync(path.join(out, file), png);
  console.log(`${png.length <= MAX ? 'OK  ' : 'BIG '} ${file} ${png.length} bytes`);
  return png.length <= MAX;
}

await send('Page.enable'); await send('Runtime.enable');
let ok = true;
await goto('/');                                  ok &= await shoot('01-overview', 1280, 800);
await goto('/incidents/1');                       ok &= await shoot('02-investigation-detail', 1280, 900);
await goto('/graph?assoc=1'); await sleep(1500);  ok &= await shoot('03-graph-and-evidence-inspector', 1600, 900);
await goto('/campaigns/1');                       ok &= await shoot('04-campaign-playbook-alignment', 1280, 1000);
await goto('/scenarios'); await waitFor(`/Expected and actual/.test(document.body.innerText)`);
await ev(`(()=>{const i=document.querySelector('#rotation'); const set=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set; set.call(i,'1'); i.dispatchEvent(new Event('input',{bubbles:true}));})()`);
await sleep(1500);                                ok &= await shoot('05-scenario-lab-rotation-1', 1280, 1000);
await goto('/simulated-call');
await ev(`(()=>{const s=document.querySelector('select'); const set=Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype,'value').set; set.call(s,'injection_attempt'); s.dispatchEvent(new Event('change',{bubbles:true}));})()`);
await sleep(600);
for (let i = 0; i < 5; i++) { await click('button:has(svg.lucide-skip-forward)'); await sleep(1200); }
                                                  ok &= await shoot('06-simulated-call-injection', 1280, 1000);
await goto('/reports'); await waitFor(`/1. Observed facts/.test(document.body.innerText)`);
                                                  ok &= await shoot('07-report', 1280, 1000);
await goto('/incidents'); await click('button[aria-label="Open navigation menu"]'); await sleep(600);
                                                  ok &= await shoot('08-mobile-drawer', 390, 844, true);

await send('Browser.close').catch(() => {});
ws.close();
setTimeout(() => process.exit(ok ? 0 : 1), 300);
