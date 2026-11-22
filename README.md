# kit

`dev` 는 Claude Code 에이전트가 한 일을 믿을 수 있게 만드는 플러그인이고, 이 저장소 `happy-nut/kit` 이 그 마켓플레이스다. 에이전트는 일의 종류마다 정해 둔 단계(플레이북)를 따르고, 판단이 갈리면 원칙 문서를 읽는다. 「됐다」는 보고는 직접 돌려 본 증거가 있을 때만 받는다. 에이전트가 틀려서 교정하면, 같은 실수를 글 대신 구조, 검사, 훅으로 막는다.

출발점은 Lauren Tan 의 강연 「All Code Is Slop (Except Mine)」(2026-11)과 그가 공개한 pstack(MIT)이다. 강연은 남의 설정을 그대로 쓰지 말고 포크해서 자기 교정 기록으로 키우라고 한다. 이 저장소가 그렇게 키운 포크다. 강연이 말하는 최종 이상(high trust 루프)과 거기로 가는 길은 [`docs/philosophy.md`](docs/philosophy.md) 에 정리했고, 판단이 갈리면 그 이상에 가까워지는 쪽을 고른다. 스킬과 문서는 한국어로 쓴다.

## 설치한다

Claude Code 가 있어야 한다. 훅은 `sh` 와 `awk` 로 돌고, PR 머지 검사는 `gh`(GitHub CLI)를 쓴다.

```bash
claude plugin marketplace add happy-nut/kit
```

```bash
claude plugin install dev@kit
```

서드파티 마켓플레이스는 자동 업데이트가 꺼져 있다. 새 판은 직접 받는다.

```bash
claude plugin update dev@kit
```

## 처음 써 본다

설치하면 대화마다 `/dev:mode` 가 켜진다. `hooks/hooks.json` 의 SessionStart 훅이 대화를 열거나, 다시 열거나, 지우거나, 압축할 때마다 `skills/mode/SKILL.md` 본문을 대화에 넣는다. 할 일을 그냥 말하면 된다. 끄려면 플러그인을 끈다(`claude plugin disable dev@kit`).

```
버튼 색이 화면마다 달라
이 PR 머지까지 해
```

에이전트는 이 순서로 일한다.

1. 목표와 가장 작은 변경을 자기 말로 한 번 적는다.
2. 플레이북 22개 가운데 하나를 고르고, 그 단계를 작업 목록에 옮긴다.
3. 단계마다 필요한 원칙 절을 읽고, 필요하면 서브에이전트에 일을 나눈다.
4. 스크린샷, 실행 출력처럼 확인한 증거를 붙여 보고한다.

프롬프트에는 원하는 것과 「됐다」를 확인할 방법만 적는다. 방법은 에이전트가 고른다.

같은 실수가 되풀이되면 `/dev:correct <지적>` 을 쓴다. 에이전트가 그 실수를 구조, 타입, 린트, 테스트로 막는다.

플러그인 자체가 마음에 안 들면 `/dev:reflect <무엇이 별로였나>` 를 쓴다. 에이전트가 이 저장소(또는 내 포크)를 고쳐 PR 을 올린다.

방향만 바꾸려면 원칙 이름을 댄다. 「Prove It Works 로 다시 봐」는 실제로 돌려 증명하게 하고, 「Fix Root Causes」는 땜질 대신 원인을 고치게 하고, 「Laziness Protocol」은 변경을 더 작게 줄이게 한다.

어떤 스킬을 쓸지 모르겠으면 `/dev:help` 에 묻는다. 실제 프롬프트로 쓰는 법을 처음부터 배우려면 [사용 안내서](docs/guide/README.md)를 순서대로 읽는다.

## 저장소 구성

```
skills/mode/SKILL.md             /dev:mode. 플레이북을 고르는 라우터
skills/mode/principles.md        원칙 24개. 한 파일에 절마다 "## 영어 이름"
skills/mode/playbooks/           플레이북 22개
skills/mode/references/          플레이북이 읽는 참고 문서
skills/mode/scripts/             플레이북이 돌리는 스크립트
skills/<이름>/SKILL.md           /dev:<이름> 으로 부르는 스킬. mode 를 넣어 32개
hooks/hooks.json                 대화마다 mode 를 켜는 SessionStart 훅
agents/                          서브에이전트 dev:worker, dev:comment-reviewer
scripts/check.py                 저장소 검사
docs/guide/                      사람이 읽는 사용 안내서 10장
docs/philosophy.md               최종 이상(high trust 루프)과 거기로 가는 길
docs/authoring.md                이 저장소를 고치는 규칙
```

