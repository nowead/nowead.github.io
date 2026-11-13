---
title: "ft_transcendence"
date: 2024-12-01
weight: 5
stage: "foundation"
track: "TRACK 02 · WEB SERVICE"
category_label: "Multiplayer web game"
status: "42 Seoul 팀 프로젝트"
period: "2024.12 — 2025.02"
role: "API 레이어 · 프런트엔드–백엔드 통합"
tags: ["TypeScript", "Fastify", "WebSocket", "OAuth", "SPA"]
github: "https://github.com/pong42-dev/ft_transcendence"
summary: "실시간 멀티플레이어 Pong 게임을 5인 팀으로 만들었습니다. 프런트엔드와 백엔드 사이의 API 계약을 정리하고 공통 API 레이어를 설계했습니다."
cover_image: "transcendence-image/pong-cover.png"
cover_width: 905
cover_height: 566
image_alt: "ft_transcendence의 실시간 Pong 게임 화면"
image_caption: "WebSocket으로 동기화되는 실시간 Pong 게임 화면."
leads_to: "onegoal"
handoff:
  - "OAuth 로그인과 2단계 인증 구현 → 소셜 로그인과 운영자 TOTP 인증"
  - "프레임워크 없는 SPA 프런트엔드 → 빌드 단계 없는 JavaScript 모듈 화면"
  - "API 계약을 먼저 맞추는 협업 → 명세와 테스트를 먼저 쓰는 개발 방식"
brief:
  problem:
    title: "다섯 명이 서로 다른 API를 기대했다"
    text: "응답 구조와 필드명이 개발 중에 자주 바뀌고, 에러 형식이 엔드포인트마다 달랐습니다. 화면마다 호출 방식과 토큰 갱신 처리가 제각각이었습니다."
  solution:
    title: "단일 API 레이어와 합의된 계약"
    text: "모든 호출이 지나는 공통 API 클라이언트를 만들고, 에러 형식과 상태 코드 규칙을 백엔드와 합의해 문서로 고정했습니다."
  verification:
    title: "리뷰 없이는 합치지 않는다"
    text: "보호 브랜치와 필수 리뷰로 변경을 확인하고, 호환되지 않는 API 변경은 프런트엔드 수정과 동시에 병합했습니다."
---

## 프로젝트

TypeScript 기반 SPA와 WebSocket 통신으로 실시간 멀티플레이어 Pong 게임을 만든 42 Seoul의 팀 프로젝트입니다. 프런트엔드 3명, 백엔드 2명으로 구성된 팀에서 **API 레이어와 프런트엔드–백엔드 통합**을 맡았습니다.

| 항목 | 내용 |
| --- | --- |
| 프런트엔드 | TypeScript, Vanilla JavaScript, TailwindCSS |
| 백엔드 | Node.js, Fastify, SQLite |
| 실시간 통신 | WebSocket 양방향 동기화 |
| 인증 | JWT, Google OAuth, 2단계 인증(TOTP) |

{{< shot src="transcendence-image/pong-game.png" alt="ft_transcendence의 터미널 스타일 Pong 게임 화면. 점수는 2 대 1이다" caption="실시간으로 동기화되는 Pong 게임 화면." width="905" height="1107" class="narrow" >}}

## 문제 정의: 버그가 아니라 계약의 문제

통합 단계에서 오류가 반복됐습니다. 하나씩 고치는 대신, 오류가 어디서 오는지를 먼저 분류했습니다.

- 백엔드 API의 응답 구조, 필드명, 상태 코드가 **개발 중에 자주 바뀌었습니다.**
- 에러 응답이 엔드포인트마다 `msg`, `message`, `error`로 **제각각이었습니다.**
- 프런트엔드 팀원마다 호출 방식이 달라 **같은 코드가 반복됐습니다.**
- 토큰 갱신 로직이 흩어져 있어 **인증 오류 처리가 화면마다 달랐습니다.**

개별 버그가 아니라, 프런트엔드와 백엔드 사이에 합의된 계약이 없다는 것이 문제였습니다.

## 해결

### 모든 호출이 지나는 단일 진입점

화면에서 `fetch`를 직접 부르지 않고, 공통 API 클라이언트만 사용하도록 했습니다.

```typescript
// ApiClient: 단일 진입점
export class ApiClient {
  public auth: AuthApiService;
  public game: GameApiService;
  public friend: FriendApiService;
  public user: UserApiService;
  public tournament: TournamentApiService;
}
```

공통 규칙은 `BaseApiService` 한 곳에 모았습니다.

| 공통 처리 | 내용 |
| --- | --- |
| 자동 재시도 | 일시적인 네트워크 오류는 3회까지 다시 시도 |
| 토큰 갱신 | 401 응답이면 토큰을 갱신한 뒤 원래 요청을 한 번 재시도 |
| 에러 정규화 | 서로 다른 에러 형식을 하나의 `ApiError`로 변환 |
| 응답 캐싱 | 자주 조회하는 GET 응답을 캐싱 |

```typescript
// request 메서드에서 401 응답 시 자동 호출
if (response.status === 401 && tokenRefreshAttempts < 1) {
  const refreshed = await this.attemptTokenRefresh(endpoint);
  if (refreshed) {
    return this.request<T>(endpoint, options, cacheConfig, tokenRefreshAttempts + 1);
  }
}
```

### 계약을 문서로 고정

코드만으로는 계약이 유지되지 않습니다. 백엔드와 다음을 합의했습니다.

1. **에러 응답 형식** — `{ msg: string, statusCode: number }`로 통일
2. **상태 코드 규칙** — 401(인증 실패), 403(권한 없음), 422(검증 실패)를 구분
3. **API 문서** — 백엔드 코드에서 Swagger 문서를 자동 생성해 항상 최신 상태 유지

주 2회 정기 회의에서 API 명세를 논의하고, 결정한 내용은 회의록으로 남겼습니다.

## 검증: 변경을 확인하는 절차

```text
main (배포)
  ↑
develop (통합)
  ↑
feature/* (개인 작업)
```

- 모든 기능은 `feature/` 브랜치에서 개발합니다.
- `develop`에 합치려면 1명 이상의 리뷰 승인이 필요합니다. 보호 브랜치로 강제했습니다.

이 절차가 실제로 동작한 사례가 있습니다. 백엔드가 프로필 응답 필드를 `display_name`에서 `displayName`으로 바꿨을 때, PR에 호환되지 않는 변경임을 표시하고 프런트엔드의 영향 범위(파일 3개)를 먼저 확인했습니다. 프런트엔드 수정 PR과 동시에 병합해 통합 브랜치가 깨지는 구간을 만들지 않았습니다.

## onegoal로 이어진 것

[onegoal](/fde/onegoal/)은 혼자 만든 서비스이지만, 이 프로젝트에서 배운 방식이 그대로 이어졌습니다.

- **인증** — OAuth 로그인과 TOTP 2단계 인증을 직접 구현해 본 경험이, 소셜 로그인과 운영자 2단계 인증을 구성하는 기준이 됐습니다.
- **프런트엔드** — 프레임워크 없이 SPA를 만든 경험으로, 빌드 단계 없는 JavaScript 모듈만으로 화면을 구성했습니다.
- **계약 먼저** — API 계약을 먼저 맞추던 방식은, 요구사항과 수용 테스트를 코드보다 먼저 쓰는 방식으로 확장됐습니다.
- **통합 브랜치와 검토** — `develop` 통합 브랜치와 병합 전 검토 절차를 같은 형태로 사용합니다.

*팀: 5인 (프런트엔드 3명, 백엔드 2명)*
