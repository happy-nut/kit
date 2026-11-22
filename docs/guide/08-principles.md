# 원칙 이름으로 방향을 잡는다

kit 에는 원칙 24개가 [`principles.md`](../../skills/mode/principles.md) 한 파일에 절마다 하나씩 들어 있다. `/dev:mode` 는 여러 단계짜리 일을 시작할 때마다 그 색인을 읽고, 일이 건드리는 원칙의 절을 끝까지 읽어 적용하고, 답에서 적용한 원칙을 이름으로 대며 그 원칙이 바꾼 결정을 함께 쓴다.

원칙은 부르는 것이 아니다. 이름으로 방향을 잡는다. 이름마다 에이전트가 이미 읽은 온전한 규칙을 가리키므로, 한 구절이 지시 한 문단보다 더 정확하게 일을 돌려세운다.

## 실제로 방향 잡기

에이전트가 이미 있는 어댑터 셋 위에 새 어댑터를 덧붙이려 한다고 하자.

```text
Subtract Before You Add 로 가. 낡은 어댑터부터 지우고, 남은 것으로 설계해.
```

빌드가 통과했다고 성공이라 한다고 하자.

```text
Prove It Works 적용해. 실제 가져오기 흐름을 돌리고 쓰인 레코드를 보여 줘.
```

병렬 시도 둘이 같은 브랜치에 쓰려 한다고 하자.

```text
Separate Before Serializing Shared State 로 가. 시도마다 자기 워크트리를 줘. 락은 쓰지 마.
```

구절마다 통하는 건 그 뒤의 규칙이 구체적이어서다. 에이전트는 여전히 답에서 그 규칙이 어떤 결정을 바꿨는지 말해야 한다. 원칙을 인용했는데 바뀐 결정이 없으면 규칙 이름만 대고 적용하지 않은 것이다.

## 24개를 짧게

핵심 원칙은 얼마나 지을지, 언제 설계를 다시 생각할지 정한다.

- [Laziness Protocol](../../skills/mode/principles.md#laziness-protocol) 은 지우는 쪽과 문제를 푸는 가장 작은 변경을 고른다.
- [Foundational Thinking](../../skills/mode/principles.md#foundational-thinking) 은 로직을 쓰기 전에 핵심 자료 구조를 고른다.
- [Redesign from First Principles](../../skills/mode/principles.md#redesign-from-first-principles) 는 새 요구를 처음부터 있었던 것처럼 녹여 넣는다.
- [Attack the Premise](../../skills/mode/principles.md#attack-the-premise) 는 실패한 고침 둘 이상이 공유한 전제를 적고, 다음 고침 전에 그 전제를 직접 시험한다.
- [Subtract Before You Add](../../skills/mode/principles.md#subtract-before-you-add) 는 위에 짓기 전에 죽은 짐을 치운다.
- [Minimize Reader Load](../../skills/mode/principles.md#minimize-reader-load) 는 읽는 사람이 머리에 들고 있어야 하는 층과 숨은 상태를 접는다.
- [Outcome-Oriented Execution](../../skills/mode/principles.md#outcome-oriented-execution) 은 버릴 호환 상태를 지키지 않고 다시 쓰기를 목표 설계로 모은다.
- [Experience First](../../skills/mode/principles.md#experience-first) 는 구현 편의보다 사용자가 얻는 결과를 고른다.
- [Exhaust the Design Space](../../skills/mode/principles.md#exhaust-the-design-space) 는 선례가 없을 때 겨루는 시제품 두세 개를 만든다.
- [Build the Lever](../../skills/mode/principles.md#build-the-lever) 는 일을 하거나 증명하는 스크립트를 만들어 리뷰어가 다시 돌릴 수 있게 한다. 에이전트가 같은 일을 자꾸 손으로 하면, 있었으면 하는 도구나 스킬을 직접 쓰게 한다. 스크립트가 한 단계를 매번 같은 방식으로 할 수 있으면 스크립트를 쓰고, 에이전트는 판단할 일에 아낀다.

구조 원칙은 상태, 검증, 호환이 어디에 사는지 정한다.

- [Model the Domain](../../skills/mode/principles.md#model-the-domain) 은 되풀이되는 규칙을 흩어진 조건문이 아니라 구조 하나에 담는다.
- [Boundary Discipline](../../skills/mode/principles.md#boundary-discipline) 은 경계에서 검증하고 안쪽 타입은 믿는다.
- [Type System Discipline](../../skills/mode/principles.md#type-system-discipline) 은 잘못된 상태를 표현할 수 없게 한다.
- [Make Operations Idempotent](../../skills/mode/principles.md#make-operations-idempotent) 는 재시도가 같은 끝 상태로 모이게 한다.
- [Migrate Callers Then Delete Legacy APIs](../../skills/mode/principles.md#migrate-callers-then-delete-legacy-apis) 는 호출부를 옮기고 옛 API 를 한 물결에 지운다.
- [Separate Before Serializing Shared State](../../skills/mode/principles.md#separate-before-serializing-shared-state) 는 조율을 더하기 전에 공유부터 없앤다.

검증 원칙은 무엇을 증거로 칠지 정한다.

- [Prove It Works](../../skills/mode/principles.md#prove-it-works) 는 대리 지표가 아니라 실제 산출물을 확인한다.
- [Fix Root Causes](../../skills/mode/principles.md#fix-root-causes) 는 코드를 바꾸기 전에 재현하고 원인까지 거슬러 간다.
- [Sequence Work into Verifiable Units](../../skills/mode/principles.md#sequence-work-into-verifiable-units) 는 작은 단위마다 검사로 끝내고 다음 단위를 시작한다.
- [Test Behavior, Not Implementation](../../skills/mode/principles.md#test-behavior-not-implementation) 은 코드의 사용자가 관찰할 수 있는 것을 단언한다. 그래서 그 동작이 깨지면 테스트가 실패하고, 내부만 바뀌면 살아남는다.
- [Explain the Number](../../skills/mode/principles.md#explain-the-number) 는 잰 숫자를 누가 믿거나 보고하기 전에, 무엇이 그 숫자를 묶는지 이름 대고 다른 것을 잰 게 아님을 배제한다. [`/dev:bench`](../../skills/bench/SKILL.md) 가 이것을 실제 실행으로 답하는 일곱 질문으로 바꾼다.

위임 원칙은 병렬 일이 엉키지 않게 한다.

- [Guard the Context Window](../../skills/mode/principles.md#guard-the-context-window) 는 대량 읽기를 서브에이전트로 보내고 본 대화에는 찾은 것만 둔다.
- [Never Block on the Human](../../skills/mode/principles.md#never-block-on-the-human) 은 되돌릴 수 있는 일을 진행하고 결과를 보인다.

메타 원칙이 하나 있다.

- [Encode Lessons in Structure](../../skills/mode/principles.md#encode-lessons-in-structure) 는 두 번 되풀이한 조언을 린트, 검사, 스크립트로 바꾼다. [`/dev:correct`](../../skills/correct/SKILL.md) 가 이것을 저장소 전체에 적용한다. [내 것으로 만든다](./09-make-it-yours.md#환경을-고친다)에서 보여 준다.

목록을 외우지 않는다. 지금은 훑어보고, 여기 있는 이름 하나면 막았을 일을 에이전트가 하는 것을 볼 때 돌아온다. 그렇게 써야 낱말이 몸에 붙는다.

다음: [내 것으로 만든다](./09-make-it-yours.md).
