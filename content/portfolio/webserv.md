---
title: "WebServ - C++98 HTTP Server"
date: 2025-01-01
weight: 3
tags: ["C++98", "HTTP", "Network", "42Seoul", "kqueue", "CGI"]
github: "https://github.com/nowead/webserv"
summary: "C++98 HTTP/1.1 서버 구현 - Reactor 패턴 기반 이벤트 주도 아키텍처"
---

## 프로젝트 개요

WebServ는 42Seoul의 네트워크 프로젝트로, C++98 표준을 사용하여 HTTP/1.1 프로토콜을 지원하는 경량 웹 서버를 처음부터 구현한 프로젝트입니다. Reactor 패턴 기반의 이벤트 주도 아키텍처와 macOS의 kqueue를 활용한 논블로킹 I/O를 통해 다중 클라이언트 연결을 효율적으로 처리합니다.

## 핵심 기술 스택

- **언어:** C++98
- **프로토콜:** HTTP/1.1
- **I/O 멀티플렉싱:** kqueue (macOS)
- **아키텍처:** Reactor Pattern, Event-Driven
- **CGI 지원:** Python, Bash 스크립트 실행
- **빌드 시스템:** Makefile

## 아키텍처

### Layered Architecture (계층 구조)

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│                      (main.cpp)                             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                      │
│  ServerManager │ EventHandler │ TimeoutHandler │ AuthManager │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                           │
│  Demultiplexer │ ClientManager │ RequestParser │ StaticHandler │
│  CgiHandler │ ResponseBuilder                               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                             │
│  GlobalConfig │ ServerConfig │ RequestConfig │ ClientSession │
└─────────────────────────────────────────────────────────────┘
```

### Event Loop (이벤트 루프)

**Reactor 패턴 기반:**
```cpp
void ServerManager::run() {
    Demultiplexer demultiplexer;
    EventHandler eventHandler;
    ClientManager clientManager;
    TimeoutHandler timeoutHandler;
    
    while (isServerRunning()) {
        // 1. 타임아웃 값 획득
        timespec* timeout = timeoutHandler.getNextTimeout();
        
        // 2. 이벤트 대기 (kqueue)
        std::vector<kevent> events = demultiplexer.waitForEvent(
            listenFds_, timeout
        );
        
        // 3. 이벤트 처리
        for (each event in events) {
            if (event.filter == EVFILT_READ) {
                if (isListeningSocket(fd))
                    processServerReadEvent(fd);
                else if (isClientSocket(fd))
                    processClientReadEvent(fd);
                else if (isCgiPipe(fd))
                    processCgiReadEvent(fd);
            } else if (event.filter == EVFILT_WRITE) {
                processClientWriteEvent(fd);
            }
        }
        
        // 4. 타임아웃된 클라이언트 정리
        timeoutHandler.checkTimeouts(clientManager);
    }
}
```

## 주요 기능

### 1. 논블로킹 I/O 및 kqueue

**소켓 설정:**
```cpp
int ServerManager::setNonBlocking(int sockFd) const {
    int flags = fcntl(sockFd, F_GETFL, 0);
    if (flags < 0) return -1;
    
    if (fcntl(sockFd, F_SETFL, flags | O_NONBLOCK) < 0)
        return -1;
        
    return 0;
}

int ServerManager::setSocketOptions(int sockFd) const {
    int opt = 1;
    // SO_REUSEADDR: 포트 재사용 허용
    if (setsockopt(sockFd, SOL_SOCKET, SO_REUSEADDR, 
                   &opt, sizeof(opt)) < 0)
        return -1;
    return 0;
}
```

**kqueue 이벤트 등록:**
```cpp
void Demultiplexer::addReadEvent(int fd) {
    struct kevent event;
    EV_SET(&event, fd, EVFILT_READ, EV_ADD | EV_ENABLE, 0, 0, NULL);
    kevent(kqueueFd_, &event, 1, NULL, 0, NULL);
}

