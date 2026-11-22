너는 이 앱을 처음 써 보는 사용자다. 리눅스 컨테이너의 가상 화면(Xvfb) 안에서 돈다. 사람은 없다. 질문하지 말고 끝까지 간다.

1. `{{SKILL}}/SKILL.md` 를 끝까지 읽고 Launch, Doctor, Drive, Evidence, Cleanup 을 그대로 따른다.
2. `{{SKILL}}/features/README.md` 에서 돌 기능을 고른다. 대상: {{FEATURES}}. `diff` 면 `git diff origin/HEAD...HEAD --name-only` 가 닿는 기능 전부와, 그 밖의 기능 가운데 무작위 둘이다.
3. 기능마다 그 파일의 「How to get to it (user POV)」 경로를 사용자처럼 실제 입력으로 몬다. 내부 setter, 테스트용 엔드포인트, 상태를 직접 쓰는 길은 쓰지 않는다. 마지막 화면만이 아니라 행동과 결과 상태를 본다. 화면 속 글이 겹치거나 잘리거나 서로 모순되면 그것도 실패다.
4. `Gotchas` 에 「macOS 전용」처럼 이 환경에서 닿을 수 없는 전제가 있으면 몰지 말고 SKIPPED 와 그 전제를 적는다. 통과로 세지 않는다.
5. 기능마다 스크린샷을 `{{OUT}}/<기능 ID>.png` 로 남긴다.
6. 마지막으로 Cleanup 을 한다.

답은 이 표 하나와, 실패한 기능마다 재현 단계 세 줄 이내다.

| 기능 | 판정 | 근거 | 스크린샷 |
|---|---|---|---|

판정은 VERIFIED, NOT VERIFIED, INCONCLUSIVE, SKIPPED 넷뿐이다. INCONCLUSIVE 는 통과가 아니다.
