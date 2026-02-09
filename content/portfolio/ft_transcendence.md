---
title: "ft_transcendence - Real-time Multiplayer Pong"
date: 2025-04-01
weight: 4
tags: ["TypeScript", "Fastify", "WebSocket", "SPA", "42Seoul", "OAuth", "i18n"]
github: "https://github.com/nowead/ft_transcendence"
summary: "실시간 멀티플레이어 Pong 게임 - TypeScript/Fastify 풀스택 웹 애플리케이션"
cover_image: "transendence-image/트센.png"
---

## 프로젝트 개요

ft_transcendence는 42Seoul의 최종 웹 프로젝트로, 실시간 멀티플레이어 Pong 게임과 토너먼트 시스템을 제공하는 현대적인 풀스택 웹 애플리케이션입니다. 터미널 스타일 CLI 인터페이스와 최신 웹 기술을 결합하여 독특하고 매력적인 사용자 경험을 제공합니다.

## 핵심 기술 스택

### Frontend
- **언어:** TypeScript (Vanilla JS, 프레임워크 없음)
- **스타일링:** Tailwind CSS
- **렌더링:** HTML5 Canvas (게임)
- **실시간 통신:** WebSocket
- **국제화:** i18next (한국어, 영어, 일본어)

### Backend
- **런타임:** Node.js
- **프레임워크:** Fastify
- **데이터베이스:** SQLite
- **인증:** JWT, Google OAuth, 2FA (TOTP)

### DevOps
- **컨테이너화:** Docker, Docker Compose
- **빌드 도구:** TypeScript Compiler, PostCSS
- **웹 서버:** Nginx (프로덕션)

## 아키텍처

### Frontend - 계층형 아키텍처

```plaintext
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│   App.ts │ Terminal.ts │ GamePage.ts │ UserProfile.ts      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                      │
│ AuthManager │ UIRenderer │ ModalManager │ GameManager      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                           │
│ ApiClient │ WebSocketService │ i18n │ Router │ GameClient  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                             │
│             authStore │ userProfileStore                    │
└─────────────────────────────────────────────────────────────┘
```

### Backend - Fastify 플러그인 아키텍처

```plaintext
src/
├── app.ts                    # Fastify 앱 설정
├── server.ts                 # 서버 엔트리 포인트
├── plugins/
│   ├── app/
│   │   ├── auth/             # 인증 (JWT, OAuth, 2FA)
│   │   ├── users/            # 사용자 관리
│   │   └── utils/            # 유틸리티
│   └── external/             # 외부 통합 (Knex, JWT, QR)
├── routes/
│   └── api/
│       ├── users/            # 사용자 API
│       ├── games/            # 게임 API
│       ├── tournaments/      # 토너먼트 API
│       └── friends/          # 친구 API
└── wss/                      # WebSocket 서버
    ├── game/                 # 게임 WebSocket
    ├── chat/                 # 채팅 (미구현)
    └── notification/         # 알림 (미구현)
```

## 주요 기능

### 1. 사용자 인증 및 관리

#### 로컬 인증
```typescript
// AuthManager.ts
async login(username: string, password: string): Promise<void> {
  const response = await this.apiClient.auth.login({
    username,
    password
  });
  
  if (response.twoFAEnabled) {
    // 2FA 모달 표시
    this.show2FAModal(response.sessionToken);
  } else {
    // 인증 완료
    authStore.setState({
      isAuthenticated: true,
      user: response.user
    });
  }
}
```

#### Google OAuth
- Authorization Code Flow 구현
- `google-auth-library` 사용
- 자동 계정 생성 및 연동

#### **2FA**(Two-Factor Authentication)
```typescript
// TwoFAModal.ts
async verifyTwoFA(code: string): Promise<void> {
  const response = await this.apiClient.auth.verify2FA({
    sessionToken: this.sessionToken,
    code: code
  });
  
  if (response.success) {
    // 토큰 저장 및 로그인 완료
    TokenManager.setAccessToken(response.accessToken);
    TokenManager.setRefreshToken(response.refreshToken);
  }
}
```

### 2. 실시간 게임 시스템

#### GameClient - WebSocket 기반 게임 로직
```typescript
class GameClient {
  private ws: WebSocketService;
  private renderer: GameRenderer;
  private inputHandler: InputHandler;
  
  connect(): void {
    this.ws.connect('/game');
    
    // 게임 상태 업데이트 수신
    this.ws.on<GameStateDto>('game_state', (state) => {
      this.renderer.render(state);
    });
    
    // 게임 이벤트 수신 (점수, 종료 등)
    this.ws.on<GameEventDto>('game_event', (event) => {
      this.handleGameEvent(event);
    });
  }
  
  sendInput(input: PlayerInput): void {
    this.ws.emit('player_input', {
      direction: input.direction,
      timestamp: Date.now()
    });
  }
}
```

#### 서버 측 게임 로직 (Backend)
```typescript
// game WebSocket handler
gameEngine.on('stateUpdate', (state: GameState) => {
  // 모든 플레이어에게 상태 전송 (60 FPS)
  broadcastToPlayers({
    type: 'game_state',
    data: {
      ball: state.ball,
      paddles: state.paddles,
      scores: state.scores
    }
  });
});

// 플레이어 입력 처리
socket.on('player_input', (input: PlayerInputMessage) => {
  gameEngine.updatePlayerInput(player.id, input);
});
```

### 3. 토너먼트 시스템

#### 토너먼트 생성 및 관리
```typescript
interface TournamentConfig {
  name: string;
  maxPlayers: number;  // 4, 8, 16
  startTime?: Date;
}

// API: POST /api/tournaments
const tournament = await apiClient.tournament.create({
  name: "Summer Championship",
  maxPlayers: 8,
  startTime: new Date('2025-04-15T10:00:00Z')
});
```

