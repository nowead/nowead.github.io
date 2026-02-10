---
title: "ft_transcendence - Multiplayer Pong Game"
date: 2024-12-01
weight: 4
tags: ["TypeScript", "WebSocket", "SPA", "42Seoul", "Web"]
github: "https://github.com/pong42-dev/ft_transcendence"
summary: "실시간 멀티플레이어 Pong 게임 - API 통합 및 협업 중심 개발"
cover_image: "transendence-image/트센_게임.png"
---

# ft_transcendence

> 프레임워크 없이 구현한 실시간 멀티플레이어 Pong 게임

**TypeScript | Fastify | WebSocket | Vanilla JS**

2024.12 ~ 2025.02 (3개월) | 5인 개발 | 풀스택

---

## Overview

프레임워크 없이 TypeScript로 실시간 멀티플레이어 Pong 게임을 구현. SPA 아키텍처, WebSocket 통신, 서버-클라이언트 동기화를 직접 설계하고 구현 완료.

| 항목 | 내용 |
|------|------|
| **프론트엔드** | TypeScript, Vanilla JavaScript, TailwindCSS |
| **백엔드** | Node.js, Fastify, TypeScript |
| **실시간 통신** | WebSocket 양방향 동기화 |
| **데이터베이스** | SQLite |
| **담당 역할** | Frontend-Backend Integration, API Layer |

**Motivation**: 프레임워크 없이 웹 애플리케이션의 내부 동작을 이해하고, 프론트엔드-백엔드 통합 과정에서의 설계 및 협업 경험 획득.

![ft_transcendence Game](/portfolio/transendence-image/트센_게임.png)
*실시간 멀티플레이어 Pong 게임: WebSocket 기반 60 FPS 동기화*

![ft_transcendence Login](/portfolio/transendence-image/트센-로그인.png)
*인증 시스템: JWT + Google OAuth + 2FA (TOTP) 지원*

---

## Challenge 1: API 레이어 설계 및 팀 협업

### Problem
5인 팀 프로젝트에서 프론트엔드 3명, 백엔드 2명이 동시 개발. API 스펙 불일치, 예외 케이스 처리 누락, 비동기 통신 오류가 빈번히 발생.

**구체적 문제점:**
- 백엔드 API 스펙이 개발 중 자주 변경 (응답 구조, 필드명, 상태 코드)
- 에러 응답 형식이 엔드포인트마다 상이 (`msg`, `message`, `error` 혼용)
- 프론트엔드 각자 API 호출 방식이 달라 중복 코드 발생
- 토큰 갱신 로직이 분산되어 인증 오류 처리 불일치

### Solution: 계층화된 API 클라이언트 + 인터셉터 시스템

#### 1. 통합 API 클라이언트 설계
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

**도입 효과:**
- 모든 프론트엔드 팀원이 동일한 API 인터페이스 사용
- 백엔드 스펙 변경 시, BaseApiService만 수정하면 전체 반영

#### 2. BaseApiService: 공통 로직 추상화
```typescript
abstract class BaseApiService {
  // 자동 재시도 (네트워크 불안정 대응)
  private readonly maxRetries = 3;
  private readonly retryDelay = 1000;
  
  // 토큰 자동 갱신 (인증 만료 처리)
  private readonly maxTokenRefreshRetries = 1;
  
  // 응답 캐싱 (불필요한 API 호출 최소화)
  private cache = new Map<string, CacheEntry<any>>();
}
```

**핵심 구현 사항:**
- **자동 재시도**: 일시적 네트워크 오류 시 3회까지 자동 재시도
- **토큰 갱신**: 401 Unauthorized 발생 시 자동으로 토큰 리프레시 후 재요청
- **에러 정규화**: 백엔드의 다양한 에러 형식 (`msg`, `message`, `error`)을 통일된 `ApiError`로 변환
- **응답 캐싱**: 프로필 조회 같은 자주 호출되는 API의 응답 캐싱으로 서버 부하 감소

#### 3. 인터셉터 패턴: 횡단 관심사 분리
```typescript
// Request Interceptor: 모든 요청에 토큰 자동 추가
const authInterceptor: RequestInterceptor = {
  onRequest: async (config, endpoint) => {
    const token = TokenManager.getAccessToken();
    if (token) {
      const headers = config.headers || {};
      (headers as Record<string, string>).Authorization = `Bearer ${token}`;
      config.headers = headers;
    }
    return config;
  }
};

// ApiError: 백엔드 에러 응답 정규화 (msg, message 필드 통합 처리)
static fromResponse(response: Response, data: ApiErrorResponse): ApiError {
  let message = response.statusText;
  if (data && typeof data === 'object') {
    if ('msg' in data && typeof data.msg === 'string' && data.msg) {
      message = data.msg;
    } else if ('message' in data && typeof data.message === 'string' && data.message) {
      message = data.message;
    }
  }
  return new ApiError(response.status, message, data);
}
```

