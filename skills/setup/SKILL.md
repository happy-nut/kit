---
name: setup
description: "devkit 이 역할마다 쓸 모델과 추론 예산을 정한다. 쓸 수 있는 모델을 찾아 스킬 기본값을 덮는 규칙 파일 ~/.claude/rules/dev-models.md 를 쓴다. Use for /dev:setup, \"configure devkit models\", \"devkit budget\", or changing devkit's model choices."
disable-model-invocation: true
---

# devkit 설정

`~/.claude/rules/dev-models.md` 를 쓴다. Claude Code 는 `~/.claude/rules/` 의 모든 `.md` 파일을 새 세션마다 읽으므로, 이 파일이 역할별 모델을 정하는 늘 적용되는 규칙이 된다.

## 단계

### 1. 쓸 수 있는 모델 찾기

이 세션에서 `Agent` 에 넘길 수 있는 모델을 센다. `Agent` 도구 스키마의 `model` 값 하나하나에 `effort` 값 하나씩을 붙인 것이 찾은 모델이다. 믿을 수 있는 출처는 이것뿐이다. 하나도 못 찾으면 쓸 수 있는 모델을 사용자에게 붙여 넣어 달라고 한다. 쓸 수 있다고 확인하지 않은 실제 모델은 쓰지 않는다. 실제 모델은 `<model> <effort>` 로 쓴다(예: `opus xhigh`). 노력 값이 마지막 낱말이다. `inherit-parent` 와 `auto` 는 찾은 모델이 아니어도 언제나 쓸 수 있다.

### 2. 지금 상태 읽기

역할과 모델의 기본 대응은 아래 5단계의 규칙 모양이다. `~/.claude/rules/dev-models.md` 가 있으면 읽고 그 `# budget` 줄과 역할 값을 지금 선택으로 본다. 없으면 기본값에서 시작한다. 역할이 5단계에 없는 줄(`hardest tasks`, `reflect tooling`, `why investigators` 같은)은 은퇴한 역할이다. 지운다.

`# defaults: 3` 줄이 없는 규칙은 옛 설정에서 왔다. 옛 설정은 모든 역할을 한 줄씩 썼으므로 그 값 일부는 선택이 아니라 옛 기본값이다. 3단계 전에 이 값들을 바꾼다.

- `design cross-judge pool` 목록이 정확히 `fable *` 하나, `opus *` 하나, `inherit-parent` 하나로(순서 무관) 되어 있으면 5단계의 그 역할 목록으로 바꾼다. `fable` 과 `opus` 는 같은 회사라, `fable` 항목은 `opus` 항목도 심사할 수 있는 곳에서만 심사할 수 있었다.
- `# budget: unlimited` 줄은 `large` 가 된다. 어떤 역할도 `xhigh` 위로 돌지 않기 때문이다.

그 밖의 값은 모두 사용자의 선택이라 그대로 둔다. `inherit-parent`·`auto` 값도 모두 그렇다. 바꾼 값을 사용자에게 알린다.

### 3. 예산 정하기, 대응, 확인

**(a) 예산을 묻는다.** 자유 입력보다 `AskUserQuestion` 을 쓴다. 이 세 선택지를 이 이름 그대로 내고, 규칙에 예산이 적혀 있으면 지금 예산을 말한다. 규칙이 없으면 `large` 가 스킬 기본값과 같다고 말한다.

- `large: xhigh 추론`
- `medium: high 추론`
- `small: medium 추론`

**(b) 적용한다.** 작업 표를 스킬 기본값으로 만든다. 다시 돌리는 경우에는 사용자가 모델 이름, 목록, 별칭(`inherit-parent`, `auto`)으로 바꾼 역할을 그대로 둔다. 모델 이름(`opus`, `sonnet`, `haiku`, `fable`) 하나하나가 따로 계열이다. 역할마다 목표 노력 값이 있다. 기본값의 노력 값을 예산만큼 옮긴 것이다. `large` 는 그대로, `medium` 은 한 칸 내리고, `small` 은 두 칸 내린다. 사다리는 `xhigh` > `high` > `medium` > `low` 다. 어떤 역할도 `xhigh` 위로 돌지 않고, 사다리 맨 아래에 닿은 목표는 거기 머문다. 기본값 대부분이 `xhigh` 이고, 예산 이름이 그 값들이 닿는 곳을 말한다. 역할의 모든 실제 모델(패널 항목 포함)의 노력 값을 그 역할의 목표로 바꾼다. 결과가 찾은 모델이 아니면 같은 계열에서 목표 이하 중 가장 높은 노력 값의 찾은 모델을 쓰고, 그것도 없으면 그 역할을 고를 것이 필요하다고 표시한다. `inherit-parent` 와 `auto` 는 바뀌지 않는다. 그래서 `medium` 은 `opus xhigh` 를 `opus high` 로, `opus high` 를 `opus medium` 으로 바꾸고, `small` 은 각각 `opus medium` 과 `opus low` 로 바꾼다.

