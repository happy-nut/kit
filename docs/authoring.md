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
| figure-it-out | `mode` 의 「맞춤 플레이북」 절 | |
| in-your-own-words | `mode` 의 「꼭 지킬 것」 첫 줄 | |
| sharpen | `sharpen` | |
| poteto-agent | `agents/worker.md` | 일 시작 전에 mode/SKILL.md 와 principles.md 를 읽음 |
| create/maintain-formal-verification-skill | `formal-setup` | 만들기·유지 두 절 |
| statechart | `statechart` | 코드 그대로. mise 가 없으면 `TLA2TOOLS` 로 |
| ketchup-video | `catchup-video` | 렌더는 HTML 슬라이드 + 헤드리스 브라우저 + ffmpeg |
| make-bot-ui | `bot-ui` | 봇 웹훅 대신 Claude Code 루틴 |
| setup-pstack | `setup` | `~/.claude/rules/dev-models.md`(역할별 모델). 역할 줄 arena → design, interrogate → review |
| poteto-help | `help` | |
| benny(자동화 팩) | `triage` + `repro-fix` | Cursor Automations 대신 Claude Code 루틴 |
| cursor-team-kit 의 deslop, control-ui, control-cli | `deslop`, `control-ui`, `control-cli` | 다른 플러그인 대신 kit 안에 둠 |
| bro | `bro` | |

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
| 다른 스킬 부르기(`/name`) | 그 `SKILL.md` 를 Read 로 읽고 따른다. Skill 도구는 모델 호출이 잠긴 스킬을 거절한다 |
| `poteto-agent` | `dev:worker` |
| `pstack-models.mdc` | `~/.claude/rules/dev-models.md` |
| Gemini 등 다른 회사 모델 | `model` 을 빼서 부모 모델로 |

## 모델

`Agent` 의 `model` 은 `opus`, `sonnet`, `haiku`, `fable` 만 받는다. 역할별 기본값과 물러나는 순서는 `skills/mode/SKILL.md` 「서브에이전트」 절에만 쓴다.

## 글

- 본문은 한국어. 짧은 평서문, 한 문장 한 생각. 긴 대시(—) 쓰지 않는다.
- 에이전트가 읽는 글이다. 비유·수사 없이 할 일과 판단 기준만. 원문에 있던 구체 기준·숫자·예외는 빠뜨리지 않는다(번역하면서 줄이지 않는다).
- 글을 줄인 PR 은 `python3 -I scripts/shrink.py` 출력(사라진 숫자·코드 이름·인용 낱말)을 본문에 붙이고, 하나마다 일부러 뺐는지 잘렸는지 적는다.
- 같은 규칙은 한 파일에만 쓰고 다른 곳은 그 절을 가리킨다.
- 원칙, mode, correct, setup 은 원본과 뜻이 같게 둔다. 원본에 없는 규칙을 더하지 않는다.
- 사람·앱·개인 도구 이름을 쓰지 않는다(`check.py` 가 `private_words` 로 막는다).
- frontmatter: `name`, `description`(한 줄, 따옴표. 한국어 뜻 + 「…」, 「…」에 쓴다 꼴의 한국어 트리거 문구 + `/dev:<이름>`. 영어 Use for 와 영어 인용 문구는 `check.py` 가 막는다), `disable-model-invocation: true`.
- Cursor 전용이라 Claude Code 에서 못 하는 단계는 지우거나 위 표대로 바꾼다. 「Skipped」 같은 줄을 남기지 않는다.
