---
title: "WebServ - C++98 HTTP Server"
date: 2025-01-01
weight: 3
tags: ["C++98", "HTTP", "Network", "42Seoul", "kqueue", "CGI"]
github: "https://github.com/nowead/webserv"
summary: "C++98 HTTP/1.1 서버 구현 - Reactor 패턴 기반 이벤트 주도 아키텍처"
cover_image: "webserv-image/webserv-architecture.png"
---

# WebServ

> C++98로 구현한 HTTP/1.1 웹 서버 — kqueue, Reactor 패턴, 논블로킹 I/O

**C++98 | HTTP/1.1 | kqueue | Reactor Pattern | CGI**

2025.01 ~ 2025.03 (3개월) | 4인 개발 | macOS

---

## Overview

C++98 표준으로 HTTP/1.1 프로토콜을 지원하는 이벤트 드리븐 웹 서버를 처음부터 구현.

| 항목 | 내용 |
|------|------|
| **언어** | C++98 (스마트 포인터 없음) |
| **I/O 멀티플렉싱** | kqueue (macOS) |
| **아키텍처** | Reactor Pattern, 4-Layer |
| **동시성** | 단일 스레드 이벤트 루프 |

**Motivation**: Nginx와 같은 고성능 웹 서버의 내부 동작 원리를 이해하고, 동시성 처리와 이벤트 기반 아키텍처를 직접 구현하여 네트워크 프로그래밍 역량 강화.

![WebServ Architecture](/portfolio/webserv-image/webserv-architecture.png)
*4-Layer Architecture: Network → Reactor → Handler → Application*

---

## Challenge 1: kqueue 기반 동시성 처리

### Problem
수천 개의 동시 연결을 단일 스레드로 처리하려면 효율적인 I/O 멀티플렉싱 필요. `select()`/`poll()`의 O(n) 스캔은 비효율적.

### Solution: Reactor Pattern + kqueue

**핵심 아키텍처:**
```cpp
void ServerManager::run() {
    EventHandler     eventHandler;
    ClientManager    clientManager;
    Demultiplexer    reactor(listenFds_);
    TimeoutHandler   timeoutHandler;

    while (isServerRunning()) {
        // 1. 다음 타임아웃 계산
        timespec* timeout = timeoutHandler.getEarliestTimeout();
        
        // 2. 이벤트 대기 (O(1) 알림)
        int numEvents = reactor.waitForEvent(timeout);
        
        // 3. 이벤트 dispatch
        for (int i = 0; i < numEvents; ++i) {
            int fd = reactor.getSocketFd(i);
            EnumEvent type = reactor.getEventType(i);
            
            if (type == READ_EVENT) {
                if (isListeningSocket(fd))
                    handleNewConnection(fd);
                else if (clientManager.isClientSocket(fd))
                    handleClientRead(fd);
                else
                    handleCgiOutput(fd);
            } else if (type == WRITE_EVENT) {
                handleClientWrite(fd);
            }
        }
        
        // 4. 타임아웃 정리
        timeoutHandler.checkTimeouts(eventHandler, reactor, clientManager);
    }
}
```

**kqueue 구현:**
```cpp
class KqueueDemultiplexer {
private:
    int kqueueFd_;
    std::vector<struct kevent> eventList_;  // 최대 1024개 이벤트
    
public:
    KqueueDemultiplexer() {
        kqueueFd_ = kqueue();
        eventList_.resize(1024);
    }
    
    void addReadEvent(int fd) {
        struct kevent event;
        EV_SET(&event, fd, EVFILT_READ, EV_ADD | EV_ENABLE, 0, 0, NULL);
        kevent(kqueueFd_, &event, 1, NULL, 0, NULL);
    }
    
    int waitForEvent(timespec* timeout) {
        return kevent(kqueueFd_, NULL, 0, 
                     &eventList_[0], 1024, timeout);
    }
};
```

**논블로킹 I/O:**
```cpp
EnumSesStatus EventHandler::recvRequest(ClientSession& session) {
    std::string buffer;
    buffer.resize(8192);
    
    // MSG_DONTWAIT로 논블로킹 recv
    ssize_t res = recv(session.getClientFd(), 
                      &buffer[0], 8192, MSG_DONTWAIT);
    
    if (res > 0) {
        // 증분 파싱
        EnumStatusCode status = parser_.parse(buffer.substr(0, res), session);
        return (status == OK) ? READ_COMPLETE : READ_CONTINUE;
    } else if (res == 0) {
        return CONNECTION_CLOSED;  // 클라이언트 종료
    } else {
        return CONNECTION_CLOSED;  // 에러 처리
    }
}
```

