---
title: "ft_transcendence - Real-time Multiplayer Pong"
date: 2025-04-01
weight: 4
tags: ["TypeScript", "Fastify", "WebSocket", "SPA", "42Seoul", "OAuth", "i18n"]
github: "https://github.com/nowead/ft_transcendence"
summary: "실시간 멀티플레이어 Pong 게임 - TypeScript/Fastify 풀스택 웹 애플리케이션"
cover_image: "transendence-image/트센_게임.png"
---

# ft_transcendence

> 프레임워크 없는 TypeScript SPA — WebSocket 게임, OAuth, 팀 협업

**TypeScript | Fastify | WebSocket | OAuth | i18n | Docker**

2025.04 ~ 2025.07 (3개월) | 4인 개발 | Full-stack

---

## Overview

실시간 멀티플레이어 Pong 게임과 토너먼트 시스템을 제공하는 풀스택 웹 애플리케이션.

| 항목 | 내용 |
|------|------|
| **Frontend** | TypeScript (Vanilla, no framework), Tailwind CSS |
| **Backend** | Fastify, SQLite, JWT, Google OAuth |
| **실시간 통신** | WebSocket (60 FPS 게임 상태 동기화) |
| **기능** | 멀티플레이어 게임, 토너먼트, 2FA, i18n (3개 언어) |

**Motivation**: 프레임워크 없이 SPA 라우팅, 상태 관리를 직접 구현하며 웹 생태계 이해. 4인 팀 협업 경험.

---

## Challenge 1: 프레임워크 없는 SPA 라우팅

### Problem
React/Vue 없이 Vanilla TypeScript로 SPA (Single Page Application) 구현. 클라이언트 사이드 라우팅과 상태 관리 필요.

### 라우터 구현
```typescript
class Router {
    private routes: Map<string, () => void> = new Map();
    private currentPath: string = '/';
    
    constructor() {
        // 브라우저 뒤로가기/앞으로가기 처리
        window.addEventListener('popstate', () => {
            this.loadRoute(window.location.pathname);
        });
    }
    
    register(path: string, handler: () => void): void {
        this.routes.set(path, handler);
    }
    
    navigate(path: string): void {
        // 히스토리 API로 URL 변경 (페이지 새로고침 없음)
        window.history.pushState({}, '', path);
        this.loadRoute(path);
    }
    
    private loadRoute(path: string): void {
        const handler = this.routes.get(path);
        if (handler) {
            this.currentPath = path;
            // 기존 페이지 제거
            document.querySelector('#app')!.innerHTML = '';
            // 새 페이지 렌더링
            handler();
        } else {
            this.navigate('/404');
        }
    }
}

// 사용 예시
const router = new Router();
router.register('/', () => new HomePage().render());
router.register('/game', () => new GamePage().render());
router.register('/profile', () => new ProfilePage().render());
```

### 상태 관리 (Redux-like)
```typescript
interface AuthState {
    isAuthenticated: boolean;
    user: User | null;
}

class AuthStore {
    private state: AuthState = {
        isAuthenticated: false,
        user: null
    };
    
    private listeners: Set<(state: AuthState) => void> = new Set();
    
    getState(): AuthState {
        return { ...this.state };  // 불변성 유지
    }
    
    setState(newState: Partial<AuthState>): void {
        this.state = { ...this.state, ...newState };
        this.notifyListeners();
    }
    
    subscribe(listener: (state: AuthState) => void): () => void {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);  // unsubscribe
    }
    
    private notifyListeners(): void {
        this.listeners.forEach(listener => listener(this.state));
    }
}

// 사용 예시
const authStore = new AuthStore();

// 컴포넌트에서 구독
authStore.subscribe((state) => {
    if (state.isAuthenticated) {
        showUserProfile(state.user);
    } else {
        showLoginButton();
    }
});
```

### Component 패턴
```typescript
abstract class Component {
    protected container: HTMLElement;
    
    constructor(parentSelector: string) {
        this.container = document.querySelector(parentSelector)!;
    }
    
    abstract render(): void;
    
    protected createElement(html: string): HTMLElement {
        const template = document.createElement('template');
        template.innerHTML = html.trim();
        return template.content.firstChild as HTMLElement;
    }
}

class GamePage extends Component {
    render(): void {
        const html = `
            <div class="game-container">
                <canvas id="game-canvas" width="800" height="600"></canvas>
                <div id="score">0 - 0</div>
            </div>
        `;
        const element = this.createElement(html);
        this.container.appendChild(element);
        
        // Canvas 게임 로직 초기화
        this.initGame();
    }
    
    private initGame(): void {
        const canvas = document.querySelector('#game-canvas') as HTMLCanvasElement;
        const gameClient = new GameClient(canvas);
        gameClient.connect();
    }
}
```

