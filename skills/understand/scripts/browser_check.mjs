// 렌더한 HTML 을 헤드리스 Chrome 으로 열어 모든 상호작용을 실제로 누르고, 기능마다 스크린샷을 찍는다.
// 쓰는 법: node browser_check.mjs <page.html> <스크린샷 폴더>
// 의존성: Chrome(또는 Chromium)과 Node 22 이상(내장 WebSocket). 바깥 패키지는 쓰지 않는다.
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const [, , page, outDir] = process.argv;
if (!page || !outDir) { console.error("쓰는 법: node browser_check.mjs <page.html> <스크린샷 폴더>"); process.exit(2); }
const CHROMES = [process.env.CHROME, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium", "/usr/bin/google-chrome", "/usr/bin/chromium"].filter(Boolean);
const chrome = CHROMES.find((c) => existsSync(c));
if (!chrome) { console.log("SKIP Chrome 이 없어 브라우저 검사를 못 했다"); process.exit(3); }
mkdirSync(outDir, { recursive: true });

const profile = mkdtempSync(join(tmpdir(), "understand-chrome-"));
const port = 9300 + Math.floor(Math.random() * 500);
const proc = spawn(chrome, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--no-first-run", "--hide-scrollbars", "--disable-gpu", "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let target;
for (let i = 0; i < 50 && !target; i++) {
  await sleep(100);
  try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === "page"); } catch {}
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let seq = 0;
const waiting = new Map();
const problems = [];
ws.addEventListener("message", (m) => {
  const msg = JSON.parse(m.data);
  if (msg.id && waiting.has(msg.id)) { waiting.get(msg.id)(msg); waiting.delete(msg.id); }
  if (msg.method === "Runtime.exceptionThrown") problems.push("예외: " + msg.params.exceptionDetails.text + " " + (msg.params.exceptionDetails.exception?.description || ""));
  if (msg.method === "Log.entryAdded" && msg.params.entry.level === "error") problems.push("콘솔 오류: " + msg.params.entry.text);
  if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") problems.push("console.error: " + JSON.stringify(msg.params.args.map((a) => a.value)));
});
const send = (method, params = {}) => new Promise((r) => { const id = ++seq; waiting.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const js = async (expr) => {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true, replMode: true });
  if (r.result.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text);
  const v = r.result.result;
  return "unserializableValue" in v ? Number(v.unserializableValue) : v.value;
};
const shots = [];
const shot = async (name, what) => {
  await sleep(150);
  const r = await send("Page.captureScreenshot", { format: "png" });
  const file = join(outDir, name + ".png");
  writeFileSync(file, Buffer.from(r.result.data, "base64"));
  shots.push({ file, what });
};
const viewport = (width, height, mobile) => send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 2, mobile });
const results = [];
const expect = (name, ok, got) => results.push({ name, ok: !!ok, got });

await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable");
await viewport(1280, 900, false);
await send("Page.navigate", { url: "file://" + resolve(page) });
await sleep(800);

const H = `q=s=>document.querySelector(s), qa=s=>[...document.querySelectorAll(s)], vis=el=>!!(el&&el.getClientRects().length&&getComputedStyle(el).visibility!=='hidden');`;
const names = await js(`${H} qa('.sec h2').map(h=>h.textContent).join('|')`);
expect("다섯 섹션 이름과 순서", names === "본질|전체 구조|작동 원리|조건과 한계|기억할 원리", names);
expect("상단에 UNDERSTAND·대상명·깊이 선택", await js(`${H} q('.brand').textContent==='UNDERSTAND' && !!q('.top h1').textContent && qa('.seg').length===3`), null);
expect("데스크톱 가로 넘침 없음", await js(`document.documentElement.scrollWidth <= innerWidth`), await js(`[document.documentElement.scrollWidth, innerWidth]`));
expect("기본 깊이는 개요", await js(`${H} qa('.sec').every(s=>s.dataset.level==='overview') && q('.seg[aria-pressed=true]').dataset.zoom==='overview'`), null);
expect("데스크톱 목차 고정 표시", await js(`${H} vis(q('#toc-list')) && getComputedStyle(q('.toc')).position==='sticky'`), null);
await shot("1-overview", "개요 깊이의 첫 화면. 상단 UNDERSTAND·대상명·개요/표준/심층, 왼쪽 고정 목차, 01 본질");

