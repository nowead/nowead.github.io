+++
date = '2025-09-08T09:00:00+09:00'
draft = false
title = '[Vulkan] Ep04. Vulkan 흐름과 용어'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Terminology", "Architecture"]
categories = ["그래픽스 프로그래밍"]
summary = "Vulkan 개발에서 반복되는 패턴과 보일러플레이트 코드를 정리합니다. 효율적인 코드 작성 방법을 다룹니다."
+++

## 시작하며

지난 [Ep03]에서 Vulkan의 큰 그림을 봤다. 하지만 여전히 "Command Buffer는 Buffer인데 왜 데이터라고 안 하지?", "Index Buffer는 또 뭐지?" 같은 의문이 꼬리를 문다.

Vulkan에는 수많은 '객체'와 '버퍼'들이 존재한다. 이것들을 한 번에 다 이해하려고 하면 체한다.

오늘은 이 용어들을 **세 가지 관점**(계층, 데이터, 실행)에서 반복적으로 해부해 볼 것이다. 이 글 하나로 앞으로 나올 용어들의 지도를 완성하는 것이 목표다.

---

## 관점1: 정적 객체 계층 (The Static Objects)

프로그램이 시작될 때 "**딱 한 번 만들어서 계속 쓰는**" 친구들이다. 하드웨어와 소프트웨어의 뼈대를 담당한다.

### 1. 시스템 연결

- **Instance**: Vulkan 라이브러리와 앱을 잇는 대문.
- **Physical Device**: 실제 그래픽 카드(GPU).
- **Logical Device**: GPU를 다루기 위한 리모컨(소프트웨어 인터페이스).

### 2. 화면 관련

- **Surface**: 윈도우(OS) 창과 Vulkan을 연결하는 추상적인 판.
- **Swapchain**: 화면에 보여질 **이미지**(Image) 들의 대기열. (보통 2~3장을 돌려가며 쓴다)
- **Image View**: 이미지를 "어떻게 볼 것인가"를 정의하는 객체. (원본 이미지를 바로 쓰지 않고 항상 View를 통해 접근한다)

### 3. 렌더링 설정

- **Render Pass**: 렌더링의 **설계도**.
  - "이 패스에서는 색상 이미지 1개, 깊이 이미지 1개를 쓴다."
  - "그리기 전에는 지우고(Clear), 끝나면 저장(Store)해라."
- **Framebuffer**: Render Pass 설계도에 끼워 넣을 **실제 종이**(Image View) 묶음.
  - Render Pass가 "틀"이라면, Framebuffer는 그 틀에 찍어낼 "실체"다.
- **Pipeline**: 렌더링 **상태**(State)의 집합체.
  - 셰이더, 뷰포트, 블렌딩, 래스터라이저 설정 등을 모두 합쳐서 **미리 구워**(Bake) 놓은 불변 객체.

---

## 관점2: 버퍼와 데이터 흐름 (The Buffers & Data)

이제 뼈대 위에 **데이터**를 흘려보낼 차례다. Vulkan에는 이름에 `Buffer`가 들어가는 녀석이 참 많다. 이를 명확히 구분해보자.

### 1. 데이터 운반용 버퍼 (메모리)

- **Vertex Buffer**: 점(Vertex)의 위치, 색상, 텍스처 좌표 정보를 담고 있는 배열.
  - 예: `[{x,y,z, r,g,b}, {x,y,z, r,g,b} ...]`
- **Index Buffer**: 정점을 재사용하기 위한 번호표 배열.
  - 사각형을 그릴 때 정점 4개만 정의하고, Index Buffer에 `[0, 1, 2, 2, 3, 0]` 순서로 그리라고 적어두면 정점 데이터를 중복해서 만들 필요가 없다. (메모리 최적화 핵심)
- **Uniform Buffer**: 셰이더 전체가 공유하는 전역 변수 저장소.
  - MVP(Model-View-Projection) 행렬처럼, 삼각형의 모든 점이 동일하게 사용하는 데이터를 담는다.
- **Staging Buffer**: "**임시 배달통**".
  - CPU는 GPU 전용 메모리(Device Local)에 직접 접근하지 못한다.
  - 그래서 CPU가 접근 가능한 이 Staging Buffer에 데이터를 먼저 쓰고, GPU에게 "이거 가져가"라고 명령한다.

