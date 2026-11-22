# 오토파일럿 (머지 없이)

`playbooks/autopilot-full.md` 플레이북을 돌리되 머지하지 않는다.

1. **5단계 대신 검증된 곳에서 멈춘다.** PR 마다 지금 head 에서 검증되고 초록이면 멈추고, PR 들을 운영자에게 넘긴다. 넘긴 뒤에는 운영자가 말하기 전에는 아무도 push 하지 않는다. 모든 루프 틱 프롬프트가 이 파일을 이름으로 적어 매 틱이 머지 없음 규칙을 보게 한다.
2. **PR 은 다른 PR 위에 지을 때만 쌓는다.** 3단계의 유일한 예외다. 그 PR 은 `playbooks/opening-a-pr.md` 대로 trunk 대신 다른 PR 의 브랜치를 base 로 삼는다. 2단계의 trunk rebase 대신 PR 마다 부모 PR 의 브랜치에 rebase 하고, 스택 뿌리는 trunk 에 rebase 한다. 아래 PR 에 새 head 가 생기면 그 위의 PR 들을 다시 쌓는다. 다시 쌓아도 `git patch-id` 가 그대로인 PR 은 판정을 유지한다.

**답:** 무엇이 머지됐는지 대신 PR 마다 판정을 나열한다.