const hasPick = await js(`${H} !!q('.pick')`);
if (hasPick) {
  const r = await js(`${H} const p=q('.pick'); q('#s2').scrollIntoView(); const y=scrollY; p.click(); const panel=q('#panel-'+p.dataset.pick); ({open:vis(panel), expanded:p.getAttribute('aria-expanded'), moved: Math.abs(scrollY-y)})`);
  expect("구조 항목을 누르면 바로 아래에 설명이 열림", r.open && r.expanded === "true" && r.moved < 2, r);
  await shot("2-structure", "02 전체 구조. L1 아래 L2 항목을 누르면 그 아래에 설명이 펼쳐진다");
  const r2 = await js(`${H} const p=q('.pick'); p.click(); ({closed:!vis(q('#panel-'+p.dataset.pick)), focus: document.activeElement===p})`);
  expect("다시 누르면 닫히고 초점은 그 항목에 남음", r2.closed && r2.focus, r2);
}
const nodes = await js(`${H} qa('.diagram .node').length`);
if (nodes) {
  const r = await js(`${H} const n=q('.diagram .node'); n.scrollIntoView({block:'center'}); n.dispatchEvent(new MouseEvent('click',{bubbles:true})); const scope=n.closest('.ladder, .block'); const sec=n.closest('.sec'); ({open: qa('[data-panel]').some(p=>scope.contains(p)&&vis(p)), sec: sec.id, level: sec.dataset.level})`);
  if (r.level === "overview" && r.sec !== "s2") {
    await js(`${H} q('.seg[data-zoom=standard]').click()`);
  }
  const r2 = await js(`${H} const n=q('.diagram .node'); const scope=n.closest('.ladder, .block'); if(!qa('[data-panel]').some(p=>scope.contains(p)&&vis(p))) n.dispatchEvent(new MouseEvent('click',{bubbles:true})); n.scrollIntoView({block:'center'}); ({open: qa('[data-panel]').some(p=>scope.contains(p)&&vis(p)), pressed: n.getAttribute('aria-pressed')})`);
  expect("관계도 노드를 누르면 설명이 열림", r2.open && r2.pressed === "true", r2);
  const kb = await js(`${H} const n=qa('.diagram .node')[1]||q('.diagram .node'); n.focus(); n.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true})); n.getAttribute('aria-pressed')`);
  expect("관계도 노드는 키보드(Enter)로도 열림", kb === "true", kb);
  await shot("3-diagram", "관계도. 선마다 관계 이름이 있고, 노드를 누르면 아래에 설명이 열린다");
  await js(`${H} q('.seg[data-zoom=overview]').click()`);
}

const before = await js(`${H} q('#s4').scrollIntoView({behavior:'instant'}); const hb=q('.top').getBoundingClientRect().bottom; const a=qa('.sec-head').find(h=>h.getBoundingClientRect().bottom>hb+8); const y=a.getBoundingClientRect().top; q('.seg[data-zoom=standard]').click(); Math.round(a.getBoundingClientRect().top - y)`);
expect("깊이를 바꿔도 보던 자리 유지", Math.abs(before) < 4, before);
expect("표준이면 모든 섹션이 표준", await js(`${H} qa('.sec').every(s=>s.dataset.level==='standard')`), null);
expect("표준에서 섹션 순서·개수 그대로", await js(`${H} qa('.sec h2').map(h=>h.textContent).join('|')`) === names, null);
await js(`${H} q('#s3').scrollIntoView()`);
await shot("4-standard", "표준 깊이. 섹션 위치와 순서는 그대로이고 03 작동 원리 내용이 펼쳐진다");

const hasScenario = await js(`${H} !!q('[data-scenario]')`);
if (hasScenario) {
  const r = await js(`${H} const f=q('.scenario'); f.scrollIntoView({block:'center'}); const radios=qa('[data-scenario]'); radios[radios.length-1].click(); const out=f.querySelector('[data-outcome]'); ({shown: qa('[data-option]').filter(vis).length, hint: vis(out.querySelector('.hint'))})`);
  expect("조건을 고르면 그 결과와 이유 하나만 보임", r.shown === 1 && !r.hint, r);
  await shot("5-scenario", "04 조건과 한계의 시나리오. 조건을 고르면 결과와 이유가 보인다");
}