### Impact
- **동시성**: 단일 스레드로 수천 개 동시 연결 처리 (C10K 해결)
- **성능**: kqueue의 O(1) 이벤트 알림으로 `select()` 대비 대폭 개선
- **교훈**: 이벤트 드리븐 아키텍처는 멀티스레딩 없이도 고성능 달성 가능

---

## Challenge 2: C++98 제약 속 메모리 안전성

### Problem
C++98은 스마트 포인터가 없어 수동 메모리 관리 필수. 네트워크 예외 상황(연결 중단, 타임아웃)에서 메모리 누수 위험.

### Solution: RAII 패턴 + 명시적 생명주기 관리

**ClientSession 생명주기:**
```cpp
class ClientSession {
private:
    int listenFd_;
    int clientFd_;
    RequestMessage* reqMsg_;
    const RequestConfig* config_;
    CgiProcessInfo cgiProcessInfo_;
    std::string readBuffer_;
    std::string writeBuffer_;
    
public:
    ClientSession(int listenFd, int clientFd, std::string clientIP) 
        : listenFd_(listenFd), clientFd_(clientFd), 
          reqMsg_(NULL), config_(NULL) {
        readBuffer_.reserve(8192 * 2);
    }
    
    ~ClientSession() {
        if (reqMsg_)
            delete reqMsg_;
        if (cgiProcessInfo_.isProcessing_)
            cgiProcessInfo_.cleanup();
    }
};
```

**소켓 자원 관리:**
```cpp
class ClientManager {
private:
    typedef std::map<int, ClientSession*> TypeClientMap;
    TypeClientMap clientList_;           // fd → session 매핑
    std::map<int, int> pipeToClientFdMap_;  // pipe → client 매핑
    
public:
    ~ClientManager() {
        TypeClientMap::iterator it;
        for (it = clientList_.begin(); it != clientList_.end(); ++it) {
            delete it->second;  // 세션 삭제
            close(it->first);   // 소켓 닫기
        }
    }
    
    TypeClientMap::iterator removeClient(int fd) {
        TypeClientMap::iterator it = clientList_.find(fd);
        if (it == clientList_.end())
            return clientList_.end();
        
        delete it->second;
        close(fd);
        
        TypeClientMap::iterator nextIt = it;
        ++nextIt;
        clientList_.erase(it);
        return nextIt;
    }
};
```

**CGI 프로세스 정리:**
```cpp
class CgiProcessInfo {
public:
    pid_t pid_;
    int outPipe_;
    
    void cleanup() {
        if (outPipe_ != -1) {
            close(outPipe_);
            outPipe_ = -1;
        }
        
        if (pid_ != -1) {
            int status = waitpid(pid_, NULL, WNOHANG);
            if (status == 0) {  // 아직 실행 중
                kill(pid_, SIGKILL);  // 강제 종료
            }
            pid_ = -1;
        }
    }
};
```

### Impact
- **안정성**: Valgrind로 메모리 누수 0 검증
- **C++98 역량**: 스마트 포인터 없이 RAII 패턴 구현
- **교훈**: 명시적 생명주기 관리로 현대 C++보다 자원 흐름 명확히 이해

---

## Challenge 3: CGI 프로세스 관리 & IPC

### Problem
Python/Bash 스크립트를 실행하려면 `fork()`/`exec()` 필요. 자식 프로세스와 파이프 통신 중 **데드락** 및 **좀비 프로세스** 위험.

### Solution: fork/exec/pipe 구조 + 논블로킹 파이프

**CGI 실행 아키텍처:**
```cpp
bool CgiHandler::executeCgi(std::vector<std::string>& argv,
                            std::vector<std::string>& envp,
                            const std::string& requestBody,
                            pid_t& childPid, int& outPipe_) {
    int inPipe[2], outPipe[2];
    pipe(inPipe);   // 부모 → 자식 (stdin)
    pipe(outPipe);  // 자식 → 부모 (stdout)
    
    // 출력 파이프를 논블로킹으로 설정
    fcntl(outPipe[0], F_SETFL, O_NONBLOCK);
    
    pid_t pid = fork();
    
    if (pid == 0) {  // 자식 프로세스
        dup2(inPipe[0], STDIN_FILENO);
        dup2(outPipe[1], STDOUT_FILENO);
        close(inPipe[1]);
        close(outPipe[0]);
        
        execve(argv[0], &argv[0], &envp[0]);
        _exit(1);  // execve 실패
    }
    
    // 부모 프로세스
    close(inPipe[0]);
    close(outPipe[1]);
    
    // Request body를 stdin으로 전송
    if (!requestBody.empty()) {
        write(inPipe[1], requestBody.c_str(), requestBody.size());
    }
    close(inPipe[1]);  // CRITICAL: EOF 전송
    
    outPipe_ = outPipe[0];  // 이벤트 루프에서 읽기
    childPid = pid;
    
    return true;
}
```

