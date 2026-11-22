---
name: ts
description: "TypeScript 를 읽거나 고칠 때의 규칙: 판별 유니온, 브랜드 타입, as 금지, 경계에서 스키마로 파싱, 완전성 검사. .ts·.tsx 파일을 읽거나 고칠 때, 「TypeScript 모범 사례」, TypeScript 타입을 리뷰할 때 쓴다. /dev:ts"
paths: ["**/*.ts", "**/*.tsx"]
disable-model-invocation: true
---

# TypeScript

「principles.md 의 Type System Discipline」(경로 `../mode/principles.md`)을 먼저 적용한다. 저장소의 `AGENTS.md`·`CLAUDE.md`·린트 설정이 이 표와 부딪치면 저장소가 앞선다.

| 규칙 | 요약 |
|------|------|
| 판별 유니온 | 변형은 `kind` 리터럴 판별자로 모델링해 불가능한 상태를 표현할 수 없게 한다. 선택 필드 묶음을 쓰지 않는다. |
| 브랜드 타입 | 원시값을 `& { readonly __brand: "X" }` 로 브랜드해 섞이지 않게 한다. 경계에서 한 번 검증한다. 브랜드는 `as` 가 아니라 검증하는 타입 가드(`input is AgentId`)에서만 나온다. |
| 구성으로 모델링 | 잘못된 값을 아예 만들 수 없게 모양을 짓는다. 비어 있지 않음은 `[T, ...T[]]`, 짝수 길이는 `[T, T][]`, 범위는 `start` 와 `duration`. 런타임 가드도, 정제 타입에 대한 바람도 아니다. |
| 가장 단순한 total 타입 | 모든 연산이 total 인 동안은 `T[]` 를 둔다. 느슨한 타입이 `!`, 캐스트, 「절대 안 일어남」 throw 를 강요하는 자리에서만 `NonEmpty<T>` 로 강화한다. |
| `any` 대신 `unknown` | 바깥 데이터는 `unknown` 이다. |
| 가드보다 스키마 먼저 | 속성 하나하나 확인하는 타입 가드를 손으로 쓰기 전에 저장소의 런타임 스키마 라이브러리를 쓰고 타입을 스키마에서 추론한다(`z.infer` 등). |
| `as` 캐스트 금지 | 모든 `as` 는 기다리는 런타임 오류다. 검증 뒤에만 캐스트한다. |
| 좁히기 순서 | 판별자 switch > `in` 연산자 > `typeof`·`instanceof` > 사용자 정의 타입 가드 > `as`. |
| 타입 가드 | 주장을 실제로 검증해야 한다. 거짓말하는 가드는 `as` 보다 나쁘다. 안전하다는 이름 뒤에 버그가 숨는다. 이름은 `isX` 나 `hasX`. |
| 완전성 | default 갈래에 `const _exhaustive: never = x;` 를 넣어 새 변형이 생기면 컴파일러가 오류를 낸다. |
| `as` 대신 `satisfies` | 리터럴 타입을 넓히지 않고 값을 검증한다. |
| 경계 검증 | 데이터가 들어오는 곳에서 이름 붙은 도메인 타입으로 파싱한다. `Record<string, unknown>`(어떻게 쓰든)은 그 파싱에서 멈춘다. 안쪽에서는 타입을 믿는다. 「principles.md 의 Boundary Discipline」을 본다. |
| 스키마에서 나온 타입 | 새 인터페이스를 선언하기 전에 `Pick`·`Omit`·`Parameters`·`ReturnType`·`Awaited`·`typeof` 를 먼저 쓴다. |
| 객체 인자 | 위치 인자가 아니라 객체를 넘겨 인자 순서가 스스로 설명되게 한다. 핫 패스(프레임마다 그리기, 토크나이저, 파서)는 예외. |
| 진짜 테스트 | 돌릴 수 있는 것은 mock 하지 않는다. 누수·disposable 검사가 있는 프레임워크의 진짜 테스트 도구를 쓰고, UI 는 돌아가는 빌드에서 확인한다. 로컬에서 돌릴 수 없는 것만 mock 한다. |
| 구조화 텔레메트리 | id 하나로 디버깅할 수 있을 만큼 맥락이 든 구조화 로거 진단을 쓴다. 출하 코드에 `console.log` 를 두지 않는다. |

예시: `references/patterns.md`.
