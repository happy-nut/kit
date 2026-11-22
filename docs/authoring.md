# devkit 작성 규칙

devkit 은 Claude Code 전용 작업 방식 플러그인이다. pstack(MIT, Lauren Tan)에서 출발했지만 그 위에 얹지 않는다. 필요한 것을 Claude Code 에 맞게 다시 쓰고, 이 사용자의 습관을 섞어 스스로 서게 한다. 출처와 라이선스는 README 맨 아래.

## 구조

```
skills/mode/SKILL.md            라우터. /dev:mode
skills/mode/principles.md       원칙 전부(한 파일)
skills/mode/playbooks/<이름>.md  플레이북
skills/mode/references/         플레이북이 쓰는 참고 문서
skills/mode/scripts/            플레이북이 쓰는 스크립트
skills/<스킬>/SKILL.md           사람이 /dev:<스킬> 로 부르는 워크플로 스킬
agents/<이름>.md                 서브에이전트(subagent_type 은 devkit:<이름>)
scripts/check.py                저장소 검사. 고치면 반드시 돌린다
```

## 이름 대응 (pstack → devkit)

| pstack | devkit | 비고 |
|---|---|---|
| poteto-mode | `mode` | 라우터 |
| principle-* 24개 | `skills/mode/principles.md` | 한 파일, 절마다 `## <영어 이름>` |
| architect + arena | `design` | 병렬 설계 탐색, 기반 고르기, 좋은 점 접붙이기 |
| swarm | `swarm` | |
| interrogate + blast-radius | `review` | 다중 모델 적대 리뷰 + 파급 범위 |
| no-comments + comment-sicko | `no-comments` + `agents/comment-reviewer.md` | |
| correct | `correct` | |
| tdd | `tdd` | |
| benchmark-checklist | `bench` | |
| how | `how` | |
| why + teach | `why` | teach 는 why 안의 「how+why 엮어 설명」 절 |
| recall | `recall` | |
| reflect + automate-me | `reflect` | devkit 자체를 고치는 PR 까지 |
| ketchup | `catchup` | |
| show-me-your-work | `log` | |
| create/maintain-verification-skill | `verify-setup` | 만들기·유지 두 절 |
| unslop + technical-writing | `write` | 한국어 글 기준. 손님 글은 korean-humanizer 로 넘김 |
| typescript-best-practices | `ts` | |
| figure-it-out, in-your-own-words, sharpen | `mode` 안의 절 | 따로 스킬 두지 않음 |
| poteto-agent | `agents/worker.md` | 일 시작 전에 mode/SKILL.md 와 principles.md 를 읽음 |
| create/maintain-formal-verification-skill | `formal-setup` | 만들기·유지 두 절 |
| statechart | `statechart` | 코드 그대로. mise 가 없으면 `TLA2TOOLS` 로 |
| ketchup-video | `catchup-video` | 렌더는 HTML 슬라이드 + 헤드리스 브라우저 + ffmpeg |
| make-bot-ui | `bot-ui` | 봇 웹훅 대신 Claude Code 루틴 |
| setup-pstack | `setup` | `~/.claude/devkit.json`(개인 저장소·금지 낱말·역할별 모델) |
| poteto-help | `help` | |
| Orchestrate 플레이북 | `mode` 의 `playbooks/orchestrate.md` | Project tracker 대신 git 밖 노트 파일, 워커는 `Agent` |
| benny(자동화 팩) | `triage` + `repro-fix` | Cursor Automations 대신 Claude Code 루틴 |
| bro | (옮기지 않음) | 방금 한 말을 쉬운 말로 다시 하기. `write` 가 같은 일을 더 넓게 한다 |

원본을 따라잡을 때는 프로젝트 스킬 `.claude/skills/upstream` 을 쓴다. 기준 커밋은 README 맨 아래 원본 링크 옆 한 곳에만 적는다.

다른 스킬을 가리킬 때는 이름(`/dev:design`)으로, 같은 스킬 안 파일은 그 SKILL.md 기준 상대 경로(`playbooks/bug-fix.md`)로, 다른 스킬의 파일은 `../<스킬>/...` 로 쓴다. pstack 이름(poteto, pstack, principle-*)은 본문에 남기지 않는다.

## Claude Code 로 옮겨 쓰기