void Demultiplexer::addWriteEvent(int fd) {
    struct kevent event;
    EV_SET(&event, fd, EVFILT_WRITE, EV_ADD | EV_ENABLE, 0, 0, NULL);
    kevent(kqueueFd_, &event, 1, NULL, 0, NULL);
}
```

### 2. HTTP 요청 파싱

**RequestParser 클래스:**
```cpp
class RequestParser {
public:
    EnumStatusCode parse(const std::string& rawRequest, 
                         RequestMessage& reqMsg);
    
private:
    EnumStatusCode parseRequestLine(const std::string& line, 
                                    RequestMessage& reqMsg);
    EnumStatusCode parseHeaders(std::istringstream& stream, 
                                RequestMessage& reqMsg);
    EnumStatusCode parseBody(std::istringstream& stream, 
                            RequestMessage& reqMsg, 
                            const RequestConfig& config);
    
    // Chunked Transfer Encoding 지원
    EnumStatusCode parseChunkedBody(std::istringstream& stream, 
                                    RequestMessage& reqMsg);
};
```

**지원 기능:**
- HTTP 메소드: GET, POST, DELETE
- Chunked Transfer Encoding
- Content-Length 검증
- URI 길이 제한 (414 URI Too Long)
- Body 크기 제한 (413 Payload Too Large)

### 3. CGI (Common Gateway Interface) 지원

**CGIHandler 클래스:**
```cpp
std::string CgiHandler::handleRequest(const RequestMessage& reqMsg, 
                                      const RequestConfig& conf) {
    // 1. CGI 환경 변수 설정
    std::vector<std::string> envVars = setupCgiEnvironment(reqMsg, conf);
    
    // 2. 파이프 생성 (stdin, stdout)
    int pipeIn[2], pipeOut[2];
    pipe(pipeIn);
    pipe(pipeOut);
    
    // 3. fork & exec
    pid_t pid = fork();
    if (pid == 0) {
        // Child process
        dup2(pipeIn[0], STDIN_FILENO);
        dup2(pipeOut[1], STDOUT_FILENO);
        close(pipeIn[1]);
        close(pipeOut[0]);
        
        execve(scriptPath.c_str(), argv, envp);
        exit(1);
    }
    
    // 4. 부모 프로세스: 데이터 송수신
    close(pipeIn[0]);
    close(pipeOut[1]);
    
    write(pipeIn[1], reqMsg.body.c_str(), reqMsg.body.size());
    close(pipeIn[1]);
    
    // 5. CGI 출력 읽기
    std::string cgiOutput = readFromPipe(pipeOut[0]);
    close(pipeOut[0]);
    
    waitpid(pid, NULL, 0);
    
    return responseBuilder_.buildForCgi(cgiOutput);
}
```

**환경 변수 설정:**
```cpp
std::vector<std::string> setupCgiEnvironment(const RequestMessage& reqMsg, 
                                            const RequestConfig& conf) {
    std::vector<std::string> env;
    env.push_back("REQUEST_METHOD=" + methodToString(reqMsg.method));
    env.push_back("SCRIPT_FILENAME=" + conf.root + reqMsg.uri);
    env.push_back("QUERY_STRING=" + reqMsg.queryString);
    env.push_back("CONTENT_TYPE=" + reqMsg.headers["Content-Type"]);
    env.push_back("CONTENT_LENGTH=" + std::to_string(reqMsg.body.size()));
    env.push_back("SERVER_PROTOCOL=HTTP/1.1");
    // ... 기타 환경 변수
    return env;
}
```

### 4. 가상 호스트 및 Settings 관리

**GlobalConfig (싱글톤):**
```cpp
class GlobalConfig {
public:
    static const GlobalConfig& getInstance();
    static void initGlobalConfig(const char* path);
    
