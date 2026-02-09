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
| **프로토콜** | HTTP/1.1, CGI |

**Motivation**: Nginx와 같은 고성능 웹 서버의 내부 동작 원리를 이해하고, 동시성 처리와 이벤트 기반 아키텍처를 직접 구현.

---

## Challenge 1: kqueue 이벤트 루프 설계

### Problem
수천 개의 동시 연결을 처리하려면 `select()`/`poll()`의 O(n) 스캔은 비효율적. kqueue의 이벤트 알림 메커니즘 학습 필요.

### kqueue 기본 구조
```cpp
class Demultiplexer {
private:
    int kqueueFd_;
    std::vector<struct kevent> eventList_;
    
public:
    Demultiplexer() {
        kqueueFd_ = kqueue();
        eventList_.resize(64);  // 최대 64개 이벤트 동시 처리
    }
    
    void addReadEvent(int fd) {
        struct kevent event;
        EV_SET(&event, fd, EVFILT_READ, EV_ADD | EV_ENABLE, 0, 0, NULL);
        kevent(kqueueFd_, &event, 1, NULL, 0, NULL);
    }
    
    std::vector<struct kevent> waitForEvents(timespec* timeout) {
        int nev = kevent(kqueueFd_, NULL, 0, 
                        eventList_.data(), eventList_.size(), 
                        timeout);
        return std::vector<struct kevent>(eventList_.begin(), 
                                         eventList_.begin() + nev);
    }
};
```

### Reactor Pattern 구현
**Main Event Loop**:
```cpp
void ServerManager::run() {
    while (isRunning_) {
        // 1. 다음 타임아웃 계산
        timespec* timeout = timeoutHandler_.getNextTimeout();
        
        // 2. 이벤트 대기 (블로킹 또는 timeout까지)
        std::vector<kevent> events = demultiplexer_.waitForEvents(timeout);
        
        // 3. 이벤트 dispatch
        for (size_t i = 0; i < events.size(); i++) {
            int fd = events[i].ident;
            
            if (events[i].filter == EVFILT_READ) {
                if (isListeningSocket(fd))
                    handleNewConnection(fd);  // accept()
                else if (isClientSocket(fd))
                    handleClientRead(fd);     // recv()
                else if (isCgiPipe(fd))
                    handleCgiOutput(fd);      // read()
            } else if (events[i].filter == EVFILT_WRITE) {
                handleClientWrite(fd);        // send()
            }
        }
        
        // 4. 타임아웃된 연결 정리
        timeoutHandler_.checkTimeouts(clientManager_);
    }
}
```

### Challenge: EAGAIN 처리
논블로킹 소켓에서 `recv()`/`send()`는 데이터가 없으면 `EAGAIN` 반환:
```cpp
ssize_t EventHandler::readFromSocket(int fd, std::string& buffer) {
    char tempBuf[4096];
    ssize_t totalRead = 0;
    
    while (true) {
        ssize_t n = recv(fd, tempBuf, sizeof(tempBuf), 0);
        
        if (n > 0) {
            buffer.append(tempBuf, n);
            totalRead += n;
        } else if (n == 0) {
            // 클라이언트가 연결 종료
            return 0;
        } else {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                // 현재 읽을 데이터 없음 → 다음 이벤트 대기
                return totalRead;
            } else {
                // 실제 에러
                return -1;
            }
        }
    }
}
```

### Impact
- 단일 스레드로 수천 개 동시 연결 처리 (C10K 문제 해결)
- kqueue의 O(1) 이벤트 알림으로 `select()`의 O(n) 스캔 제거
- **교훈**: 이벤트 드리븐 아키텍처는 멀티스레딩 없이도 고성능 달성 가능. 논블로킹 I/O의 핵심은 "부분 읽기/쓰기" 처리.

---

## Challenge 2: HTTP 파싱 상태 머신

### Problem
HTTP 요청은 가변 길이 (헤더 수, Body 크기). 네트워크 패킷은 분할 도착 가능 → **증분 파싱** 필요.

