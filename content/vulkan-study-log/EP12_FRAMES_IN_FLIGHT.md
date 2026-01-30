+++
date = '2025-09-26T10:00:00+09:00'
draft = false
title = '[Vulkan] EP12. Frames in Flight'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Synchronization", "Frames in Flight", "Performance"]
categories = ["그래픽스 프로그래밍"]
summary = "MAX_FRAMES_IN_FLIGHT 개념을 통해 CPU-GPU 병렬 처리를 최적화하고, 자원 재사용 동기화를 구현합니다."
+++

## 시작하며

[EP11](EP11_RENDERING_PRESENTATION.md)에서 세마포어와 펜스를 사용한 기본 동기화를 다뤘다. 이번 편에서는 **Frames in Flight** 개념을 심층적으로 살펴본다.

Vulkan에서 CPU와 GPU는 비동기적으로 동작한다. CPU는 렌더링 명령을 커맨드 버퍼에 기록하여 GPU에 제출하고, GPU는 이 명령들을 독립적으로 실행한다. `MAX_FRAMES_IN_FLIGHT` 개념은 이러한 비동기적 특성을 효율적으로 관리하고 CPU가 GPU보다 너무 앞서가는 것을 방지하기 위한 핵심적인 동기화 메커니즘이다.

---

## 1. MAX_FRAMES_IN_FLIGHT의 필요성

### 1.1. CPU-GPU 병목 현상 방지

CPU가 너무 빠르게 커맨드 버퍼를 제출하면 문제가 발생한다:

- GPU가 처리할 수 있는 속도보다 제출 속도가 빨라짐
- GPU 큐가 과도하게 쌓임
- GPU 메모리 부족 또는 드라이버 내부 복잡성 증가
- 전체적인 비효율 초래

### 1.2. 자원 재사용 동기화

렌더링에 사용되는 자원들은 동시 접근을 피해야 한다:

- 커맨드 버퍼, 유니폼 버퍼 등
- GPU가 사용 중일 때 CPU가 덮어쓰거나 수정하면 안 됨
- `MAX_FRAMES_IN_FLIGHT`는 자원이 더 이상 GPU에서 사용되지 않음을 확인
- CPU가 안전하게 재사용할 수 있도록 보장

### 1.3. 파이프라인 스톨 방지

GPU는 깊은 파이프라인으로 동작한다:

- 여러 프레임을 동시에 처리하는 것이 성능에 유리
- `MAX_FRAMES_IN_FLIGHT`는 일정 수의 프레임을 GPU 파이프라인에 유지
- 스톨을 최소화하고 GPU 활용도를 높임

```plaintext
[Frame 0] ----[GPU 처리 중]----
[Frame 1] --------[GPU 처리 중]----
[Frame 2] ------------[CPU 준비]----[GPU 처리 중]----

-> MAX_FRAMES_IN_FLIGHT = 2일 때, Frame 0과 Frame 1이 동시에 GPU에서 처리 가능
```

---

## 2. 동기화 객체 확장

`MAX_FRAMES_IN_FLIGHT` 값을 설정하면, 해당 개수만큼의 동기화 객체 세트가 필요하다.

### 2.1. 상수 정의

```cpp
const int MAX_FRAMES_IN_FLIGHT = 2;  // 최대 2개 프레임 동시 처리
```

### 2.2. 동기화 객체 배열

```cpp
std::vector<VkSemaphore> imageAvailableSemaphores;
std::vector<VkSemaphore> renderFinishedSemaphores;
std::vector<VkFence> inFlightFences;
std::vector<VkFence> imagesInFlight;

uint32_t currentFrame = 0;
```

### 2.3. 각 동기화 객체의 역할

| 객체 | 개수 | 역할 |
|------|------|------|
| `imageAvailableSemaphores` | MAX_FRAMES_IN_FLIGHT | 스왑체인 이미지 획득 완료 신호 |
| `renderFinishedSemaphores` | MAX_FRAMES_IN_FLIGHT | 렌더링 완료 신호 |
| `inFlightFences` | MAX_FRAMES_IN_FLIGHT | CPU-GPU 동기화 (프레임 완료 대기) |
| `imagesInFlight` | swapChainImages.size() | 각 스왑체인 이미지의 사용 상태 추적 |

### 2.4. 동기화 객체 생성

