---
name: control-ui
description: "로컬 브라우저·CDP 하네스를 만들거나 고쳐 웹·IDE·Electron·데스크톱 앱 화면을 몰고 들여다본다. 로컬 화면 검증, 스크린샷, 접근성 스냅숏, 성능 프로파일, 화면 비교, 화면 버그 재현에 쓴다. 「화면 직접 조작해 봐」, 「브라우저 몰아 봐」, 「앱 스크린샷 찍어」, 「이 화면 버그 재현해」에 쓴다. /dev:control-ui"
disable-model-invocation: true
---

# 화면 몰기

로컬 브라우저 자동화로 화면 동작을 증거와 함께 확인한다. 저장소에 Playwright·브라우저·Electron 하네스가 있으면 먼저 그것을 다시 쓴다. 없으면 Claude Code 의 브라우저 도구로 앱의 dev 서버를 몰고, 그것으로 안 되는 일만 dev 서버나 Chromium 디버그 포트에 붙는 임시 로컬 하네스를 짜서 Bash 로 돌린다.

## 도구

| 대상 | 쓸 것 |
|---|---|
| 로컬 웹 앱 | Claude Code 데스크톱의 내장 브라우저(`mcp__Claude_Browser__*`). dev 서버는 `preview_start` 로 띄운다. 없으면 Claude in Chrome(`mcp__claude-in-chrome__*`) |
| Electron·Chromium 앱, 원시 CDP 가 필요한 일 | 아래 CDP 하네스를 Bash 로 |
| 브라우저 밖 데스크톱 앱 화면 | computer-use(`mcp__computer-use__*`) |

브라우저 도구는 `read_page`(접근성 트리), `find`, `computer`(클릭·입력·스크린샷), `resize_window`(뷰포트·색 모드), `read_console_messages`, `read_network_requests`, `javascript_tool` 을 준다. 처음 쓰기 전에 그 도구의 스킬(내장 브라우저면 built-in-browser, Chrome 이면 chrome-browser, 데스크톱이면 computer-use)을 읽는다.

## 어디에 쓰나

- 실제 브라우저의 포커스, 키보드 입력, 스크롤, 크기 바꾸기, 렌더링에 달린 화면 버그 재현.
- 스크린샷과 스냅숏으로 화면·접근성 변경 검증.
- 내보내기 전에 로컬 웹·IDE·Electron 동작 확인.
- 콘솔 로그, 네트워크 로그, CPU 프로파일, 트레이스, 힙 스냅숏 수집.
- 검증 보고에 붙일 전과 후 증거 만들기(`/dev:mode` 의 「꼭 지킬 것」).

## 준비

1. 저장소 문서에 적힌 dev 명령으로 앱을 로컬에서 띄운다.
2. 이미 있는 로컬 하네스를 찾는다. Playwright 테스트, Cypress 스펙, Storybook, 브라우저 스크립트, Electron 실행 스크립트, 스냅숏 도구.
3. 웹 앱이면 위 브라우저 도구나 이미 있는 브라우저 도구로 로컬 주소에 붙는다.
4. Electron·Chromium 이면 지원될 때 원격 디버깅 포트를 켠다.
5. 탭 순서만 보지 말고 안정된 앱 표지로 맞는 페이지를 고른다.
6. 좌표보다 접근성 역할, 레이블, 안정된 `data-*` 선택자를 쓴다.

## 일반 웹 하네스

되도록 저장소에 설치된 브라우저 도구를 쓴다. 저장소에 이미 Playwright 가 있으면 한 번 쓰고 버릴 최소 탐침은 이렇다.

```javascript
import { chromium } from "playwright";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
await page.goto("http://127.0.0.1:<port>");
await page.getByRole("button", { name: /submit/i }).click();
await page.screenshot({ path: "/tmp/ui-harness-after.png", fullPage: true });
await browser.close();
```

