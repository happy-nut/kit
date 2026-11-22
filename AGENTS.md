# kit 에서 일하는 에이전트에게

규칙마다 그것을 강제하는 장치를 짝지어 둔다. 장치가 없는 규칙은 판단이 필요한 것만 남긴다.

| 규칙 | 강제하는 장치 |
|---|---|
| 키트에 개인 이름·도구 이름을 넣지 않는다 | `scripts/check.py` 의 `private_words` 검사 |
| 커밋 작성자 메일은 GitHub noreply 다 | `scripts/check.py` 의 작성자 메일 검사 |
| 본문이 가리키는 스킬·에이전트·원칙·파일은 있어야 한다 | `scripts/check.py` 의 참조 검사 |
| README 의 개수와 스킬 표는 실제와 같다 | `scripts/check.py` 의 README 검사 |
| 원칙, mode, correct, setup 은 원본과 뜻이 같다 | 판단. 원본을 따라잡을 때 `.claude/skills/upstream` 으로 견준다 |
