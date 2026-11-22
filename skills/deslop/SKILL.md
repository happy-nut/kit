---
name: deslop
description: "브랜치가 들여온 AI 가 만든 군더더기 코드(쓸데없는 주석, 믿는 경로의 방어 코드, any 캐스트, 깊은 중첩)를 걷어 내고 코드 모양을 주변에 맞춘다. 「군더더기 걷어내」, 「AI 티 나는 코드 지워」, 「이 diff 정리해」에 쓴다. /dev:deslop"
disable-model-invocation: true
---

# AI 군더더기 코드 걷어 내기

기본 브랜치(대개 `main`)와의 diff 를 보고, 이 브랜치가 들여온 AI 가 만든 군더더기를 지운다. diff 는 `git diff $(git merge-base HEAD main)` 로 본다. 이 브랜치의 커밋과 커밋하지 않은 변경이 함께 나온다. 기본 브랜치 이름이 다르면 `git symbolic-ref refs/remotes/origin/HEAD` 로 찾는다.

## 볼 것

- 필요 없거나 그 파일의 주석 습관과 맞지 않는 주석. 주석을 남길지 판단은 `/dev:no-comments` 를 따른다.
- 믿을 수 있는 코드 경로에 어울리지 않는 방어 검사나 try/catch.
- 타입 문제를 피하려고만 쓴 `any` 캐스트.
- 이른 반환(early return)으로 펴야 할 깊은 중첩.
- 그 밖에 그 파일과 주변 코드베이스와 어긋나는 패턴.

## 가드레일

- 분명한 버그를 고치는 경우가 아니면 동작을 바꾸지 않는다.
- 넓게 다시 쓰기보다 작고 겨냥한 편집을 고른다.
- 마지막 요약은 짧게, 1~3문장.
