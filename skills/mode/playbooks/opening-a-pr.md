# PR 열기

다른 모든 플레이북의 끝에서 부른다.

trunk 에서 딴 git 워크트리에서 일하고, 관계없는 작업을 섞지 않는다. 홀로 착지할 수 있는 작은 커밋으로 rebase 한다. 커밋 전에 diff 에 `/dev:deslop` 을 돌린다.

제목은 `type(scope): subject` 다. 변경을 실어 나르는 실제 심볼이 있으면 그 이름을 쓴다. 본문은 40줄 안의 1분 브리핑이다. 아래 `##` 제목을 이 순서로 쓰고 빈 것은 뺀다. `## Why`, `## What changed`, `## Scope`, `## Tradeoffs`(리뷰어가 안 적으면 물어볼 버린 대안만), `## Blast Radius`, `## Verification`.

후속은 base 브랜치로 쌓는다. PR 은 ready 로 연다. `gh pr create` 를 `--draft` 없이 쓰거나, Origin CLI 가 저장소를 풀면 `origin pr create --status open` 을 쓴다. PR 을 열었다고 babysit 을 시작하지 않는다.
