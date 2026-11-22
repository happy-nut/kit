---
name: control-cli
description: "외부 서비스 없이 로컬 하네스를 만들거나 고쳐 대화형 CLI·TUI 를 몰고 들여다보고 프로파일한다. CLI 사용성 확인, 시작 시간 회귀, 메모리 누수, 멈춤, 프롬프트 흐름, 터미널 데모에 쓴다. 「CLI 직접 돌려 봐」, 「TUI 몰아 봐」, 「이 CLI 버그 재현해」, 「시작 시간 프로파일해」에 쓴다. /dev:control-cli"
disable-model-invocation: true
---

# CLI 몰기

대화형 CLI 를 손으로 찔러 보지 말고 다시 돌릴 수 있는 로컬 하네스로 돌린다. 저장소에 테스트·데모 하네스가 있으면 먼저 그것을 다시 쓴다. 없으면 표준 로컬 도구로 임시 하네스를 짠다. 모든 명령은 Bash 도구로 돌린다. Bash 는 대화형 입력을 받지 않으니 대화형 프로그램은 아래 tmux 나 PTY 하네스 안에서 띄운다.

## 어디에 쓰나

- 결정적인 입력으로 CLI·TUI 버그 재현.
- 키보드 흐름, 프롬프트, 인터럽트, 크기 바꾸기, 터미널 배치 확인.
- 버그 수정의 전과 후 기록(transcript) 남기기.
- 시작 시간, 느린 작업, 멈춤, 메모리 증가 프로파일.
- 설명보다 보여 주는 게 쉬울 때 짧은 터미널 데모 녹화.

## 하네스 루프

1. 시험할 명령과 가장 작은 재현 작업 공간을 정한다.
2. 이미 있는 로컬 하네스를 찾는다. 패키지 스크립트, e2e 테스트, 데모 녹화기, expect 스크립트, PTY 도우미.
3. 하네스가 없으면 결정적인 환경 변수를 준 격리된 터미널 세션에서 CLI 를 띄운다.
4. 상호작용 전에 지금 화면을 뜬다.
5. 한 번에 행동 하나를 보낸다. 글자, Enter, 화살표, Escape, Ctrl-C, 크기 바꾸기.
6. 다음 행동 전에 구체적인 화면 패턴이나 프롬프트를 기다린다.
7. 기록과 프로파일 산출물을 저장한다.
8. 세션을 깨끗하게 끝낸다.

## 하네스 고르기

- 저장소 하네스: 앱의 시작, 환경, 프롬프트를 알고 있으니 체크인된 스크립트를 먼저 쓴다.
- `tmux`: 세션 관리, `capture-pane`, `send-keys`, 붙기·떼기.
- PTY 탐침: tmux 가 없으면 짧은 Python, Node, Expect 스크립트.
- 런타임 인스펙터: CPU 프로파일, 힙 스냅숏, 살아 있는 평가에는 Node 나 Bun 인스펙터.
- 터미널 녹화기: 사용자가 데모를 원하면 저장소의 데모 도구나 asciinema 호환 도구.

## 최소 tmux 하네스

```bash
SESSION="cli-harness-$(date +%s)"
tmux new-session -d -s "$SESSION" -- <command-under-test>
tmux capture-pane -pt "$SESSION"
tmux send-keys -t "$SESSION" "help" Enter
tmux capture-pane -pt "$SESSION"
tmux kill-session -t "$SESSION"
```

Node CLI 는 이렇게 띄운다.

```bash
NODE_OPTIONS="--inspect=127.0.0.1:0" tmux new-session -d -s "$SESSION" -- <node-cli-command>
```

터미널 출력에서 인스펙터 주소를 찾는다. 프로파일이 필요하면 그 주소에 Chrome DevTools 프로토콜로 붙는 도구(CDP 클라이언트 스크립트를 Bash 로)를 쓴다.

## 최소 PTY 하네스

tmux 도 데모 하네스도 없는 저장소에서 결정적인 기다림이 필요하면 PTY 스크립트를 쓴다. 사용자가 다시 쓸 테스트로 더해 달라고 하지 않으면 임시로 둔다.

```python
import os
import pty
import select
import subprocess
import time

master_fd, slave_fd = pty.openpty()
proc = subprocess.Popen(
    ["<command>", "<arg>"],
    stdin=slave_fd,
    stdout=slave_fd,
    stderr=slave_fd,
    close_fds=True,
)
os.close(slave_fd)

deadline = time.time() + 30
buffer = b""
while time.time() < deadline:
    ready, _, _ = select.select([master_fd], [], [], 0.25)
    if not ready:
        continue
    chunk = os.read(master_fd, 4096)
    buffer += chunk
    if b"<ready text>" in buffer:
        os.write(master_fd, b"help\n")
        break

print(buffer.decode(errors="replace"))
proc.terminate()
os.close(master_fd)
```

CLI 가 더 풍부한 터미널 제어를 요구하면 `pty.fork()` 나 이미 있는 PTY 라이브러리를 쓴다.

## 프로파일 요령

성능 숫자를 보고하면 먼저 `/dev:bench`.

- 시작 시간 회귀: 같은 기계, 같은 환경, 같은 명령에서 기준(baseline)과 처치(treatment)의 시작 시간을 잰다.
- 느린 작업: CPU 프로파일을 켜고, 작업을 하고, 프로파일을 멈추고, 자기 시간(self-time) 상위 함수를 비교한다.
- 메모리 누수: 가능하면 GC 를 강제하고 힙 스냅숏을 뜬다. 작업을 되풀이하고, 다시 GC 를 강제하고, 스냅숏을 하나 더 뜬다.
- 멈춤: 인터럽트하기 전에 화면, 살아 있는 핸들·자원, 스택이나 CPU 샘플을 뜬다.

## 가드레일

- sleep 보다 결정적인 기다림을 쓴다. 꼭 sleep 해야 하면 이유를 적는다.
- 몰고 있는 세션에 자격 증명이나 파괴적인 명령을 보내지 않는다.
- 저장소에 테스트·데모 하네스가 이미 있지 않으면 하네스는 `/tmp` 에 둔다.
- 다른 저장소의 경로를 박아 넣지 않는다. 명령을 지금 저장소의 스크립트와 런타임에 맞춘다.
- 사용자가 남겨 달라고 하지 않으면 tmux 세션, 임시 폴더, 인스펙터 프로세스, 데모 산출물을 치운다.