### Impact
- React 없이 SPA 구현 완료 (라우팅, 상태 관리, 컴포넌트 패턴)
- 프레임워크의 내부 동작 원리 이해 (History API, 반응형 상태)
- **교훈**: 프레임워크는 문제 해결 패턴의 집합. 직접 구현하며 "왜 React가 필요한가"를 이해.

---

## Challenge 2: WebSocket 게임 동기화

### Problem
Pong 게임은 60 FPS로 실시간 동기화 필요. 네트워크 지연 (latency)과 클라이언트-서버 상태 불일치 문제.

### 서버 측: 권위 있는 게임 로직
```typescript
// Backend: wss/game/GameEngine.ts
class GameEngine {
    private ball: Ball;
    private paddles: Map<string, Paddle> = new Map();
    private TICK_RATE = 60;  // 60 FPS
    
    start(): void {
        setInterval(() => this.update(), 1000 / this.TICK_RATE);
    }
    
    private update(): void {
        // 1. 공 이동
        this.ball.x += this.ball.velocityX;
        this.ball.y += this.ball.velocityY;
        
        // 2. 벽 충돌
        if (this.ball.y <= 0 || this.ball.y >= 600) {
            this.ball.velocityY *= -1;
        }
        
        // 3. 패들 충돌
        for (const paddle of this.paddles.values()) {
            if (this.checkCollision(this.ball, paddle)) {
                this.ball.velocityX *= -1.1;  // 속도 증가
            }
        }
        
        // 4. 득점 체크
        if (this.ball.x <= 0) {
            this.scores.player2++;
            this.resetBall();
        }
        
        // 5. 모든 클라이언트에 상태 전송
        this.broadcastState();
    }
    
    updatePlayerInput(playerId: string, input: PlayerInput): void {
        const paddle = this.paddles.get(playerId);
        if (!paddle) return;
        
        // 입력에 따라 패들 이동 (서버가 검증)
        if (input.direction === 'up') {
            paddle.y = Math.max(0, paddle.y - 10);
        } else if (input.direction === 'down') {
            paddle.y = Math.min(600 - paddle.height, paddle.y + 10);
        }
    }
    
    private broadcastState(): void {
        const state: GameStateDto = {
            ball: this.ball,
            paddles: Array.from(this.paddles.values()),
            scores: this.scores,
            timestamp: Date.now()
        };
        
        // WebSocket으로 모든 플레이어에게 전송
        this.players.forEach(player => {
            player.socket.send(JSON.stringify({
                type: 'game_state',
                data: state
            }));
        });
    }
}
```

### 클라이언트 측: 예측 & 보간
```typescript
// Frontend: services/GameClient.ts
class GameClient {
    private canvas: HTMLCanvasElement;
    private ctx: CanvasRenderingContext2D;
    private ws: WebSocketService;
    private lastServerState: GameStateDto | null = null;
    
    connect(): void {
        this.ws.connect('/game');
        
        this.ws.on<GameStateDto>('game_state', (state) => {
            this.lastServerState = state;
        });
        
        // 키보드 입력 → 서버 전송
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowUp') {
                this.ws.emit('player_input', { direction: 'up' });
            } else if (e.key === 'ArrowDown') {
                this.ws.emit('player_input', { direction: 'down' });
            }
        });
        
        // 렌더링 루프 (60 FPS)
        requestAnimationFrame(() => this.render());
    }
    
    private render(): void {
        if (this.lastServerState) {
            // 서버 상태 그대로 렌더링 (권위 있는 상태)
            this.drawBall(this.lastServerState.ball);
            this.lastServerState.paddles.forEach(p => this.drawPaddle(p));
        }
        
        requestAnimationFrame(() => this.render());
    }
}
```

### 네트워크 지연 처리
**문제**: 100ms 지연 시 공의 위치가 과거 위치로 표시.

**해결**: 클라이언트 예측 (Client-side Prediction)
```typescript
// 로컬 패들은 즉시 이동, 서버는 검증만
private predictLocalPaddle(input: PlayerInput): void {
    // 즉시 로컬 렌더링
    this.localPaddle.y += input.direction === 'up' ? -10 : 10;
    
    // 서버에 입력 전송 (timestamp 포함)
    this.ws.emit('player_input', {
        direction: input.direction,
        timestamp: Date.now()
    });
}

// 서버 상태 도착 시 보정
private reconcileWithServer(serverState: GameStateDto): void {
    // 서버 패들 위치와 로컬 예측 차이 계산
    const diff = serverState.myPaddle.y - this.localPaddle.y;
    
    if (Math.abs(diff) > 5) {
        // 차이가 크면 서버 상태로 스냅
        this.localPaddle.y = serverState.myPaddle.y;
    } else {
        // 작은 오차는 보간 (부드러운 보정)
        this.localPaddle.y += diff * 0.3;
    }
}
```

### Impact
- 60 FPS WebSocket 실시간 게임 동기화 성공
- 네트워크 지연에도 부드러운 게임플레이 (예측 + 보간)
- **교훈**: 멀티플레이어 게임은 "서버 권위 + 클라이언트 예측"이 핵심. 동기화는 타협의 연속.

