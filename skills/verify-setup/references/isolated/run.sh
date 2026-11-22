#!/bin/sh
set -eu

here=$(cd "$(dirname "$0")" && pwd)
root=$(git -C "$here" rev-parse --show-toplevel)
image="verify-$(basename "$root")"
name="$image-$$"
out="${VERIFY_OUT_HOST:-$root/.verify-out}"

docker info >/dev/null 2>&1 || { echo "run.sh: no docker daemon (start colima, OrbStack, or Docker Desktop)" >&2; exit 2; }
docker build -q -f "$here/Dockerfile" -t "$image" "$root" >/dev/null

mkdir -p "$out"
status=0
docker run --name "$name" --shm-size=2g \
  -e ANTHROPIC_API_KEY -e CLAUDE_CODE_OAUTH_TOKEN \
  "$image" sh -c "${VERIFY_PREPARE:-true} && .verify/walk.sh ${VERIFY_SKILL:?set VERIFY_SKILL to the verify skill dir} $*" || status=$?
docker cp "$name:/work/.verify-out/." "$out/" 2>/dev/null || true
docker rm "$name" >/dev/null
echo "evidence: $out"
exit "$status"