### Finite State Machine
```cpp
enum ParseState {
    PARSE_REQUEST_LINE,
    PARSE_HEADERS,
    PARSE_BODY,
    PARSE_CHUNKED_BODY,
    PARSE_COMPLETE,
    PARSE_ERROR
};

class RequestParser {
private:
    ParseState state_;
    std::string buffer_;  // 누적 버퍼
    
public:
    EnumStatusCode parse(const std::string& newData, 
                         RequestMessage& reqMsg) {
        buffer_ += newData;  // 새 데이터 추가
        
        while (state_ != PARSE_COMPLETE && state_ != PARSE_ERROR) {
            switch (state_) {
            case PARSE_REQUEST_LINE:
                if (!hasCompleteLine(buffer_)) return INCOMPLETE;
                state_ = parseRequestLine(buffer_, reqMsg);
                break;
                
            case PARSE_HEADERS:
                if (!hasDoubleNewline(buffer_)) return INCOMPLETE;
                state_ = parseHeaders(buffer_, reqMsg);
                break;
                
            case PARSE_BODY:
                // Content-Length만큼 읽었는지 확인
                size_t contentLength = reqMsg.headers["Content-Length"];
                if (buffer_.size() < contentLength) return INCOMPLETE;
                state_ = parseBody(buffer_, reqMsg, contentLength);
                break;
            }
        }
        
        return (state_ == PARSE_COMPLETE) ? OK : BAD_REQUEST;
    }
};
```

### Chunked Transfer Encoding
HTTP/1.1의 스트리밍 전송:
```
POST /upload HTTP/1.1
Transfer-Encoding: chunked

7\r\n
Mozilla\r\n
9\r\n
Developer\r\n
0\r\n
\r\n
```

파싱 로직:
```cpp
EnumStatusCode parseChunkedBody(std::string& buffer, 
                                RequestMessage& reqMsg) {
    while (true) {
        // 1. 청크 크기 읽기 (16진수)
        size_t pos = buffer.find("\r\n");
        if (pos == std::string::npos) return INCOMPLETE;
        
        std::string sizeStr = buffer.substr(0, pos);
        size_t chunkSize = std::strtol(sizeStr.c_str(), NULL, 16);
        buffer.erase(0, pos + 2);
        
        if (chunkSize == 0) {
            // 마지막 청크
            buffer.erase(0, 2);  // 최종 \r\n 제거
            return PARSE_COMPLETE;
        }
        
        // 2. 청크 데이터 읽기
        if (buffer.size() < chunkSize + 2) return INCOMPLETE;
        reqMsg.body.append(buffer, 0, chunkSize);
        buffer.erase(0, chunkSize + 2);  // 데이터 + \r\n 제거
    }
}
```

### Impact
- 부분 요청 처리로 메모리 효율 향상 (전체 요청이 도착할 때까지 블로킹 없음)
- Chunked encoding으로 스트리밍 업로드 지원
- **교훈**: 네트워크 프로그래밍은 "부분 데이터"가 기본. 상태 머신으로 점진적 파싱 구현.

---

## Challenge 3: CGI 프로세스 관리 & 데드락

### Problem
Python/Bash 스크립트 실행을 위해 `fork()`/`exec()` 필요. 자식 프로세스와 파이프 통신 중 **데드락** 발생.

### CGI 실행 구조
```cpp
std::string CgiHandler::executeCgi(const RequestMessage& req, 
                                    const RequestConfig& config) {
    int pipeIn[2], pipeOut[2];
    pipe(pipeIn);   // 부모 → 자식 (stdin)
    pipe(pipeOut);  // 자식 → 부모 (stdout)
    
    pid_t pid = fork();
    
    if (pid == 0) {
        // 자식 프로세스
        dup2(pipeIn[0], STDIN_FILENO);
        dup2(pipeOut[1], STDOUT_FILENO);
        
        close(pipeIn[0]); close(pipeIn[1]);
        close(pipeOut[0]); close(pipeOut[1]);
        
        // 환경 변수 설정
        char* envp[] = {
            "REQUEST_METHOD=POST",
            "CONTENT_LENGTH=1024",
            // ...
            NULL
        };
        
        execve("/usr/bin/python3", argv, envp);
        exit(1);  // execve 실패
    }
    
    // 부모 프로세스
    close(pipeIn[0]);
    close(pipeOut[1]);
    
    // 1. Request body를 stdin으로 전송
    write(pipeIn[1], req.body.c_str(), req.body.size());
    close(pipeIn[1]);  // CRITICAL: EOF 전송
    
    // 2. CGI 출력 읽기
    std::string output;
    char buffer[4096];
    ssize_t n;
    while ((n = read(pipeOut[0], buffer, sizeof(buffer))) > 0) {
        output.append(buffer, n);
    }
    close(pipeOut[0]);
    
    waitpid(pid, NULL, 0);
    
    return output;
}
```