```cpp
void createSyncObjects() {
    imageAvailableSemaphores.resize(MAX_FRAMES_IN_FLIGHT);
    renderFinishedSemaphores.resize(MAX_FRAMES_IN_FLIGHT);
    inFlightFences.resize(MAX_FRAMES_IN_FLIGHT);
    imagesInFlight.resize(swapChainImages.size(), VK_NULL_HANDLE);

    VkSemaphoreCreateInfo semaphoreInfo{};
    semaphoreInfo.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;

    VkFenceCreateInfo fenceInfo{};
    fenceInfo.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    fenceInfo.flags = VK_FENCE_CREATE_SIGNALED_BIT;  // 초기 signaled 상태

    for (size_t i = 0; i < MAX_FRAMES_IN_FLIGHT; i++) {
        if (vkCreateSemaphore(device, &semaphoreInfo, nullptr, 
                              &imageAvailableSemaphores[i]) != VK_SUCCESS ||
            vkCreateSemaphore(device, &semaphoreInfo, nullptr, 
                              &renderFinishedSemaphores[i]) != VK_SUCCESS ||
            vkCreateFence(device, &fenceInfo, nullptr, 
                          &inFlightFences[i]) != VK_SUCCESS) {
            throw std::runtime_error("failed to create synchronization objects!");
        }
    }
}
```

**`VK_FENCE_CREATE_SIGNALED_BIT` 사용 이유:**

- 첫 프레임에서 `vkWaitForFences`가 즉시 통과하도록 함
- 초기 `signaled` 상태로 생성하지 않으면 첫 프레임에서 무한 대기 발생

---

## 3. drawFrame 함수 상세 분석

### 3.1. 전체 흐름

```cpp
void drawFrame() {
    // 1. 이전 프레임 완료 대기
    vkWaitForFences(device, 1, &inFlightFences[currentFrame], 
                    VK_TRUE, UINT64_MAX);

    // 2. 스왑체인 이미지 획득
    uint32_t imageIndex;
    VkResult result = vkAcquireNextImageKHR(device, swapChain, UINT64_MAX,
                                             imageAvailableSemaphores[currentFrame],
                                             VK_NULL_HANDLE, &imageIndex);

    if (result == VK_ERROR_OUT_OF_DATE_KHR) {
        recreateSwapChain();
        return;
    }

    // 3. 이미지 사용 상태 확인
    if (imagesInFlight[imageIndex] != VK_NULL_HANDLE) {
        vkWaitForFences(device, 1, &imagesInFlight[imageIndex], 
                        VK_TRUE, UINT64_MAX);
    }
    imagesInFlight[imageIndex] = inFlightFences[currentFrame];

    // 4. 펜스 리셋
    vkResetFences(device, 1, &inFlightFences[currentFrame]);

    // 5. 커맨드 버퍼 제출
    VkSubmitInfo submitInfo{};
    // ... (설정 생략)
    vkQueueSubmit(graphicsQueue, 1, &submitInfo, inFlightFences[currentFrame]);

    // 6. 화면 제시
    VkPresentInfoKHR presentInfo{};
    // ... (설정 생략)
    vkQueuePresentKHR(presentQueue, &presentInfo);

    // 7. 프레임 인덱스 순환
    currentFrame = (currentFrame + 1) % MAX_FRAMES_IN_FLIGHT;
}
```

### 3.2. 단계별 상세 설명

#### 단계 1: 이전 프레임 완료 대기

```cpp
vkWaitForFences(device, 1, &inFlightFences[currentFrame], VK_TRUE, UINT64_MAX);
```

**목적:**

- `currentFrame`에 해당하는 펜스가 `signaled`될 때까지 CPU를 블록
- 이전 프레임의 모든 GPU 작업이 완료되었음을 보장
- 이 시점에서 해당 프레임의 커맨드 버퍼 및 자원을 안전하게 재사용 가능

**파라미터:**

- `VK_TRUE`: 모든 펜스가 `signaled`될 때까지 대기
- `UINT64_MAX`: 무한 대기 (타임아웃 없음)

#### 단계 2: 스왑체인 이미지 획득

```cpp
vkAcquireNextImageKHR(device, swapChain, UINT64_MAX,
                      imageAvailableSemaphores[currentFrame],
                      VK_NULL_HANDLE, &imageIndex);
```

**동작:**

- 스왑체인에서 다음 렌더링 대상 이미지 인덱스 획득
- `imageAvailableSemaphores[currentFrame]`이 이미지 사용 가능 시 `signaled`됨

#### 단계 3: 이미지 사용 상태 확인

```cpp
if (imagesInFlight[imageIndex] != VK_NULL_HANDLE) {
    vkWaitForFences(device, 1, &imagesInFlight[imageIndex], VK_TRUE, UINT64_MAX);
}
imagesInFlight[imageIndex] = inFlightFences[currentFrame];
```