개수는 `ls skills/mode/playbooks | wc -l`, `grep -c '^## ' skills/mode/principles.md`, `ls skills | wc -l` 로 다시 셀 수 있다.

플레이북은 일의 종류마다 단계를 정해 둔 문서다. 조사, 버그 수정, 기능, 리팩터링, 성능, PR 열기와 돌보기, 자율 실행, 일시 중지, 워크트리 정리 같은 것이 있고, 전체 목록은 `skills/mode/playbooks/` 에 있다.

원칙은 판단이 갈릴 때 쓰는 기준이다. `Prove It Works` 를 따르면 에이전트는 돌려 보기 전에 됐다고 말하지 않는다. `Never Block on the Human` 을 따르면 사람 답을 기다리는 동안 막히지 않은 다른 일을 한다.

## 스킬

스킬은 `/dev:<이름>` 으로 직접 부를 때만 돈다. `/dev:mode` 가 플레이북 단계에서 다른 스킬을 부르기도 한다.

일을 시키고 나누는 스킬이다.

| 스킬 | 하는 일 |
|---|---|
| `/dev:idea` | 원하는 이상을 듣고 현재를 조사해 갭을 문제로 정하고, MECE 로직 트리로 임팩트가 가장 큰 현실적 문제 하나를 고른다 |
| `/dev:mode` | 플레이북을 고르고 단계대로 일한다 |
| `/dev:design` | 설계안 여러 개를 병렬로 그리고, 하나를 골라 다른 안의 좋은 점을 붙인다 |
| `/dev:swarm` | 일을 독립된 조각으로 나눠 병렬로 풀고, 결과를 PASS, ISSUES, BLOCKED 로 모은다 |
| `/dev:review` | 여러 모델이 변경을 깨 보려 하고, 실행으로 증명한 문제만 보고한다. 파급 범위도 본다 |

실수를 막고 품질을 지키는 스킬이다.

| 스킬 | 하는 일 |
|---|---|
| `/dev:correct` | 에이전트가 되풀이하는 실수를 구조, 린트, 테스트로 막는다. 새 검사가 과거 실수에서 실패하는지 증명한다 |
| `/dev:tdd` | 버그를 실패하는 회귀 테스트로 먼저 재현한다. 테스트가 싸고 분명할 때만 쓴다 |
| `/dev:bench` | 성능 숫자를 믿거나 보고하기 전에 측정 방법을 점검한다 |
| `/dev:no-comments` | 주석을 심사해 지우고, 주석이 변명하던 우회 코드를 고친다 |
| `/dev:ts` | `.ts`, `.tsx` 를 고칠 때 따르는 TypeScript 규칙 |
| `/dev:write` | 문서, README, PR 설명, 커밋 메시지를 쓰는 규칙 |
| `/dev:deslop` | 커밋 전에 diff 에서 에이전트가 남긴 군더더기(서술 주석, 근거 없는 방어 코드, 관계없는 수정)를 지운다 |
| `/dev:control-ui` | 웹·데스크톱 화면을 직접 띄워 조작하고 전과 후 증거를 남긴다 |
| `/dev:control-cli` | CLI·대화형 터미널 프로그램을 직접 돌려 조작하고 확인한다 |
| `/dev:bro` | 방금 한 말을 전문용어 없이 쉬운 말로 다시 한다 |
| `/dev:sharpen` | 일을 더 크게가 아니라 더 깊게 만들도록 프롬프트를 다시 쓴다 |

코드와 작업 맥락을 이해하는 스킬이다.