### 2. 명령 저장용 버퍼

- **Command Buffer**: 얘는 데이터가 아니라 "**명령문**"을 담는 버퍼다.
  - `vkCmdDraw`, `vkCmdBindPipeline` 같은 함수 호출을 **녹화**(Record) 해두는 테이프다.
  - GPU는 이 테이프를 받아야만 움직인다.
- **Command Pool**: Command Buffer를 찍어내는 공장이자 메모리 관리자.

### 3. 연결 고리 (Descriptors)

- **Descriptor**: "유니폼 버퍼는 메모리 A번지에 있고, 텍스처는 B번지에 있어"라고 셰이더에게 알려주는 **포인터**.
- **Descriptor Set**: 실제 리소스들을 묶어놓은 세트.
- **Descriptor Set Layout**: 세트의 구조(설계도).

---

## 관점3: 실행과 동기화 (Execution & Sync)

객체도 만들었고 데이터도 채웠다. 이제 매 프레임 반복되는 **Loop** 안에서 이들이 어떻게 움직이는지 보자.

### 1. 명령의 실행 (Queue & Submit)

- **Queue**: GPU에게 일감을 던져주는 **투입구**.
  - 우리가 녹화한 **Command Buffer**를 `vkQueueSubmit` 함수로 큐에 제출하면 GPU가 일을 시작한다.

### 2. 기다림 (Synchronization)

Vulkan은 개발자가 직접 교통정리를 해야 한다. 여기서 사고가 가장 많이 난다.

- **Semaphore**(세마포어): **GPU vs GPU**(내부자들끼리의 신호)
  - 상황: `Acquire Image` (이미지 가져오기) 명령과 `Draw` (그리기) 명령은 둘 다 GPU가 처리한다.
  - 문제: 이미지를 가져오기도 전에 그리기를 시작하면 안 된다.
  - 해결: "이미지 다 가져오면 신호 줄게(Signal), 그때 그려(Wait)"라고 **Semaphore**로 약속한다.

- **Fence**(펜스): **CPU vs GPU**(관리자와 작업자 간 신호)
  - 상황: CPU는 GPU보다 빠르다. GPU가 1프레임을 다 그리지도 않았는데 CPU가 2프레임 데이터를 수정하면 화면이 깨진다.
  - 해결: CPU가 "GPU야 너 다 했니?" 하고 묻고, 안 끝났으면 기다린다(`vkWaitForFences`). 일종의 **울타리**다.

---

## 요약: 용어

흐름을 다시한번 정리해보자.

1. **준비**(Setup)

    - **Instance/Device**로 시동 걸고,
    - **RenderPass/Pipeline**으로 작업 규칙 정하고,
    - **Framebuffer**로 그릴 대상 연결.

2. **데이터 로드**(Resources)

    - **Staging Buffer**에 데이터 복사 -> **Vertex/Index Buffer**로 전송.
    - **Uniform Buffer** 생성 후 **Descriptor Set**으로 셰이더와 연결.

3. **그리기 루프**(Render Loop)

    - **Fence** 대기 (이전 프레임 완료 확인).
    - **Acquire Image** (스왑체인에서 종이 받기 -> **Semaphore A** 신호 예약).
    - **Command Buffer** 녹화 (혹은 리셋 후 녹화).
    - **Queue Submit** (제출! -> **Semaphore A** 기다리고, 끝나면 **Semaphore B** 신호 줘).
    - **Present** (화면 출력 -> **Semaphore B** 기다렸다가 출발).

## 마치며

수많은 용어가 나왔지만, 결국 역할은 셋 중 하나다.
"**설정하거나(Object), 담거나(Buffer), 순서를 정하거나(Sync)**."

아직 궁금한 점이 많다. **실시간으로 입력되는 데이터들은 어떻게 GPU에게 알려줄 수 있는지. 그리고 미리 구워지는 객체들은 어떻게 설정을 하는건지. 위에 나오는 여러 객체들은 어떻게 디자인 되어있고 어떤 자료구조를 가지는지 등등.** 이제 개념들을 하나하나 자세히 공부하면서 궁금증을 해결하고 몸으로 체화해야겠다.