await js(`${H} q('.seg[data-zoom=deep]').click(); const d=q('.checks'); d.open=true; d.scrollIntoView();`);
const ans = await js(`${H} const b=q('[data-answer]'); const a=document.getElementById(b.dataset.answer); const hidden=!vis(a); b.click(); ({hiddenFirst:hidden, shown:vis(a), label:b.textContent})`);
expect("답은 누르기 전까지 숨김", ans.hiddenFirst && ans.shown, ans);
await shot("6-check", "05 아래 이해 확인. 먼저 답을 떠올린 뒤 답 보기를 누른다");

const fold = await js(`${H} const b=q('#s3 [data-fold]'); b.click(); const f=!vis(q('#s3 .sec-body')); b.click(); ({folded:f, back:vis(q('#s3 .sec-body'))})`);
expect("섹션 접기·펼치기", fold.folded && fold.back, fold);
const moreBtn = await js(`${H} q('.seg[data-zoom=overview]').click(); const b=qa('[data-more]').find(b=>!b.hidden); if(!b) null; else { const s=b.closest('.sec'); b.click(); ({sec:s.id, level:s.dataset.level, others: qa('.sec').filter(x=>x!==s).every(x=>x.dataset.level==='overview')}) }`);
if (moreBtn) expect("더 보기는 그 섹션만 펼침", moreBtn.level !== "overview" && moreBtn.others, moreBtn);

const reset = await js(`${H} q('[data-reset]').click(); ({zoom:document.body.dataset.zoom, levels: qa('.sec').every(s=>s.dataset.level==='overview'), panels: qa('[data-panel]').every(p=>p.hidden), answers: qa('.answer').every(a=>a.hidden), details: qa('details').every(d=>!d.open), radios: qa('[data-scenario]').every(r=>!r.checked), top: scrollY})`);
expect("초기화는 처음 상태로", reset.zoom === "overview" && reset.levels && reset.panels && reset.answers && reset.details && reset.radios, reset);

await viewport(390, 844, true);
await send("Page.reload");
await sleep(700);
expect("모바일 가로 넘침 없음", await js(`document.documentElement.scrollWidth <= innerWidth`), await js(`[document.documentElement.scrollWidth, innerWidth]`));
const toc = await js(`${H} const hid=!vis(q('#toc-list')); q('.toc-toggle').click(); ({hiddenFirst:hid, open:vis(q('#toc-list'))})`);
expect("모바일 목차는 접혀 있다가 펼쳐짐", toc.hiddenFirst && toc.open, toc);
await shot("7-mobile", "휴대폰 폭(390px). 같은 순서와 컴포넌트, 목차는 접었다 편다");
await js(`${H} q('.toc-toggle').click(); q('.seg[data-zoom=deep]').click(); qa('[data-pick]').forEach(p=>{ if(p.tagName==='BUTTON' && p.getAttribute('aria-expanded')==='false') {} });`);
const clipped = await js(`${H} qa('main *').filter(el=>{const r=el.getBoundingClientRect(); return r.width>0 && r.right>innerWidth+1 && !el.closest('.table-wrap, .diagram')}).map(el=>el.className||el.tagName).slice(0,5)`);
expect("모바일 심층에서 잘리는 요소 없음", clipped.length === 0, clipped);

await viewport(1280, 900, false);
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }] });
await send("Page.reload");
await sleep(700);
const dark = await js(`getComputedStyle(document.body).backgroundColor`);
expect("시스템 다크 모드", dark !== "rgb(251, 251, 250)", dark);
await js(`${H} q('.seg[data-zoom=standard]').click(); const p=q('.pick'); if(p){p.click(); q('#s2').scrollIntoView();}`);
await shot("8-dark", "다크 모드. 같은 레이아웃, 색만 바뀐다");

const external = await js(`performance.getEntriesByType('resource').map(r=>r.name).filter(n=>!n.startsWith('file:') && !n.startsWith('data:'))`);
expect("바깥 요청 없음", external.length === 0, external);
expect("콘솔 오류·예외 없음", problems.length === 0, problems);

ws.close(); proc.kill(); await sleep(200);
try { rmSync(profile, { recursive: true, force: true }); } catch {}
const failed = results.filter((r) => !r.ok);
for (const r of results) console.log((r.ok ? "PASS " : "FAIL ") + r.name + (r.ok ? "" : " → " + JSON.stringify(r.got)));
writeFileSync(join(outDir, "shots.json"), JSON.stringify(shots, null, 2));
console.log(`${results.length - failed.length}/${results.length} 통과, 스크린샷 ${shots.length}장 → ${outDir}`);
process.exit(failed.length ? 1 : 0);