사용자가 요청하지 않으면 이 탐침 하나를 위해 Playwright 를 프로젝트 의존성으로 더하지 않는다. 이미 있는 dev 의존성이나 환경에 이미 있는 바깥 브라우저 도구(위 브라우저 도구 포함)를 쓴다.

## 일반 CDP 하네스

Electron 이나 `--remote-debugging-port=<port>` 로 띄운 Chromium 앱은 CDP 로 붙는다.

```javascript
import { chromium } from "playwright";

const browser = await chromium.connectOverCDP("http://127.0.0.1:<debug-port>");
const pages = browser.contexts().flatMap((context) => context.pages());
let page;
for (const candidate of pages) {
  if (await candidate.locator("<app-root-selector>").count()) {
    page = candidate;
    break;
  }
}

if (!page) {
  console.log(await Promise.all(pages.map(async (p) => ({
    title: await p.title(),
    url: p.url(),
  }))));
  throw new Error("No matching app page found");
}

await page.screenshot({ path: "/tmp/ui-harness-cdp.png", fullPage: true });
await browser.close();
```

`<app-root-selector>` 는 지금 저장소의 안정된 표지로 바꾼다. 앱 루트 노드, 랜드마크, 제품 고유의 `data-*` 속성 같은 것.

## 상호작용 루프

1. 움직이기 전에 페이지 스냅숏(`read_page`)이나 스크린샷을 뜬다.
2. 가장 최근 페이지 구조에서 대상을 고른다.
3. 구조를 바꾸는 행동을 정확히 하나만 한다. 클릭, 입력, 키 누르기, 끌기, 스크롤, 이동, 크기 바꾸기.
4. 새 스냅숏이나 스크린샷을 뜬다.
5. 기대한 상태 변화가 일어났는지 확인한다.
6. 사용자가 증거를 요청했으면 전과 후 비교용 산출물을 남긴다.

## CDP 로 하는 일

고수준 브라우저 API 로 모자랄 때만 원시 CDP 를 쓴다. 브라우저 도구의 `resize_window`·`read_console_messages`·`read_network_requests` 로 되는 일은 그쪽으로 한다.

- 성능: CPU 프로파일, 트레이스, 페인트 깜빡임 표시, FPS 미터, 레이아웃 이동 살피기.
- 메모리: 누수 조사용 힙 스냅숏과 강제 GC.
- 네트워크: 요청 막기, 속도 제한, 캐시 끄기, 요청·응답 로그.
- 렌더링: 뷰포트 바꾸기, 색 모드 흉내, 동작 줄이기(reduced motion), 접근성 검사.
- 디버깅: 콘솔 흘려 받기, 예외 잡기, DOM 스냅숏.

성능 숫자를 보고하면 먼저 `/dev:bench`.

## 페이지 고르기

디버그 포트 하나를 앱 창·탭 여럿이 함께 쓸 때:

- 시험하는 표면의 긍정 표지(앱 루트 선택자 같은 것)를 먼저 쓴다.
- 필요하면 부정 표지로 엉뚱한 표면을 피한다.
- 맞는 페이지가 없으면 짐작하지 말고 열린 페이지의 제목과 주소를 늘어놓는다.

## 가드레일

- 이동이나 구조 변경 뒤에는 낡은 요소 참조(ref)를 믿지 않는다. 스냅숏을 다시 뜬다.
- 바로 앞에 새 스크린샷을 뜨지 않았으면 좌표 클릭을 피한다.
- 시험 데이터는 로컬에 두고 버릴 수 있게 한다.
- 개인정보가 민감한 작업 공간의 스크린샷이나 힙 스냅숏은 사용자가 분명히 동의하지 않으면 남기지 않는다.
- 다른 저장소의 선택자, 포트, 스크립트 경로를 박아 넣지 않는다. 지금 저장소의 로컬 앱 표지를 찾는다.
- 끝나면 내가 띄운 dev 서버(`preview_stop`), 디버그 세션, 임시 프로필, 연 탭을 정리한다.
