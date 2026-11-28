// 렌더한 HTML 을 헤드리스 Chrome 으로 열어 읽기 흐름, 금지 요소, 뼈대 그림이 읽는 자리를 따라가는지, 모바일 가독성을 실제로 보고 스크린샷을 찍는다.
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
  await sleep(500);
  const r = await send("Page.captureScreenshot", { format: "png" });
  const file = join(outDir, name + ".png");
  writeFileSync(file, Buffer.from(r.result.data, "base64"));
  shots.push({ file, what });
};
const viewport = (width, height, mobile) => send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 2, mobile });
const results = [];
const expect = (name, ok, got) => results.push({ name, ok: !!ok, got });
const ORDER = ["출발점", "뼈대", "설명되는 현상", "새로운 추론", "적용 한계"];
const H = `q=s=>document.querySelector(s), qa=s=>[...document.querySelectorAll(s)], vis=el=>!!(el&&el.getClientRects().length&&getComputedStyle(el).visibility!=='hidden');`;
// 그림이 지금 보이는 것. off 가 아닌 부분과 연결, on 인 것.
const FIG = `${H} fig=()=>{const s=q('.stage svg'); const ids=(sel,a)=>[...new Set(qa(sel).filter(n=>!n.classList.contains('off')).map(n=>n.dataset[a]))].sort(); return {block:s.dataset.block, show:ids('[data-part]','part'), links:ids('[data-link]','link'), focus:[...qa('[data-part].on').map(n=>n.dataset.part), ...new Set(qa('[data-link].on').map(n=>n.dataset.link))].sort(), known:s.classList.contains('known')};}; want=b=>({block:b.id, show:b.dataset.show.split(' ').filter(Boolean).sort(), links:b.dataset.links.split(' ').filter(Boolean).sort(), focus:b.dataset.focus.split(' ').filter(Boolean).sort(), known:b.dataset.mode==='known'});`;
const readAt = (i) => js(`${FIG} const b=qa('[data-show]')[${i}]; const st=q('.stage').getBoundingClientRect(); const line = st.width > innerWidth*0.8 ? st.bottom + 40 : innerHeight*0.5; scrollBy(0, b.getBoundingClientRect().top - line + 6); await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))); ({got: fig(), want: want(b), kind: b.className})`);

await send("Runtime.enable"); await send("Log.enable"); await send("Page.enable");
await viewport(1280, 900, false);
await send("Page.navigate", { url: "file://" + resolve(page) });
await sleep(800);

const head = await js(`${H} const t=q('.thesis').getBoundingClientRect(); ({brand:q('.brand').textContent, h1:!!q('h1').textContent.trim(), thesisBottom:t.bottom, h:innerHeight})`);
expect("첫 화면에 대상명과 핵심 명제", head.brand === "UNDERSTAND" && head.h1 && head.thesisBottom < head.h, head);
const first = await js(`${FIG} const r=q('.stage svg').getBoundingClientRect(); ({...fig(), top:r.top, bottom:r.bottom, h:innerHeight, all:qa('[data-part]').length})`);
expect("첫 화면에 뼈대 전체가 보인다", first.show.length === first.all && first.focus.length === 0 && first.bottom <= first.h + 1 && first.top >= -1, first);
const names = await js(`${H} qa('.sec h2').map(h=>h.lastChild.textContent.trim())`);
const idx = names.map((n) => ORDER.indexOf(n));
expect("영역은 고정 순서를 지키고 있는 것만 나온다", idx.every((v, i) => v >= 0 && (i === 0 || v > idx[i - 1])) && names.includes("뼈대"), names);
const banned = await js(`${H} ({controls: qa('input, button, select, details, nav, textarea, [contenteditable]').length, words: (document.body.innerText.match(/\\bL[1-5]\\b|개요|표준|심층|더 보기|초기화|출처|각주|해당 없음|퀴즈|이해 확인|진행률|슬라이더/g)||[]), refs: qa('sup, .ref, [href^="#src"]').length})`);
expect("조절 장치·버튼·접기·출처·퀴즈가 없다", banned.controls === 0 && banned.words.length === 0 && banned.refs === 0, banned);
const hidden = await js(`${H} qa('.story p, .story li, .story h3').filter(el=>!vis(el)).map(el=>el.textContent.slice(0,30))`);
expect("클릭 없이 모든 설명이 보인다", hidden.length === 0, hidden);
expect("데스크톱 가로 넘침 없음", await js(`document.documentElement.scrollWidth <= innerWidth`), await js(`[document.documentElement.scrollWidth, innerWidth]`));
await shot("1-head", "첫 화면. 대상명, 핵심 명제, 뼈대 전체");

