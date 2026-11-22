# 워크트리·시뮬레이터 정리

1. 스냅샷을 찍고 감사한다. `df -h /` 를 기록하고 `../scripts/worktree-audit.sh [-b <pr-base-ref>] [repo-path]` 를 돌린다(principles.md 의 Build the Lever). `-b` 가 없으면 `IN_BASE` 를 `origin/HEAD` 에 대어 보니, PR 이 다른 브랜치를 겨누면 `-b origin/<branch>` 를 준다. 스크립트는 경로를 손으로 치지 않고 `git worktree list` 에서 읽는다. 손으로 친 `myrepo-worktrees/x` 는 `.claude/worktrees/x` 에 사는 것을 놓친다(principles.md 의 Encode Lessons in Structure). 워크트리마다 크기, 나이, 머지 여부, 커밋 안 한 작업, PR 상태, 그것을 다룬 가장 최근 세션으로 분류하고 묶음을 제안한다. 기록 훑기가 느리니 백그라운드로 돌린다.
2. 묶음은 조언이지 허락이 아니다. 고정된 세션과 진행 중인 세션이 진짜 산출물이다(principles.md 의 Prove It Works). 그 목록을 사용자나 세션 목록에서 받아 후보마다 대어 본다. 스크립트가 사용자가 고정해 둔 워크트리를 `safe` 로 찍은 적이 있다. 고정 목록이 이긴다.
3. 지우기 전에 쓰임을 확인한다. `verify-recent-chat` 행마다, 그리고 의심 가는 것마다 서브에이전트를 펼쳐 기록을 읽고, 그 세션이 고정됐거나 진행 중인지와 어느 워크트리를 다루는지 보고받는다(principles.md 의 Guard the Context Window, 기록은 덩치가 크다). 고정된 세션은 백그라운드 서브에이전트로 형제 워크트리에 설계 겨루기와 재현 트리를 띄운다. 그 이름이 세션 목록에 안 보여도 쓰이는 중이다. 서브에이전트마다 일에 맞는 수준을 `/dev:mode` 「서브에이전트」 절대로 고른다.
4. 되돌릴 수 없는 손실 앞에서 멈춘다. `wip:N` 은 추적 중인 파일의 커밋 안 한 편집 N 개다. diff 를 보이고 결정을 먼저 받는다. 깨끗한 워크트리를 지우는 것은 브랜치에서 되살릴 수 있지만 커밋 안 한 작업은 사라진다. `scratch:N` 은 추적 안 하는 버릴 파일이라 지워도 되지만 파일 이름을 적는다. `/dev:mode` 「자율」 절대로, 깨끗하고 머지됐고 쓰이지 않는 것은 진행한다. `wip` 와 쓰이는 중인 것은 멈춘다.
5. 확인된 것만 지운다. 경로마다 `git worktree remove --force <path>`. 무시된 빌드 산출물 때문에 폴더가 남으면 `rm -rf` 로 지우고 `git worktree prune`. 브랜치 ref 는 남으니 커밋은 잃지 않는다. `df -h /` 와 다시 뽑은 목록으로 확인한다.
6. 시뮬레이터와 다른 공간을 정리한다. 보통 시뮬레이터가 다음으로 크다. `xcrun simctl --set testing delete all`(XCTestDevices 복제본), `xcrun simctl delete unavailable`, `xcrun simctl runtime list` 뒤 옛 런타임은 `runtime delete <id>`. 더 필요하면 Xcode `DerivedData` 와 `iOS DeviceSupport`, 패키지 캐시(pnpm, uv, brew, yarn). 사용자가 남기라고 하지 않은 캐시만 지운다.

코드 리뷰가 실수를 잡아 주지 않는 채 사용자 상태를 지우는 유일한 플레이북이다. 그래서 위의 관문이 리뷰다.

**답:** `df -h /` 전후와 되찾은 공간, 지운 워크트리, 남긴 것마다 한 줄 이유(어느 세션이 쓰는 중인지, 또는 커밋 안 한 작업).