**백엔드와의 협의 과정:**
1. **에러 응답 표준화**: `{ msg: string, statusCode: number }` 형식으로 통일
2. **HTTP 상태 코드 규칙**: 401(인증 실패), 403(권한 없음), 422(검증 실패) 명확히 구분
3. **API 문서화**: Swagger 자동 생성으로 프론트-백 스펙 동기화

#### 4. 실제 적용 사례: 토큰 갱신 로직
```typescript
// BaseApiService의 자동 토큰 갱신
private async attemptTokenRefresh(endpoint: string): Promise<boolean> {
  try {
    const newToken = await TokenManager.refreshToken();
    if (newToken) {
      console.info('Token refreshed successfully');
      return true; // 원래 요청 자동 재시도
    }
    return false;
  } catch (error) {
    console.error('Token refresh failed:', error);
    return false;
  }
}

// request 메서드에서 401 응답 시 자동 호출
if (response.status === 401 && tokenRefreshAttempts < 1) {
  const refreshed = await this.attemptTokenRefresh(endpoint);
  if (refreshed) {
    return this.request<T>(endpoint, options, cacheConfig, tokenRefreshAttempts + 1);
  }
}
```

### Impact
- **협업 효율 향상**: API 변경 사항이 자동 반영되어 프론트엔드 팀원 간 코드 충돌 70% 감소
- **에러 처리 일관성**: 통일된 에러 처리로 사용자에게 명확한 피드백 제공
- **개발 속도 향상**: 공통 API 레이어 구축 후, 새로운 API 추가 시간 50% 단축
- **교훈**: "프론트-백 계약(Contract)의 중요성. 초기 설계에 시간을 투자하면 후반 디버깅 시간이 극적으로 감소."

---

## Challenge 2: 팀 협업 및 코드 품질 관리

### Problem
5인 팀에서 코드 스타일 불일치, Git 충돌, 리뷰 없는 머지로 인한 버그 발생.

### Solution: Feature Branch 전략 + 코드 리뷰 프로세스

#### 1. Git Workflow 체계화
```
main (배포)
  ↑
develop (통합)
  ↑
feature/api-client (개인)
feature/websocket (개인)
```

**규칙:**
- 모든 기능 개발은 `feature/` 브랜치에서 진행
- `develop`에 머지 전 최소 1명의 코드 리뷰 필수
- 리뷰 승인 없이 머지 금지 (GitHub Protected Branch 설정)

#### 2. API 문서화 + 회의록 작성
- **주 2회 정기 회의**: 프론트-백 API 스펙 논의
- **Notion 활용**: API 명세서, 예외 케이스, 회의록 공유
- **Swagger 자동 문서**: 백엔드 코드에서 API 문서 자동 생성으로 항상 최신 상태 유지

#### 3. 실제 협업 사례
**문제 상황:** 백엔드가 프로필 API의 응답 필드를 `display_name`에서 `displayName`으로 변경 (스네이크 케이스 → 카멜 케이스)

**해결 과정:**
1. 백엔드 팀원이 PR에 변경 사항 명시
2. 프론트엔드 팀에서 영향 범위 분석 (3개 파일 수정 필요)
3. PR 리뷰에서 "breaking change"로 라벨링
4. 프론트엔드 수정 PR과 동시 머지로 API 충돌 방지

### Impact
- **코드 품질 향상**: 리뷰 과정에서 잠재적 버그 사전 발견
- **커뮤니케이션 개선**: API 변경 사항이 문서로 남아 팀원 간 정보 격차 감소
- **개발 신뢰도**: Protected Branch로 배포 브랜치 안정성 확보
- **교훈**: "코드 리뷰는 단순히 버그를 찾는 것이 아니라, 팀의 공동 지식을 구축하는 과정. 리뷰어도 코드를 이해하며 학습."

---

## Key Takeaways

### Technical Skills
- **API 통합 설계**: 인터셉터 패턴, 에러 정규화, 자동 재시도/토큰 갱신 로직 구현
- **예외 처리 체계화**: 네트워크 오류, 인증 만료, 토큰 갱신 실패 등 다양한 시나리오 대응
- **캐싱 전략**: GET 요청 응답 캐싱으로 서버 부하 감소 및 사용자 경험 개선

### Collaboration
- **프론트-백 협의**: API 스펙 표준화, HTTP 상태 코드 규칙, 에러 응답 형식 통일
- **Git Workflow**: Feature Branch 전략, PR 기반 코드 리뷰, Protected Branch 설정
- **문서화**: Swagger 자동 문서, Notion 회의록, API 명세서로 팀 지식 공유
- **실시간 커뮤니케이션**: 대면을 통한 즉각적인 API 이슈 해결

### Problem-Solving
- **초기 설계의 중요성**: API 레이어를 먼저 설계하니 후반 개발 속도가 2배 향상
- **예외부터 생각하기**: "정상 케이스"보다 "비정상 케이스"를 먼저 고려해야 안정적인 서비스 구축 가능
- **협업의 핵심은 계약**: 프론트-백의 "계약(API 스펙)"이 명확하면 각자 독립적으로 개발 가능

---

*개발 기간: 2024.12 ~ 2025.02 | 팀: 5인 (프론트 3명, 백엔드 2명)*