**이벤트 루프 통합:**
```cpp
void ServerManager::processCgiReadEvent(int pipeFd, 
    ClientManager& clientManager, EventHandler& eventHandler,
    TimeoutHandler& timeoutHandler, Demultiplexer& reactor) {
    
    // 파이프에서 클라이언트 FD 조회
    int clientFd = clientManager.accessClientFd(pipeFd);
    ClientSession* client = clientManager.accessClientSession(clientFd);
    
    // CGI 데이터 읽기
    EnumSesStatus status = eventHandler.handleCgiReadEvent(*client);
    
    switch (status) {
    case WAIT_FOR_CGI:
        break;  // 계속 대기
    case WRITE_CONTINUE:
        timeoutHandler.updateActivity(clientFd, status);
        reactor.addWriteEvent(clientFd);
        break;
    case CONNECTION_CLOSED:
        removeClientInfo(clientFd, clientManager, timeoutHandler);
        break;
    }
    
    if (status != WAIT_FOR_CGI)
        clientManager.removePipeFromMap(pipeFd);
}
```

**프로세스 정리:**
```cpp
class CgiProcessInfo {
public:
    pid_t pid_;
    int outPipe_;
    std::ostringstream cgiResultBuffer_;
    bool isProcessing_;
    
    CgiProcessInfo() : pid_(-1), outPipe_(-1), isProcessing_(false) {}
    
    void cleanup() {
        close(outPipe_);
        
        int waitPidReturn = waitpid(pid_, NULL, WNOHANG);
        if (waitPidReturn == 0) {  // 아직 실행 중
            kill(pid_, SIGKILL);   // 강제 종료
        }
        
        pid_ = -1;
        outPipe_ = -1;
        cgiResultBuffer_.str("");
        isProcessing_ = false;
    }
};
```

### Impact
- **동시성 유지**: CGI 실행 중에도 다른 클라이언트 처리 가능 (논블로킹 파이프)
- **안정성**: 좀비 프로세스 방지 (WNOHANG), 데드락 해결 (EOF 전송)
- **교훈**: IPC의 핵심은 "양쪽 끝 닫기". 프로세스간 통신은 자원 정리가 생명

---

## Architecture

```plaintext
┌─────────────────────────────────────────┐
│      ServerManager (Reactor Loop)       │
│    Single Thread Event Dispatcher       │
└─────────────────────────────────────────┘
         ↓               ↓
┌──────────────┐   ┌─────────────────┐
│ Demultiplexer│   │  EventHandler   │
│   (kqueue)   │   │ Read/Write/CGI  │
└──────────────┘   └─────────────────┘
         ↓               ↓
┌──────────────┐   ┌──────────────────┐
│ClientManager │   │ RequestParser    │
│Session Pool  │   │HTTP State Machine│
└──────────────┘   └──────────────────┘
         ↓               ↓
┌──────────────┐   ┌─────────────────┐
│StaticHandler │   │   CgiHandler    │
│file serving  │   │fork/exec/pipe   │
└──────────────┘   └─────────────────┘
```

**설계 원칙:**
- **Separation of Concerns**: Demultiplexer(감지) ↔ EventHandler(처리) 분리
- **Single Responsibility**: 각 클래스가 하나의 책임만 담당
- **Dependency Inversion**: 인터페이스 기반 설계 (DemultiplexerBase 템플릿)

---

## Key Takeaways

### 동시성 처리
- **이벤트 루프 > 멀티스레딩**: 컨텍스트 스위칭 없이 수천 연결 처리
- **kqueue의 힘**: O(1) 이벤트 알림, level-triggered 방식
- **논블로킹 I/O**: MSG_DONTWAIT와 증분 파싱 조합

### C++ 역량
- **C++98 제약**: 스마트 포인터 없이 RAII 패턴 구현
- **예외 안전성**: 소멸자에서 모든 자원 정리
- **STL 활용**: map, vector, string으로 효율적 자료구조 설계

### 아키텍처
- **Reactor 패턴**: 이벤트 감지와 처리 로직 완전 분리
- **비동기 I/O**: kqueue로 소켓과 파이프 통합 관리
- **계층 분리**: Presentation → Application → Service → Infrastructure

---

## Technologies

**Core**: C++98, kqueue, HTTP/1.1, CGI/1.1  
**Build**: Makefile, modular compilation  
**Testing**: Valgrind (메모리 누수), curl, siege (부하 테스트)

---

*개발 기간: 2025.01 ~ 2025.03 | 팀: 4인 (sehyupar, seonseo, damin, taerakim)*