    // 3단계 검색: 리스닝 소켓 → 도메인 이름 → URL 경로
    const RequestConfig* findRequestConfig(
        int listenFd,                   // 리스닝 소켓 FD
        const std::string& domainName,  // Host 헤더
        const std::string& targetUri     // 요청 URI
    ) const;
    
private:
    std::vector<ServerConfig> servers_;
    std::map<int, std::vector<ServerConfig*>> listenFdToServers_;
};
```

**설정 파일 예시 (Nginx-like):**
```nginx
server {
    listen 127.0.0.1:8080;
    server_name example.com www.example.com;
    root /var/www/html;
    index index.html;
    
    client_max_body_size 10m;
    error_page 404 /error/404.html;
    
    location / {
        methods GET POST;
        autoindex on;
    }
    
    location /cgi-bin {
        cgi_extension .py;
        methods GET POST;
    }
    
    location /upload {
        methods POST;
        upload_path /tmp/uploads;
        client_max_body_size 20m;
    }
    
    location /old-page {
        return 301 /new-page;
    }
}
```

### 5. 타임아웃 관리

**TimeoutHandler 클래스:**
```cpp
class TimeoutHandler {
public:
    void addConnection(int fd, time_t currentTime);
    void updateActivity(int fd, time_t currentTime);
    void checkTimeouts(ClientManager& clientManager, time_t currentTime);
    
    // kqueue timeout 값 계산
    timespec* getNextTimeout(time_t currentTime);
    
private:
    std::map<int, time_t> lastActivity_;  // FD별 마지막 활동 시간
    const time_t TIMEOUT_SECONDS = 60;
};
```

## 프로젝트 구조

```
src/
├── main.cpp                 # 엔트리 포인트
├── GlobalConfig/            # 전역 설정 관리 (싱글톤)
├── ConfigParser/            # 설정 파일 파싱
├── ServerManager/           # 메인 이벤트 루프 (Reactor 패턴)
├── Demultiplexer/           # kqueue 래퍼
├── EventHandler/            # 이벤트 처리 (Read/Write/CGI)
├── ClientManager/           # 클라이언트 세션 관리
├── ClientSession/           # 클라이언트 연결 상태
├── RequestParser/           # HTTP 요청 파싱
├── RequestHandler/          # 요청 처리 (Static/CGI)
│   ├── StaticHandler.cpp    # 정적 파일 서빙
│   └── CgiHandler.cpp       # CGI 스크립트 실행
├── ResponseBuilder/         # HTTP 응답 생성
├── TimeoutHandler/          # 타임아웃 관리
└── utils/                   # 유틸리티 함수
```

## 빌드 및 실행

```bash
# Clone repository
git clone https://github.com/yourusername/webserv.git
cd webserv

# Build
make

# Run with config file
./webserv configs/default.conf
```

## 주요 성과

- **HTTP/1.1 프로토콜 완전 구현:** GET, POST, DELETE 메소드 지원
- **이벤트 기반 아키텍처:** kqueue를 활용한 논블로킹 I/O
- **CGI 지원:** Python, Bash 스크립트 실행 및 환경 변수 전달
- **가상 호스트:** 도메인별 독립적인 설정 관리
- **타임아웃 관리:** 비활성 연결 자동 정리
- **오류 처리:** 커스텀 오류 페이지, 상세한 오류 메시지
- **Chunked Transfer Encoding:** 스트리밍 데이터 전송 지원

## 기술적 도전 과제

1. **kqueue API 마스터:** macOS의 이벤트 알림 메커니즘 이해
2. **논블로킹 I/O:** EAGAIN/EWOULDBLOCK 처리, 부분 읽기/쓰기
3. **HTTP 파싱:** RFC 9110/9112 준수, Chunked Encoding
4. **CGI 프로세스 관리:** fork/exec, 파이프 통신, 환경 변수
5. **메모리 관리:** C++98 제약 (스마트 포인터 없음), RAII 패턴 활용

---

**개발 기간:** 2025.01 ~ 2025.03  
**팀 구성:** 4인 (sehyupar, seonseo, damin, taerakim)  
**주요 기술:** C++98, HTTP/1.1, kqueue, Reactor Pattern, CGI, 논블로킹 I/O