| 스킬 | 하는 일 |
|---|---|
| `/dev:how` | 코드가 어떻게 도는지, 새 코드를 어디에 둘지 설명한다 |
| `/dev:why` | 커밋, PR, 이슈에서 근거를 찾아 코드가 왜 이렇게 됐는지 답한다 |
| `/dev:recall` | 며칠 전 작업의 맥락을 대화 기록에서 되살린다 |
| `/dev:catchup` | 자리를 비운 사이 바뀐 것과 사용자가 정할 것만 짧게 보고한다 |
| `/dev:catchup-video` | catchup 을 자막 달린 짧은 영상으로 만든다 |
| `/dev:log` | 긴 자율 작업의 결정을 TSV 파일 하나에 기록한다 |

프로젝트마다 검증을 만드는 스킬이다.

| 스킬 | 하는 일 |
|---|---|
| `/dev:verify-setup` | 앱을 사용자처럼 조작해 변경을 증명하는 프로젝트 전용 검증 스킬을 만들고 유지한다 |
| `/dev:featuremap` | 기능 지도를 커버리지(자동 검증·방법만·없음, 지도에 든 진입점)가 붙은 인터랙티브 HTML 한 장으로 만든다 |
| `/dev:formal-setup` | 버그가 가장 비싼 코드를 TLA+ 같은 형식 검증으로 검사하는 프로젝트 전용 스킬을 만들고 유지한다 |
| `/dev:statechart` | TLA+ 모델을 TLC 로 검사하고, 규칙이 깨지는 가장 짧은 경로를 Mermaid 상태 차트로 그린다 |

운영과 설정을 돕는 스킬이다.

| 스킬 | 하는 일 |
|---|---|
| `/dev:reflect` | 되풀이되는 교정과 선호를 찾아 이 저장소를 고치는 PR 을 올린다 |
| `/dev:triage` | 채널에 올라온 이슈 보고를 분류하고, 스레드에 판정 답글 하나를 단다 |
| `/dev:repro-fix` | 분류된 버그를 실제 UI 에서 재현하고, 재현한 뒤에만 수정 PR 초안을 낸다 |
| `/dev:bot-ui` | 누르면 Claude Code 루틴을 깨우는 로컬 페이지를 만든다 |
| `/dev:setup` | 역할마다 쓸 서브에이전트 모델과 추론 예산을 `~/.claude/rules/dev-models.md` 에 쓴다 |
| `/dev:help` | 상황에 맞는 스킬을 고르고, 보낼 프롬프트를 써 준다 |

## 개인 낱말을 막는다

이 저장소를 고칠 때만 쓴다. 저장소 밖 `~/.claude/devkit.json` 에 이 저장소에 들어오면 안 되는 낱말(정규식)을 둔다. `scripts/check.py` 가 그 낱말이 들어오면 실패한다.

```json
{ "private_words": ["<내 앱·회사·계정 이름>"] }
```

## 이 저장소를 고친다

규칙은 `docs/authoring.md` 에 있다. 고친 뒤 검사를 돌린다.

```bash
python3 scripts/check.py
```

`check.py` 는 매니페스트, 스킬과 에이전트의 frontmatter, 본문이 가리키는 파일·스킬·원칙 이름, README 의 개수와 스킬 표, `private_words`, 작성자 메일을 검사하고, 이어서 스크립트의 `--self-test` 를 돌린다. CI 는 `skills/*/scripts/test/*.test.ts` 도 Node 22 로 돌린다. CI(`.github/workflows/check.yml`)도 push 와 PR 마다 `check.py` 를 돌린다.

커밋할 때마다 검사하려면 훅 경로를 한 번 지정한다. 이 저장소는 공개라 커밋 작성자 메일도 공개된다. 그래서 로컬 `user.email` 이 GitHub noreply 주소가 아니면 `check.py` 가 실패한다.

```bash
git config core.hooksPath .githooks
```

`main` 에 push 되면 `.github/workflows/release.yml` 이 그 판으로 태그와 GitHub Release 를 만든다. 그러니 `gh release create` 를 따로 부르지 않는다.

스킬에 문장을 더 쓰기 전에, 검사나 구조로 막을 수 있는지 먼저 본다.

## 출처

원칙, 플레이북, 스킬 상당수는 [pstack 원본 저장소](https://github.com/cursor/plugins/tree/main/pstack)(커밋 7a58391)를 고쳐 썼다. 원본의 스킬과 플레이북을 모두 옮겼고, 이름 대응표는 `docs/authoring.md` 에 있다.

Copyright (c) 2026 Lauren Tan, MIT License

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
