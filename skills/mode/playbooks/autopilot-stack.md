# 오토파일럿 (머지 없이)

**언제.** `autopilot-full.md` 에서 머지만 뺀 것. PR 대기열을 완전 자율로 만들고 검증한 뒤 사용자에게 넘겨 착지시키게 한다. PR 은 그것이 기대는 PR 위에만 쌓는다(「머지하지 말고 오토파일럿」, 「쌓기만 해, 출시는 내가」).

**소유.** `autopilot-full.md` 와 같이 판정을 소유한다. 착지는 사용자의 것이다.

## 단계

1. `autopilot-full.md` 를 돌리되 5단계 대신 검증된 곳에서 멈춘다.
   PR 마다 지금 head 에서 검증되고 초록이면 멈추고 사용자에게 넘긴다. 넘긴 뒤에는 사용자가 말하기 전에는 아무도 push 하지 않는다. 모든 루프 틱 프롬프트가 이 파일을 이름으로 적어 매 틱이 「머지 없음」 규칙을 보게 한다.
2. PR 은 다른 PR 위에 지을 때만 쌓는다.
   `autopilot-full.md` 3단계의 유일한 예외다. 그 PR 은 trunk 대신 다른 PR 의 브랜치를 base 로 삼는다(`opening-a-pr.md` 7단계). `autopilot-full.md` 2단계의 trunk rebase 대신 PR 마다 부모 PR 의 브랜치에 rebase 하고, 스택 뿌리만 trunk 에 rebase 한다. 아래 PR 에 새 head 가 생기면 그 위의 PR 들을 다시 쌓는다. 다시 쌓아도 `git patch-id` 가 그대로인 PR 은 판정을 유지한다.

## 답변에 넣을 것

- 무엇이 머지됐는지 대신 PR 마다 판정을 나열한다.
- 스택 순서와 사용자가 아래에서부터 착지시킬 명령(`gh pr merge <pr> --squash`).