### 데드락 사례
**문제**: 부모가 `write()`를 끝내고 `read()`로 넘어갔지만, 자식이 무한히 `read(stdin)` 대기.

**원인**: `close(pipeIn[1])`을 하지 않아 자식이 EOF를 받지 못함. 파이프 버퍼가 가득 차면 부모의 `write()`도 블로킹 → **양방향 데드락**.

**해결**:
```cpp
// Body 전송 후 즉시 write end 닫기
write(pipeIn[1], req.body.c_str(), req.body.size());
close(pipeIn[1]);  // ← 이것이 핵심! 자식에게 EOF 전송
```

### CGI Timeout
CGI 스크립트가 무한 루프에 빠지면 서버 전체가 멈출 수 있음:
```cpp
// SIGALRM으로 timeout 구현
signal(SIGALRM, cgiTimeoutHandler);
alarm(30);  // 30초 timeout

pid_t pid = fork();
if (pid == 0) {
    execve(scriptPath, argv, envp);
}

waitpid(pid, &status, 0);
alarm(0);  // 타이머 해제

if (WIFSIGNALED(status) && WTERMSIG(status) == SIGALRM) {
    return "504 Gateway Timeout";
}
```

### Impact
- CGI 스크립트 실행 성공 (Python, Bash)
- 파이프 통신의 EOF 처리 및 데드락 해결
- **교훈**: IPC의 핵심은 "양쪽 끝 닫기". 프로세스간 통신은 양방향 동기화 필수.

---

## 최종 아키텍처

```plaintext
┌─────────────────────────────────────────┐
│         ServerManager (main loop)       │
│  Reactor Pattern Event Dispatcher       │
└─────────────────────────────────────────┘
         ↓               ↓
┌──────────────┐   ┌─────────────────┐
│ Demultiplexer│   │  EventHandler   │
│  (kqueue)    │   │ Read/Write/CGI  │
└──────────────┘   └─────────────────┘
         ↓               ↓
┌──────────────┐   ┌──────────────────┐
│ClientManager │   │ RequestParser    │
│Session Manage│   │HTTP State Machine│
└──────────────┘   └──────────────────┘
         ↓               ↓
┌──────────────┐   ┌─────────────────┐
│StaticHandler │   │   CgiHandler    │
│file serving  │   │fork/exec/pipe   │
└──────────────┘   └─────────────────┘
```

---

## Key Takeaways

### Concurrency
- **이벤트 루프 > 멀티스레딩** (단일 스레드로 C10K 달성)
- **논블로킹 I/O는 부분 처리가 기본**: EAGAIN, 증분 읽기/쓰기
- **kqueue의 힘**: O(1) 이벤트 알림, level-triggered vs edge-triggered

### Architecture
- **Reactor 패턴**: Demultiplexer (이벤트 감지) + Event Handler (처리 로직 분리)
- **상태 머신 설계**: HTTP 파싱, CGI 통신 모두 FSM
- **계층 분리**: Presentation → Business Logic → Service → Data

### C++98 Constraints
- **RAII 패턴**: 스마트 포인터 없이 자원 관리 (소켓 래퍼 클래스)
- **예외 안전성**: 소멸자에서 모든 자원 정리
- **메모리 누수 방지**: `new`/`delete` 페어링, Valgrind 검증

---

*개발 기간: 2025.01 ~ 2025.03 | 팀: 4인 (sehyupar, seonseo, damin, taerakim)*