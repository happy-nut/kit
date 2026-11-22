# kit 에서 일하는 에이전트에게

규칙마다 그것을 강제하는 장치를 짝지어 둔다. 장치가 없는 규칙은 판단이 필요한 것만 남긴다.

| 규칙 | 강제하는 장치 |
|---|---|
| 사람을 기다리며 멈추는 길은 하나다. 작업 목록을 지우지 않고 `wrap_up` 을 `blocked: true` 로 부른다. 사람이 답하면 멈춘 단계부터 끝까지 간다 | `hooks/open-plan-stop.py` 가 목록을 보관했다가 다음 사람 메시지에 되살린다. `scripts/test_hooks.py` 의 「Stop 훅 전체 여러 턴」 |
| Stop 훅의 통과 조건을 넓히면, 통과한 다음 턴까지 모든 Stop 훅을 함께 시험한다 | `scripts/test_hooks.py` 의 「Stop 훅 전체 여러 턴」. 새 통과 조건마다 「통과 뒤 사람이 답함 → 이어 가지 않음」 장면을 더한다 |
| 교정은 프로젝트의 장치로 남긴다 | `hooks/correction-stop.py` |
| 사람에게 보이는 글은 한국어 | `hooks/korean-stop.py`, `hooks/tool-text.py` |
| 코드에 새 주석을 넣지 않는다 | `hooks/no-new-comments.py` |
| 바뀐 파일이 없는 PR 은 머지하지 않는다 | `hooks/guard-bash.py` |
| 개인 저장소에서 연 PR 은 머지까지 하고 턴을 닫는다 | `hooks/open-pr-stop.py` |
| 스킬 글을 줄여도 `evals/` 상황의 근거 문장은 남긴다 | `scripts/check.py` 의 `check_evals` |
| 키트에 개인 이름·도구 이름을 넣지 않는다 | `scripts/check.py` 의 개인 낱말 검사 |

둘째 줄의 「통과 뒤 장면을 더한다」는 판단이다. 어떤 장면이 다음 턴인지는 훅마다 다르다.