// 덩어리마다 읽는 자리에 두고 그림이 그 덩어리의 상태를 보이는지 본다.
const nBlocks = await js(`${H} qa('[data-show]').length`);
const wrong = [];
const grow = [];
let stepNo = 0;
for (let i = 0; i < nBlocks; i++) {
  const r = await readAt(i);
  if (JSON.stringify(r.got) !== JSON.stringify(r.want)) wrong.push({ i, got: r.got, want: r.want });
  if (r.kind.includes("step")) {
    grow.push(r.got.show.length);
    stepNo++;
    await shot(`step-${stepNo}`, `뼈대 ${stepNo}단계. 새로 세운 부분과 연결이 짚인다`);
  } else if (r.kind.includes("bridge")) await shot("bridge", "출발점. 아는 그림을 같은 뼈대에 겹치고 차이가 나는 부분을 표시한다");
  else if (r.kind.includes("phen") && !shots.some((s) => s.file.endsWith("phen.png"))) await shot("phen", "현상 하나가 뼈대 위에서 지나는 길");
  else if (r.kind.includes("infer") && !shots.some((s) => s.file.endsWith("infer.png"))) await shot("infer", "추론 하나가 뼈대 위에서 지나는 길");
}
expect("읽는 덩어리마다 그림이 그 상태(보이는 부분·연결·짚는 것)를 보인다", nBlocks > 0 && wrong.length === 0, wrong.slice(0, 3));
expect("뼈대는 단계마다 자라고 마지막 단계에서 다 선다", grow.length >= 3 && grow.every((v, i) => i === 0 || v >= grow[i - 1]) && grow[grow.length - 1] === first.all, grow);
const fixed = await js(`${H} const r=q('.stage').getBoundingClientRect(); ({top:r.top, h:innerHeight})`);
expect("읽는 동안 그림이 화면에 붙어 있다", fixed.top >= -1 && fixed.top < 40, fixed);

await viewport(390, 844, true);
await send("Page.reload");
await sleep(700);
expect("모바일 가로 넘침 없음", await js(`document.documentElement.scrollWidth <= innerWidth`), await js(`[document.documentElement.scrollWidth, innerWidth]`));
const small = await js(`${H} qa('.stage svg').map(s=>{const vb=s.viewBox.baseVal; const r=s.getBoundingClientRect(); const sc=Math.min(r.width/vb.width, r.height/vb.height); const fs=Math.min(...[...s.querySelectorAll('text')].map(t=>parseFloat(getComputedStyle(t).fontSize))); return {sc:+sc.toFixed(2), px:+(fs*sc).toFixed(1)};}).filter(x=>x.px<10.5)`);
expect("모바일에서 그림 글자가 10.5px 이상", small.length === 0, small);
const bodyPx = await js(`parseFloat(getComputedStyle(document.querySelector('.story p')).fontSize)`);
expect("모바일 본문 글자 15px 이상", bodyPx >= 15, bodyPx);
await shot("m1-head", "휴대폰 폭(390px) 첫 화면");
const mid = Math.min(2, nBlocks - 1);
const steps = await js(`${H} qa('[data-show]').findIndex(b=>b.classList.contains('step'))`);
const mr = await readAt(steps + 1);
expect("모바일에서도 읽는 덩어리의 상태를 그림이 보인다", JSON.stringify(mr.got) === JSON.stringify(mr.want), mr);
const mst = await js(`${H} const r=q('.stage').getBoundingClientRect(); ({top:r.top, h:r.height, vh:innerHeight})`);
expect("모바일에서 그림은 위에 붙고 화면 절반을 넘지 않는다", mst.top >= -1 && mst.top < 2 && mst.h <= mst.vh * 0.5, mst);
await shot("m2-step", "휴대폰 폭. 그림이 위에 붙고 그 아래 글이 지나간다");

await viewport(1280, 900, false);
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }] });
await send("Page.reload");
await sleep(700);
const dark = await js(`getComputedStyle(document.body).backgroundColor`);
expect("시스템 다크 모드", dark !== "rgb(251, 251, 250)", dark);
await readAt(mid);
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
