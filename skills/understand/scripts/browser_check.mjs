// 렌더한 HTML 을 헤드리스 Chrome 으로 열어 읽기 흐름·금지 요소·상호작용·모바일 가독성을 실제로 보고, 영역마다 스크린샷을 찍는다.
// 쓰는 법: node browser_check.mjs <page.html> <스크린샷 폴더> [기대값.json]
// 기대값 파일(tests/run.py 가 Python 계산으로 만든다)이 있으면 시뮬레이터 입력을 바꿔 화면 숫자가 그 계산과 같은지 본다.
// 의존성: Chrome(또는 Chromium)과 Node 22 이상(내장 WebSocket). 바깥 패키지는 쓰지 않는다.
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync, readFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const [, , page, outDir, expectFile] = process.argv;
if (!page || !outDir) { console.error("쓰는 법: node browser_check.mjs <page.html> <스크린샷 폴더>"); process.exit(2); }
const CHROMES = [process.env.CHROME, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Chromium.app/Contents/MacOS/Chromium", "/usr/bin/google-chrome", "/usr/bin/chromium"].filter(Boolean);
const chrome = CHROMES.find((c) => existsSync(c));
if (!chrome) { console.log("SKIP Chrome 이 없어 브라우저 검사를 못 했다"); process.exit(3); }
rmSync(outDir, { recursive: true, force: true });
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
const ORDER = ["출발점", "핵심 메커니즘", "설명되는 현상", "새로운 추론", "적용 한계"];
const H = `q=s=>document.querySelector(s), qa=s=>[...document.querySelectorAll(s)], vis=el=>!!(el&&el.getClientRects().length&&getComputedStyle(el).visibility!=='hidden');`;

await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable");
await viewport(1280, 900, false);
await send("Page.navigate", { url: "file://" + resolve(page) });
await sleep(800);

const head = await js(`${H} const t=q('.thesis').getBoundingClientRect(); ({brand:q('.brand').textContent, h1:!!q('h1').textContent.trim(), thesisTop:t.top, thesisBottom:t.bottom, h:innerHeight})`);
expect("첫 화면에 대상명과 핵심 명제", head.brand === "UNDERSTAND" && head.h1 && head.thesisBottom < head.h, head);
const names = await js(`${H} qa('.sec h2').map(h=>h.lastChild.textContent.trim())`);
const idx = names.map((n) => ORDER.indexOf(n));
expect("영역은 고정 순서를 지키고 있는 것만 나온다", idx.every((v, i) => v >= 0 && (i === 0 || v > idx[i - 1])) && names.length >= 1, names);
expect("빈 영역 없음", await js(`${H} qa('.sec').every(s=>s.textContent.trim().length > s.querySelector('h2').textContent.length + 20)`), null);
const banned = await js(`${H} ({buttons: qa('button, details, nav, select').length, depth: qa('[data-depth], [data-fold], [data-more], [data-reset]').length, words: (document.body.innerText.match(/\\bL[1-5]\\b|개요|표준|심층|더 보기|초기화|출처|각주|해당 없음|퀴즈|이해 확인|진행률|가장 구체적인 수준|갈래로 더/g)||[]), refs: qa('sup, .ref, [href^="#src"]').length})`);
expect("금지 요소 없음(모드·접기·단계 버튼·계층 표시·출처·초기화·퀴즈)", banned.buttons === 0 && banned.depth === 0 && banned.words.length === 0 && banned.refs === 0, banned);
const clash = await js(`${H} const cards=qa('.switch, .infer'); cards.flatMap(c=>{const top=c.getBoundingClientRect().top; return [...c.children].filter(k=>vis(k) && k.getBoundingClientRect().top < top - 1).map(k=>k.className||k.tagName);})`);
expect("카드 안 글이 카드 테두리 밖으로 넘지 않음", clash.length === 0, clash);
const hidden = await js(`${H} qa('main p, main li, main h3, main figure, main table').filter(el=>!vis(el) && !el.closest('[data-option], .note, .sr')).map(el=>el.textContent.slice(0,30))`);
expect("클릭 없이 모든 설명이 보인다", hidden.length === 0, hidden);
expect("데스크톱 가로 넘침 없음", await js(`document.documentElement.scrollWidth <= innerWidth`), await js(`[document.documentElement.scrollWidth, innerWidth]`));
await shot("1-head", "첫 화면. 대상명, 핵심 명제, 최소 설명");
const secIds = await js(`${H} qa('.sec').map(s=>s.id)`);
for (const [i, id] of secIds.entries()) {
  await js(`${H} q('#${id}').scrollIntoView({behavior:'instant'})`);
  await shot(`${i + 2}-${id}`, `${names[i]} 영역`);
}

const exp = expectFile && existsSync(expectFile) ? JSON.parse(readFileSync(expectFile, "utf8")) : null;
const plots = await js(`${H} qa('[data-plot]').map(b=>({lines: [...b.querySelectorAll('polyline')].map(l=>l.getAttribute('points').split(' ').length), ys: JSON.parse(b.dataset.plot).ys.length, marks: b.querySelectorAll('[data-mark]').length}))`);
expect("그래프가 그려진다(출력마다 선 하나, 점 50개 이상)", plots.length > 0 && plots.every(p => p.lines.length === p.ys && p.lines.every(n => n >= 50)), plots);
for (let k = 0; k < await js(`${H} qa('.model').length`); k++) {
  await js(`${H} qa('.model figure')[${k}].scrollIntoView({behavior:'instant', block:'center'})`);
  await shot(`model-${k + 1}`, `정신 모델 ${k + 1} 의 관계도. 변수마다 지금 값, 선마다 부호와 관계`);
}
expect("관계도마다 변수의 지금 값이 보인다", await js(`${H} qa('.model svg').length > 0 && qa('.model svg').every(s=>s.querySelector('.val'))`), null);
if (await js(`${H} qa('[data-in]').length`)) {
  const before = await js(`${H} ({outs: qa('[data-out]').map(o=>o.textContent).join('|'), lines: qa('[data-plot] polyline').map(l=>l.getAttribute('points')).join('|')})`);
  const after = await js(`${H} const set=${JSON.stringify(exp ? exp.inputs : null)}; qa('[data-in]').forEach(i=>{ i.value = set ? set[i.dataset.in] : i.max; i.dispatchEvent(new Event('input',{bubbles:true})); }); const outs={}; qa('[data-out]').forEach(o=>{ (outs[o.dataset.out] ||= new Set()).add(o.textContent); }); ({outs: Object.fromEntries(Object.entries(outs).map(([k,v])=>[k,[...v]])), lines: qa('[data-plot] polyline').map(l=>l.getAttribute('points')).join('|'), marks: qa('[data-plot]').map(b=>b.querySelectorAll('[data-mark]').length)})`);
  expect("변수를 바꾸면 관계도의 값과 그래프가 함께 바뀐다", after.lines !== before.lines && JSON.stringify(Object.values(after.outs).map(v => v.length)) === JSON.stringify(Object.values(after.outs).map(() => 1)), after.outs);
  if (exp) {
    const screen = Object.fromEntries(Object.keys(exp.outputs).map(k => [k, after.outs[k] ? after.outs[k][0] : null]));
    expect("화면 계산이 Python 계산과 같다", JSON.stringify(screen) === JSON.stringify(exp.outputs), { screen, python: exp.outputs });
    expect("그래프의 임계선 수가 Python 계산과 같다", JSON.stringify(after.marks) === JSON.stringify(exp.marks), { screen: after.marks, python: exp.marks });
  }
  await js(`${H} q('[data-plot]').scrollIntoView({behavior:'instant', block:'center'})`);
  await shot("plot", "변수를 바꾼 뒤의 그래프. 임계선과 지금 위치가 함께 움직인다");
}
const hasSwitch = await js(`${H} !!q('[data-switch]')`);
if (hasSwitch) {
  const first = await js(`${H} qa('[data-option]').filter(vis).length`);
  const r = await js(`${H} const rs=qa('[data-switch]'); rs[rs.length-1].click(); const out=q('[data-outcome]'); ({shown: [...out.querySelectorAll('[data-option]')].filter(vis).map(o=>o.dataset.option), last: String(rs.length-1)})`);
  expect("조건 전환: 처음부터 결과가 보이고, 바꾸면 그 결과 하나만 보인다", first >= 1 && r.shown.length === 1 && r.shown[0] === r.last, { first, ...r });
  await js(`${H} q('.switch').scrollIntoView({behavior:'instant', block:'center'})`);
  await shot("switch", "조건 전환. 조건을 바꾸면 결과와 이유가 바뀐다");
}

await viewport(390, 844, true);
await send("Page.reload");
await sleep(700);
expect("모바일 가로 넘침 없음", await js(`document.documentElement.scrollWidth <= innerWidth`), await js(`[document.documentElement.scrollWidth, innerWidth]`));
const small = await js(`${H} qa('svg').map(s=>{const vb=s.viewBox.baseVal; const sc=s.getBoundingClientRect().width/vb.width; const fs=Math.min(...[...s.querySelectorAll('text')].map(t=>parseFloat(getComputedStyle(t).fontSize))); return {sc:+sc.toFixed(2), px:+(fs*sc).toFixed(1)};}).filter(x=>x.px<10.5)`);
expect("모바일에서 그림 글자가 10.5px 이상", small.length === 0, small);
const bodyPx = await js(`parseFloat(getComputedStyle(document.querySelector('.sec p:not(.basis):not(.k):not(.assume)')).fontSize)`);
expect("모바일 본문 글자 15px 이상", bodyPx >= 15, bodyPx);
await js(`${H} q('[data-plot]').scrollIntoView({behavior:'instant', block:'center'})`);
await shot("m3-plot", "휴대폰 폭의 그래프. 변수 조절은 위에 붙는다");
await shot("m1-head", "휴대폰 폭(390px) 첫 화면");
if (await js(`${H} !!q('.fig')`)) {
  await js(`${H} q('.fig').scrollIntoView({behavior:'instant'})`);
  await shot("m2-figure", "휴대폰 폭의 그림. 넓으면 그림 안에서만 가로로 밀린다");
}

await viewport(1280, 900, false);
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }] });
await send("Page.reload");
await sleep(700);
const dark = await js(`getComputedStyle(document.body).backgroundColor`);
expect("시스템 다크 모드", dark !== "rgb(251, 251, 250)", dark);
await js(`${H} (q('.fig')||q('.sec')).scrollIntoView({behavior:'instant'})`);
await shot("dark", "다크 모드. 같은 배치, 색만 바뀐다");

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
