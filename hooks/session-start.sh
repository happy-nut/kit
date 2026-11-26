#!/bin/sh
f="${CLAUDE_PLUGIN_ROOT}/skills/mode/SKILL.md"
[ -f "$f" ] || exit 0
printf '/dev:mode 가 켜져 있다. 모든 요청을 아래 작업 방식으로 한다. 이 파일은 %s 이고, 본문의 상대 경로는 이 파일 기준이다.\n\n' "$f"
awk 'NR==1&&/^---$/{fm=1;next} fm&&/^---$/{fm=0;next} !fm' "$f"

r=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -f "$r/.verify/run.sh" ] || [ -f "$r/.verify/NONE" ] && exit 0
printf '\n이 저장소(%s)에는 사람 화면 밖에서 도는 격리 검증(.verify/run.sh)이 없다. 동작을 증명해야 하는 일을 받으면, 그 일보다 먼저 %s/skills/verify-setup/SKILL.md 를 Read 로 읽고 격리 검증을 세운다. 사용자가 만지는 앱이 없는 저장소면 .verify/NONE 에 그 이유 한 줄을 적어 커밋한다.\n' "$r" "$CLAUDE_PLUGIN_ROOT"
