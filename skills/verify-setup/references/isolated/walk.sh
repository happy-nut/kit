#!/bin/sh
set -eu

skill="${1:?usage: walk.sh <verify skill dir> [features...]}"
shift
out="${VERIFY_OUT:-/work/.verify-out}"
mkdir -p "$out"

if [ -z "${ANTHROPIC_API_KEY:-}${CLAUDE_CODE_OAUTH_TOKEN:-}" ]; then
  echo "walk.sh: ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN must be set" >&2
  exit 2
fi

prompt=$(sed -e "s#{{SKILL}}#$skill#g" -e "s#{{OUT}}#$out#g" -e "s#{{FEATURES}}#${*:-diff}#g" "$(dirname "$0")/walk-prompt.md")

exec xvfb-run -a -s "-screen 0 1600x1000x24" \
  claude -p "$prompt" --permission-mode bypassPermissions --output-format text > "$out/report.md"
