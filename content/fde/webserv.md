---
title: "WebServ"
date: 2025-01-01
weight: 4
stage: "foundation"
track: "TRACK 02 · WEB SERVICE"
category_label: "HTTP server"
status: "42 Seoul 팀 프로젝트"
period: "2025.01 — 2025.03"
role: "4인 팀 프로젝트"
tags: ["C++98", "HTTP/1.1", "kqueue", "CGI", "Reactor"]
github: "https://github.com/nowead/webserv"
summary: "C++98로 HTTP/1.1 서버를 소켓부터 구현했습니다. 요청이 서버에 도착해 응답으로 돌아가기까지의 과정을 직접 만들어 본 경험입니다."
cover_image: "webserv-image/webserv-architecture.png"
cover_fit: "contain"
cover_width: 835
cover_height: 621
image_alt: "WebServ의 네트워크, Reactor, 핸들러, 애플리케이션 계층 구조도"
image_caption: "Network → Reactor → Handler → Application으로 나눈 4계층 구조."
leads_to: "onegoal"
handoff:
  - "HTTP 요청·응답과 연결 수명에 대한 이해 → 리버스 프록시와 헤더 구성 판단"
  - "프로세스와 파이프를 직접 다룬 경험 → 워커 프로세스 기반 운영 구성"
  - "부하·메모리 검사로 확인하는 습관 → 운영 구성까지 점검하는 하네스"
brief:
  problem:
    title: "느린 연결 하나가 전체를 막는다"
    text: "단일 스레드 서버에서 하나의 느린 요청이나 응답 없는 CGI 스크립트가 다른 모든 연결을 멈추게 할 수 있었습니다."
  solution:
    title: "Reactor 패턴과 논블로킹 I/O"
    text: "kqueue로 준비된 소켓만 처리하는 이벤트 루프를 만들고, 요청 파싱과 CGI 입출력을 모두 논블로킹으로 연결했습니다."
  verification:
    title: "부하와 메모리로 확인"
    text: "siege로 동시 접속 부하를 걸고, Valgrind로 세션과 요청 객체의 누수를 점검했습니다. curl로 프로토콜 동작을 확인했습니다."
---

## 왜 서버를 직접 만들었나

웹 서비스는 대부분 프레임워크와 웹 서버 위에서 시작합니다. 편리하지만, 요청이 실제로 어떤 과정을 거쳐 처리되는지는 가려집니다. WebServ는 그 가려진 부분을 직접 구현하는 42 Seoul의 팀 프로젝트입니다. 소켓 통신부터 이벤트 루프, HTTP 파싱, CGI 실행까지 C++98로 만들었습니다.

| 항목 | 내용 |
| --- | --- |
| 언어 | C++98 (스마트 포인터 없음) |
| I/O 멀티플렉싱 | kqueue (macOS) |
| 구조 | Reactor 패턴, 4계층 |
| 동시성 | 단일 스레드 이벤트 루프 |

## 문제 정의: 무엇이 서버를 멈추게 하는가

요구사항은 "여러 클라이언트를 동시에 처리하는 HTTP/1.1 서버"였습니다. 이를 실제로 서버를 멈추게 하는 조건으로 나눠 정의했습니다.

- **느린 연결** — 한 클라이언트가 요청을 조금씩 보내는 동안 다른 연결이 기다리면 안 됩니다.
- **끝나지 않는 CGI** — 스크립트가 응답하지 않아도 서버는 계속 동작해야 합니다.
- **새는 자원** — 스마트 포인터가 없는 C++98에서 소켓과 메모리가 연결 종료와 함께 반드시 정리되어야 합니다.

## 해결

### 준비된 소켓만 처리하는 이벤트 루프

연결마다 스레드를 만드는 대신, kqueue가 알려 주는 준비된 이벤트만 처리하는 Reactor 패턴을 선택했습니다. 이벤트 감지(Demultiplexer)와 처리(EventHandler)를 분리하고, 가장 가까운 타임아웃까지만 기다리도록 했습니다.

```cpp
while (isServerRunning()) {
    // 1. 다음 타임아웃 계산
    timespec* timeout = timeoutHandler.getEarliestTimeout();

    // 2. 준비된 I/O 이벤트 대기
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
```

요청은 `MSG_DONTWAIT`로 받은 만큼만 읽고, 상태를 가진 파서가 이어서 해석합니다. 요청이 여러 조각으로 나뉘어 도착해도 다른 연결을 막지 않습니다.

### 연결과 함께 사라지는 자원

세션 객체가 소켓과 요청·응답 버퍼를 소유하고, 소멸자에서 모두 정리하도록 했습니다. 생성과 해제의 책임을 `ClientManager` 한 곳에 모아, 연결이 끊기거나 타임아웃이 나는 모든 경로에서 같은 정리 절차를 거칩니다.

### CGI: 프로세스와 파이프

CGI는 `fork`/`exec`로 스크립트를 실행하고 파이프로 입출력을 주고받습니다. 여기서 두 가지 문제를 겪었습니다.

- **데드락** — 요청 본문을 다 쓴 뒤 입력 파이프를 닫지 않으면, 스크립트는 입력의 끝을 기다리고 서버는 출력을 기다립니다. 본문을 쓴 직후 파이프를 닫아 EOF를 보내도록 수정했습니다.
- **좀비 프로세스** — 종료된 자식을 회수하지 않으면 프로세스가 남습니다. `waitpid(WNOHANG)`로 상태를 확인하고, 아직 실행 중이면 종료시킨 뒤 정리합니다.

출력 파이프는 논블로킹으로 설정해 소켓과 같은 이벤트 루프에 등록했습니다. CGI가 실행되는 동안에도 다른 클라이언트의 요청을 처리합니다.

## 검증

| 도구 | 확인한 것 |
| --- | --- |
| siege | 동시 접속 부하에서 서버가 멈추지 않고 응답하는지 |
| Valgrind | 세션, 요청 객체, 파이프의 누수 여부 |
| curl | 메서드, 상태 코드, 헤더 등 HTTP 동작 |

## onegoal로 이어진 것

[onegoal](/fde/onegoal/)을 배포할 때는 서버를 직접 만들지 않았습니다. Caddy와 Gunicorn을 사용했습니다. 하지만 이 프로젝트 덕분에 그 구성을 블랙박스로 두지 않을 수 있었습니다.

- 프록시가 애플리케이션 서버로 넘기는 헤더와, 그중 **어떤 클라이언트 IP를 신뢰할지**를 프로토콜 수준에서 판단했습니다.
- 워커 프로세스 기반으로 동작하는 애플리케이션 서버의 구성을 이해하고 선택했습니다.
- "동작한다"가 아니라 **실제 프록시를 띄워 확인한다**는 기준을 운영 구성 점검으로 옮겼습니다.

*팀: 4인 (sehyupar, seonseo, damin, taerakim)*