**왜 필요한가:**

- 스왑체인 이미지 개수와 `MAX_FRAMES_IN_FLIGHT`가 다를 수 있음
- 예: 스왑체인 이미지 3개, MAX_FRAMES_IN_FLIGHT = 2
- 특정 이미지가 아직 다른 프레임에서 사용 중일 수 있음

**동작:**

1. `imagesInFlight[imageIndex]`가 `VK_NULL_HANDLE`이 아니면 해당 이미지가 사용 중
2. 해당 펜스가 `signaled`될 때까지 대기
3. 현재 프레임의 펜스를 해당 이미지에 할당

#### 단계 4: 펜스 리셋

```cpp
vkResetFences(device, 1, &inFlightFences[currentFrame]);
```

**주의:**

- `vkWaitForFences` 이후, `vkQueueSubmit` 이전에 호출해야 함
- 펜스를 `unsignaled` 상태로 초기화

#### 단계 5: 커맨드 버퍼 제출

```cpp
VkSubmitInfo submitInfo{};
submitInfo.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;

VkSemaphore waitSemaphores[] = {imageAvailableSemaphores[currentFrame]};
VkPipelineStageFlags waitStages[] = {VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT};
submitInfo.waitSemaphoreCount = 1;
submitInfo.pWaitSemaphores = waitSemaphores;
submitInfo.pWaitDstStageMask = waitStages;

submitInfo.commandBufferCount = 1;
submitInfo.pCommandBuffers = &commandBuffers[imageIndex];

VkSemaphore signalSemaphores[] = {renderFinishedSemaphores[currentFrame]};
submitInfo.signalSemaphoreCount = 1;
submitInfo.pSignalSemaphores = signalSemaphores;

vkQueueSubmit(graphicsQueue, 1, &submitInfo, inFlightFences[currentFrame]);
```

**동기화 객체 사용:**

| 객체 | 용도 |
|------|------|
| `waitSemaphores` | 이미지 획득 완료 대기 |
| `signalSemaphores` | 렌더링 완료 신호 |
| `fence` | CPU-GPU 동기화 |

#### 단계 6: 화면 제시

```cpp
VkPresentInfoKHR presentInfo{};
presentInfo.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR;

presentInfo.waitSemaphoreCount = 1;
presentInfo.pWaitSemaphores = signalSemaphores;

VkSwapchainKHR swapChains[] = {swapChain};
presentInfo.swapchainCount = 1;
presentInfo.pSwapchains = swapChains;
presentInfo.pImageIndices = &imageIndex;

vkQueuePresentKHR(presentQueue, &presentInfo);
```

**동작:**

- `renderFinishedSemaphores[currentFrame]`이 `signaled`될 때까지 대기
- 렌더링 완료된 이미지를 화면에 표시

#### 단계 7: 프레임 인덱스 순환

```cpp
currentFrame = (currentFrame + 1) % MAX_FRAMES_IN_FLIGHT;
```

**동작:**

- 0 -> 1 -> 0 -> 1 -> ... (MAX_FRAMES_IN_FLIGHT = 2일 때)
- 다음 프레임을 위한 동기화 객체 세트 선택

---

## 4. 동기화 흐름 시각화

### 4.1. 프레임 0 (첫 프레임)

```plaintext
[CPU]
1. vkWaitForFences(inFlightFences[0])
   -> 초기 signaled이므로 즉시 통과

2. vkAcquireNextImageKHR(imageAvailableSemaphores[0])
   -> imageIndex = 0 획득

3. imagesInFlight[0] = VK_NULL_HANDLE
   -> 대기 없음
   -> imagesInFlight[0] = inFlightFences[0]

4. vkResetFences(inFlightFences[0])
   -> unsignaled로 변경

5. vkQueueSubmit(fence: inFlightFences[0])
   -> GPU 작업 시작

6. vkQueuePresentKHR()
   -> 프레젠테이션 요청

7. currentFrame = 1

[GPU]
- imageAvailableSemaphores[0] signaled -> 렌더링 시작
- 렌더링 완료 -> renderFinishedSemaphores[0] signaled
- 큐 완료 -> inFlightFences[0] signaled
- 화면 표시
```

### 4.2. 프레임 1 (두 번째 프레임)

```plaintext
[CPU]
1. vkWaitForFences(inFlightFences[1])
   -> 초기 signaled이므로 즉시 통과

2. vkAcquireNextImageKHR(imageAvailableSemaphores[1])
   -> imageIndex = 1 획득

3. imagesInFlight[1] = VK_NULL_HANDLE
   -> 대기 없음
   -> imagesInFlight[1] = inFlightFences[1]

4-7. 동일한 과정...

8. currentFrame = 0

[GPU]
- Frame 0과 Frame 1이 동시에 처리 가능!
```