---

## Challenge 3: 팀 협업 & 프로젝트 관리

### Problem
4인 팀에서 Frontend/Backend/DB 동시 개발. 브랜치 전략, API 계약, 코드 리뷰 필요.

### Git Workflow
```bash
# Feature branch 전략
main (protected)
  ├── develop
  │   ├── feature/auth
  │   ├── feature/game
  │   └── feature/tournament

# Pull request 규칙
1. develop에서 feature 브랜치 생성
2. 작업 완료 후 PR 생성
3. 최소 1명 리뷰 후 merge
4. develop → main은 릴리스 시에만
```

### API 계약 (OpenAPI-like)
```typescript
// contracts/api-spec.ts
// Frontend와 Backend가 공유하는 타입 정의
export interface LoginRequest {
    username: string;
    password: string;
}

export interface LoginResponse {
    success: boolean;
    accessToken?: string;
    twoFAEnabled?: boolean;
    sessionToken?: string;
}

// Frontend에서 사용
const response = await apiClient.post<LoginResponse>(
    '/api/auth/login',
    loginRequest
);

// Backend에서 사용
app.post<{Body: LoginRequest, Reply: LoginResponse}>(
    '/api/auth/login',
    async (request, reply) => {
        // 타입 자동 완성
        const { username, password } = request.body;
        // ...
    }
);
```

### 코드 리뷰 문화
**규칙**:
1. 한 PR에 500줄 이하 (리뷰 가능한 크기)
2. 커밋 메시지: `[Feature/Fix/Refactor] 내용`
3. 리뷰 의견은 질문 형태로 (`왜 이렇게 했나요?`)

**실제 리뷰 예시**:
```
Reviewer: "GameEngine.update()가 200줄이라 복잡해 보입니다. 
          updateBall(), checkCollisions() 등으로 분리하면 어떨까요?"

Author: "동의합니다. 리팩터링하겠습니다."

→ 코드 품질 향상, 상호 학습 효과
```

### 이슈 관리 (GitHub Projects)
```
📋 Backlog
  ├── [고] 토너먼트 대진표 버그 수정
  ├── [중] 친구 온라인 상태 실시간 업데이트
  └── [저] 프로필 사진 크기 조정

🔥 In Progress (최대 3개)
  ├── [@damin] WebSocket 재연결 로직
  └── [@seonseo] OAuth 에러 처리

✅ Done (Sprint 종료 시 정리)
  ├── 2FA 구현 완료
  └── i18n 3개 언어 지원
```

### 역할 분담
| 팀원 | 담당 | 기여 |
|------|------|------|
| **A** | Backend API, DB 설계 | Fastify 라우팅, SQLite 스키마 |
| **B** | WebSocket 게임 로직 | GameEngine, 충돌 검사 |
| **C** | Frontend 인증, 라우팅 | OAuth, JWT, SPA Router |
| **D (나)** | Frontend 게임 UI, i18n | Canvas 렌더링, 다국어 |

### Impact
- 4인 팀이 3개월간 풀스택 프로젝트 완주
- 브랜치 전략, PR 리뷰, API 계약으로 충돌 최소화
- **교훈**: 좋은 협업은 "명확한 역할 + 겹치는 관심사 (코드 리뷰)". 커뮤니케이션이 기술보다 중요.

---

## 주요 기능

- **실시간 게임**: WebSocket 기반 60 FPS Pong, 로컬/온라인 모드
- **토너먼트**: Single Elimination 방식, 자동 대진표 생성
- **인증**: JWT, Google OAuth, 2FA (TOTP)
- **친구**: 친구 요청, 온라인 상태, 게임 초대
- **다국어**: i18next (한국어, 영어, 일본어)
- **터미널 UI**: CLI 스타일 인터페이스, 명령어 자동완성

---

## Key Takeaways

### Web Ecosystem
- **프레임워크의 가치**: 라우팅, 상태 관리를 직접 구현하며 React/Vue의 존재 이유 이해
- **웹소켓 실전**: 단방향 (HTTP) vs 양방향 (WebSocket) 통신의 차이
- **OAuth 플로우**: Authorization Code Flow, 토큰 관리, 보안 고려사항

### Collaboration
- **브랜치 전략**: Feature branch + PR 리뷰로 충돌 관리
- **API 계약**: TypeScript 타입 공유로 프론트-백엔드 연동 오류 감소
- **코드 리뷰 문화**: 비판이 아닌 학습의 도구

### TypeScript
- **타입 안전성**: 컴파일 타임에 오류 발견 (API 응답 타입 불일치 등)
- **추상화 설계**: Interface, Abstract Class로 확장 가능한 구조
- **모듈 시스템**: ESM import/export, 의존성 주입 패턴

---

*개발 기간: 2025.04 ~ 2025.07 | 팀: 4인 | 풀스택 웹 개발*