**(c) 역할을 보이고 확인한다.** 모든 역할과 그 모델을 보이고, 찾은 모델에 없는 실제 모델은 고를 것이 필요하다고 표시한다. 2단계에서 지운 줄도 모두 적는다. 그대로 받을지, 특정 역할을 바꿀지 묻는다. 선택지는 `xhigh` 이하의 찾은 모델과 `inherit-parent`, `auto` 다(둘 다 이 역할이 부모 대화의 모델로 돈다는 뜻이다). 자유 입력보다 `AskUserQuestion` 을 쓴다. 패널 역할(`design runners`, `review reviewers`)의 값은 목록이고, 별칭 항목을 포함해 항목 하나에 서브에이전트 하나가 뜨므로 목록 길이가 인원수다. `design cross-judge pool` 도 목록이지만 `/dev:design` 은 심사자 하나만 돌린다. 부모와 다른 회사의 값만 목록 순서대로 시도하므로, 원하는 순서로 놓는다. `fable` 과 다른 Claude 모델은 같은 회사다. `inherit-parent` 나 `auto` 값은 심사하지 않는다. `swarm workers` 는 경주나 비교가 갈래마다 다른 모델을 정하지 않는 한 모든 워커의 기본 모델이다.

### 4. 검증

쓰는 모든 실제 모델은 찾은 모델에 있고 `xhigh` 이하다. `inherit-parent` 와 `auto` 는 언제나 통과한다. 고른 실제 모델을 쓸 수 없으면 멈추고 다시 묻는다.

### 5. 규칙 쓰기

`~/.claude/rules/dev-models.md` 를 frontmatter 없이 쓴다. 주석 줄, `# defaults: 3` 줄, 고른 이름과 그 이름이 말하는 노력 값을 적은 `# budget` 줄, 그리고 `/dev:mode` 가 쓰는 이름으로 역할마다 한 줄. 다시 돌려도 같은 결과가 나오게 파일 전체를 덮어쓴다. 역할 줄을 `CLAUDE.md` 나 `AGENTS.md` 에 쓰지 않는다. 모양:

```
# devkit 역할별 모델. 역할마다 한 줄. 줄을 지우면 그 역할은 스킬 기본값으로 돌아간다.
# 값이 `inherit-parent` 나 `auto` 면 그 역할은 부모 대화의 모델로 돈다(`Agent` 의 `model` 을 뺀다). 패널 목록의 별칭 항목도 인원수에 든다.
# defaults: 3
# budget: large (xhigh)
feature, refactoring: opus xhigh
bug-fix: opus xhigh
perf-issue: opus xhigh
hillclimb: opus xhigh
judgment and prose: opus xhigh
design runners: fable high, opus high, inherit-parent
design cross-judge pool: opus high, inherit-parent
swarm workers: opus high
review reviewers: fable high, opus high, inherit-parent
```

### 6. 확인

규칙을 썼고 새 세션부터 적용된다고 말한다. 이 스킬을 다시 돌리면 고쳐진다.

### 7. 검증 스킬 제안 (한 번)

프로젝트에 진짜 앱을 몰아 증명하는 방법(`verify-*` 스킬이나 기존 하네스)이 있는지 본다. 없으면 한 번만 제안한다. 「에이전트가 사용자처럼 앱을 몰아 변경이 동작하는지 증명하게 하는 프로젝트 전용 검증 스킬을 만들까요? `/dev:verify-setup` 으로 만들 수 있어요.」 그러자고 하면 `/dev:verify-setup` 을 따른다. 아니면 더 권하지 않고 넘어간다.

### 8. 형식 검증 스킬 제안 (한 번)

프로젝트에 형식 검증 스킬(모델 검사기, 증명, 다른 검증기를 코드에 돌리는 프로젝트 스킬)이 이미 있는지 본다. 없으면 한 번만 제안한다. 「테스트가 닿는 경우만이 아니라 범위 안의 모든 경우에 코드의 핵심 속성이 성립함을 증명하는 형식 검증 스킬을 만들까요? `/dev:formal-setup` 으로 만들 수 있어요.」 그러자고 하면 `/dev:formal-setup` 을 따른다. 아니면 더 권하지 않고 넘어간다.