### 4.3. 프레임 2 (세 번째 프레임)

```plaintext
[CPU]
1. vkWaitForFences(inFlightFences[0])
   -> Frame 0이 아직 완료되지 않았다면 대기!
   -> Frame 0 완료 후 통과

2. vkAcquireNextImageKHR(imageAvailableSemaphores[0])
   -> imageIndex = 2 (또는 0) 획득

3. imagesInFlight[imageIndex] 확인
   -> 해당 이미지가 사용 중이면 대기

[결과]
- 최대 2개 프레임만 동시에 GPU에서 처리
- CPU가 GPU보다 앞서가지 않음
- 자원 충돌 없이 안전하게 재사용
```

---

## 5. imagesInFlight의 필요성

### 5.1. 문제 상황

```plaintext
스왑체인 이미지: 3개 (인덱스 0, 1, 2)
MAX_FRAMES_IN_FLIGHT: 2

Frame 0: imageIndex = 0, inFlightFences[0]
Frame 1: imageIndex = 1, inFlightFences[1]
Frame 2: imageIndex = 2, inFlightFences[0]  // 펜스 0 재사용
Frame 3: imageIndex = 0, inFlightFences[1]  // 이미지 0 재사용!
```

**문제:**

- Frame 3에서 이미지 0을 사용하려고 함
- 하지만 Frame 0이 아직 이미지 0을 사용 중일 수 있음
- `inFlightFences[1]`은 Frame 1의 완료만 보장

### 5.2. 해결책

`imagesInFlight` 배열로 각 이미지의 실제 사용 상태를 추적:

```cpp
// 이미지 획득 후
if (imagesInFlight[imageIndex] != VK_NULL_HANDLE) {
    // 해당 이미지를 사용하던 프레임이 완료될 때까지 대기
    vkWaitForFences(device, 1, &imagesInFlight[imageIndex], VK_TRUE, UINT64_MAX);
}
// 현재 프레임의 펜스를 해당 이미지에 연결
imagesInFlight[imageIndex] = inFlightFences[currentFrame];
```

---

## 6. 자원 정리

```cpp
void cleanup() {
    for (size_t i = 0; i < MAX_FRAMES_IN_FLIGHT; i++) {
        vkDestroySemaphore(device, renderFinishedSemaphores[i], nullptr);
        vkDestroySemaphore(device, imageAvailableSemaphores[i], nullptr);
        vkDestroyFence(device, inFlightFences[i], nullptr);
    }
    // imagesInFlight는 펜스의 참조만 저장하므로 별도 정리 불필요
    
    // 나머지 자원 정리...
}
```

---

## 7. 성능 고려사항

### 7.1. MAX_FRAMES_IN_FLIGHT 값 선택

| 값 | 장점 | 단점 |
|----|------|------|
| 1 | 메모리 사용 최소 | GPU 활용도 낮음, 스톨 발생 |
| 2 | 균형 잡힌 성능 | 일반적으로 권장 |
| 3+ | GPU 파이프라인 최대 활용 | 메모리 사용 증가, 입력 지연 증가 |

### 7.2. 권장 사항

- 대부분의 경우 **2 또는 3**이 적절
- VSync 활성화 시 스왑체인 이미지 개수와 맞추는 것이 좋음
- 입력 지연에 민감한 게임은 낮은 값 선택

---

## 8. 핵심 정리

### 8.1. MAX_FRAMES_IN_FLIGHT 목적

1. CPU-GPU 병렬 처리 최적화
2. 자원 재사용 동기화
3. GPU 파이프라인 스톨 방지

### 8.2. 동기화 객체 역할

- **세마포어:** GPU 내부 작업 간 동기화
- **펜스:** CPU-GPU 간 동기화
- **imagesInFlight:** 스왑체인 이미지별 사용 상태 추적

### 8.3. 핵심 원칙

1. 펜스로 이전 프레임 완료 확인 후 자원 재사용
2. 세마포어로 GPU 작업 순서 보장
3. imagesInFlight로 이미지 충돌 방지

---

## 다음 단계

Frames in Flight 메커니즘을 이해했다면, 다음 단계로:

1. **Vertex Buffer:** 정점 데이터를 GPU 메모리로 전송
2. **Uniform Buffer:** 셰이더에 동적 데이터 전달
3. **Descriptor Sets:** 셰이더 리소스 바인딩

---

**다음 편:** [Vulkan] EP13. Vertex Buffer