#### 대진표 생성 (Single Elimination)
```typescript
class TournamentBracket {
  private rounds: Round[];
  
  generateBracket(players: Player[]): void {
    const numRounds = Math.log2(players.length);
    
    // Round 1
    for (let i = 0; i < players.length; i += 2) {
      this.rounds[0].matches.push({
        player1: players[i],
        player2: players[i + 1],
        winner: null
      });
    }
    
    // 이후 라운드는 승자가 결정되면 자동 생성
  }
  
  advanceWinner(matchId: string, winnerId: string): void {
    const match = this.findMatch(matchId);
    match.winner = winnerId;
    
    // 다음 라운드 매치 생성
    const nextMatch = this.getOrCreateNextMatch(match);
    nextMatch.player1 = winnerId;
  }
}
```

### 4. 친구 시스템

#### 친구 요청 및 관리
```typescript
// API: POST /api/friends/request
await apiClient.friend.sendRequest(userId);

// API: POST /api/friends/accept
await apiClient.friend.acceptRequest(friendshipId);

// API: GET /api/friends
const friends = await apiClient.friend.getFriends();

// 온라인 상태 실시간 업데이트 (WebSocket)
websocket.on('friend_status', (data: FriendStatusUpdate) => {
  userProfileStore.updateFriendStatus(data.userId, data.status);
});
```

### 5. 터미널 CLI 인터페이스

#### CommandHandler - 명령어 파싱 및 실행
```typescript
class CommandHandler {
  private commands: Map<string, Command>;
  
  constructor() {
    this.registerCommands();
  }
  
  private registerCommands(): void {
    this.commands.set('login', {
      execute: () => this.modalManager.showLogin(),
      description: 'Login to your account'
    });
    
    this.commands.set('game', {
      execute: (args) => this.startGame(args),
      description: 'Start a game: game [local|online|tournament]'
    });
    
    this.commands.set('lang', {
      execute: (args) => i18next.changeLanguage(args[0]),
      description: 'Change language: lang <ko|en|ja>'
    });
    
    this.commands.set('friends', {
      execute: () => this.showFriendsList(),
      description: 'Show friends list'
    });
  }
  
  async execute(input: string): Promise<string> {
    const [cmd, ...args] = input.trim().split(' ');
    const command = this.commands.get(cmd);
    
    if (!command) {
      return i18next.t('errors.commandNotFound');
    }
    
    try {
      return await command.execute(args);
    } catch (error) {
      return i18next.t('errors.commandFailed');
    }
  }
}
```

### 6. 다국어 지원 (i18n)

#### i18next 설정
```typescript
// src/services/i18n.ts
import i18next from 'i18next';
import HttpBackend from 'i18next-http-backend';

export async function initI18n(): Promise<void> {
  await i18next
    .use(HttpBackend)
    .init({
      lng: localStorage.getItem('language') || 'ko',
      fallbackLng: 'en',
      backend: {
        loadPath: '/locales/{{lng}}/translation.json'
      }
    });
}

// 사용 예시
terminal.writeLine(i18next.t('welcome.message'));
```

#### 번역 파일 구조
```plaintext
public/locales/
├── ko/
│   └── translation.json
├── en/
│   └── translation.json
└── ja/
    └── translation.json
```

### 7. 상태 관리 (Redux-like Pattern)

#### authStore 구현
```typescript
interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  loading: boolean;
}

class AuthStore {
  private state: AuthState;
  private listeners: Set<(state: AuthState) => void> = new Set();
  
  getState(): AuthState {
    return this.state;
  }
  
  setState(newState: Partial<AuthState>): void {
    this.state = { ...this.state, ...newState };
    this.notifyListeners();
  }
  
  subscribe(listener: (state: AuthState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
  
  private notifyListeners(): void {
    this.listeners.forEach(listener => listener(this.state));
  }
}

export const authStore = new AuthStore();
```

## 실행 방법

### Docker Compose
```bash
# 전체 환경 실행
make all

# 개발 가이드 확인
make dev-guide

# 상태 확인
make status
```

### 로컬 개발
```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend
cd backend
npm install
npm run dev
```

## 주요 성과

- **풀스택 웹 애플리케이션:** TypeScript 기반 Frontend + Backend 구현
- **실시간 게임 로직:** WebSocket을 통한 60 FPS 멀티플레이어 게임
- **토너먼트 시스템:** Single Elimination 방식 대진표 자동 생성
- **OAuth 통합:** Google OAuth 2.0 구현 (Authorization Code Flow)
- **2FA 보안:** TOTP 기반 2단계 인증
- **다국어 지원:** i18next를 통한 3개 언어 (한국어, 영어, 일본어)
- **모듈화된 아키텍처:** 계층 분리 및 의존성 주입 패턴

## 기술적 도전 과제

1. **WebSocket 상태 동기화:** 클라이언트-서버 게임 상태 일관성 유지
2. **Vanilla TypeScript SPA:** 프레임워크 없이 라우팅 및 상태 관리 구현
3. **토너먼트 로직:** 대진표 생성 알고리즘, 승자 자동 배정
4. **OAuth & 2FA:** 보안 토큰 관리, TOTP 검증 구현
5. **Canvas 렌더링:** 60 FPS 게임 렌더링 최적화

---

**개발 기간:** 2025.04 ~ 2025.07  
**팀 구성:** 4인  
**주요 기술:** TypeScript, Fastify, WebSocket, OAuth, 2FA, SQLite, i18next, Docker