| Cursor 쪽 | Claude Code 쪽 |
|---|---|
| `Task` | `Agent` (`subagent_type`, `model`, `isolation: "worktree"`, `run_in_background`) |
| `AskQuestion` | `AskUserQuestion` |
| todolist | 세션의 작업 목록 도구(데스크톱 앱이면 update_plan, 아니면 TodoWrite) |
| readonly 서브에이전트 | `Explore` + 브리프에 「파일을 고치지 마라」 |
| cloud agent | `Agent` + `isolation: "worktree"` |
| `/loop` | Claude Code `/loop` 스킬 또는 ScheduleWakeup |
| Bugbot | GitHub PR 리뷰 코멘트 전반(사람·봇) |
| Cursor 대화 기록 | `~/.claude/projects/<경로의 / 와 . 을 - 로>/<세션>.jsonl`, 현재 작업 폴더 것만 |
| control-ui / control-cli | 브라우저 도구(Claude in Chrome, 내장 브라우저, playwright), 터미널 실행 |
| deslop | `/simplify` 또는 diff 를 직접 다시 읽어 서술 주석·근거 없는 방어 코드·죽은 호환 경로·관계없는 수정을 지움 |

## 모델

`Agent` 의 `model` 은 `opus`, `sonnet`, `haiku`, `fable` 만 받는다. 다른 회사 모델은 없다.

| 역할 | 모델 |
|---|---|
| 코드·판단·글 | `opus` |
| `skills/mode/SKILL.md` 「서브에이전트」 절의 예외인 일 | `fable` |
| 검증·기계적 편집·스웜 워커·넓게 읽기 | `sonnet` |
| 설계·리뷰 패널(3인) | `fable`, `opus`, `sonnet` 하나씩. 같은 회사라 다양성이 약하다는 걸 결과에 적는다 |

`Agent` 가 지정한 모델을 못 찾거나 거부하면 `model` 을 빼고 다시 불러 지금 세션의 모델을 그대로 승계하고 그렇게 말한다. 서브에이전트를 못 띄운 채 멈추지 않는다.

## 글

- 본문은 한국어. 짧은 평서문, 한 문장 한 생각. 긴 대시(—) 쓰지 않는다.
- 에이전트가 읽는 글이다. 비유·수사 없이 할 일과 판단 기준만. 원문에 있던 구체 기준·숫자·예외는 빠뜨리지 않는다(번역하면서 줄이지 않는다).
- 글을 줄인 PR 은 `python3 -I scripts/shrink.py` 출력(사라진 숫자·코드 이름·인용 낱말)을 본문에 붙이고, 하나마다 일부러 뺐는지 잘렸는지 적는다.
- `evals/<스킬>.md` 가 있는 스킬을 줄이면 줄이기 전과 뒤에 그 상황을 `skills/mode/playbooks/eval.md` 로 돌리고, 기대 결정이 그대로인지 PR 본문에 적는다. 근거 문장이 스킬에서 사라지면 `check.py` 가 실패한다.
- 같은 규칙은 한 파일에만 쓰고 다른 곳은 그 절을 가리킨다. `check.py` 의 `check_single_source` 가 훅 표, README 개수, 설치 경로, 정해 둔 규칙 문장을 검사한다.
- frontmatter: `name`, `description`(한 줄, 따옴표. 한국어 뜻 + 영어 트리거 문구 + `/dev:<이름>`), `disable-model-invocation: true`.
- Cursor 전용이라 Claude Code 에서 못 하는 단계는 지우거나 위 표대로 바꾼다. 「Skipped」 같은 줄을 남기지 않는다.

## 이 사용자의 규칙 (모든 파일에 녹인다)

- 저장소 구분: 개인 목록은 devkit 밖 `~/.claude/devkit.json` 에(없으면 모두 회사). 본문에서는 `/dev:mode` 의 「저장소 구분」을 가리키기만 한다. 사람·앱·개인 도구 이름을 devkit 에 쓰지 않는다(`check.py` 가 막는다). 개인은 「고쳐」가 머지까지, 「배포」가 배포 뒤 확인까지. 회사는 머지·배포·공유 브랜치 push·팀 채팅·티켓 쓰기를 사용자가 그 말을 했을 때만.
- 갈림길은 묻지 않는다. 실행해 알 수 있으면 프로토타입으로 정하고, 아니면 가장 나은 쪽으로 하고 이유를 보고한다. 질문은 취향·제품 결정 하나만.
- 질문·「논의하자」에는 답만. 바꾸지 않는다.
- 「됐다」는 눈으로 본 결과다. 화면 변경은 실제로 띄워 기능마다 스크린샷. 백엔드 값만 보지 말고 화면 값까지.
- 교정을 받을 때마다 장치로 막는다(`/dev:correct`). 두 번째를 기다리지 않는다.
- 사용자에게 하는 말은 한국어. 손님이 읽는 한국어 글은 korean-humanizer 를 거쳐 승인받는다.
- 저장소의 `AGENTS.md`·`CLAUDE.md` 가 devkit 보다 앞선다.
