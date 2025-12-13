+++
date = '2025-09-25T16:31:15+09:00'
draft = false
title = '[Vulkan] EP11. Rendering과 Presentation'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Rendering", "Synchronization", "Semaphore", "Fence"]
categories = ["그래픽스 프로그래밍"]
+++

## 시작하며

[EP10]에서 Framebuffer와 Command Buffer를 생성했다. 이제 실제로 매 프레임 렌더링을 수행하고 화면에 결과를 표시할 차례다.

Vulkan의 렌더링 루프는 CPU와 GPU의 비동기 작업을 명시적으로 동기화해야 한다. **세마포어(Semaphore)**와 **펜스(Fence)**를 사용하여 프레임 간 의존성을 관리하고, 자원 충돌을 방지한다.

이 글에서는 렌더링 및 프레젠테이션의 전체 흐름, 동기화 메커니즘, 그리고 스왑체인 재생성을 다룬다.

---

## 1. 렌더링 파이프라인과 동기화

### 1.1. CPU와 GPU의 비동기 실행

Vulkan에서 CPU와 GPU는 **독립적으로 비동기 실행**된다:

**CPU**:
- 커맨드 버퍼에 명령 기록
- 큐에 커맨드 버퍼 제출
- 다음 프레임 준비

**GPU**:
- 제출된 커맨드 버퍼 실행
- 렌더링 수행
- 결과 이미지 생성

### 1.2. 동기화가 필요한 이유

동기화 없이는 다음과 같은 문제가 발생한다:

**1. 이미지 가용성 문제**:
- CPU가 아직 GPU에서 사용 중인 스왑체인 이미지를 재사용하려 시도
- 렌더링이 완료되지 않은 이미지를 화면에 표시

**2. 프레임 과부하**:
- CPU가 GPU보다 훨씬 빠르게 커맨드 버퍼를 제출
- GPU 큐가 과도하게 쌓여 메모리 부족 발생

**3. 자원 충돌**:
- GPU가 커맨드 버퍼를 실행 중인데 CPU가 해당 버퍼를 수정
- 예측 불가능한 동작 발생

### 1.3. Vulkan의 동기화 객체

Vulkan은 명시적 동기화를 위한 두 가지 주요 객체를 제공한다:

| 객체 | 동기화 대상 | 용도 |
|------|------------|------|
| **Semaphore** | GPU ↔ GPU | 큐 작업 간 동기화 |
| **Fence** | CPU ↔ GPU | CPU가 GPU 작업 완료 대기 |

---

## 2. 세마포어 (Semaphore)

### 2.1. 세마포어란?

세마포어는 **GPU 내부의 큐 작업 간 동기화**를 수행한다.

**특징**:
- CPU는 세마포어 상태를 직접 확인할 수 없음
- GPU 큐 간 신호(signal) 및 대기(wait) 전용
- 이진 세마포어: Unsignaled / Signaled 두 상태만 존재

### 2.2. 세마포어 동작 방식

**Wait Semaphore**:
```
vkQueueSubmit(..., waitSemaphores, ...)
→ 지정된 세마포어가 Signaled 될 때까지 큐 실행 대기
```

**Signal Semaphore**:
```
vkQueueSubmit(..., signalSemaphores, ...)
→ 큐 작업 완료 시 세마포어를 Signaled 상태로 변경
```

### 2.3. 세마포어 생성

```cpp
VkSemaphoreCreateInfo semaphoreInfo{};
semaphoreInfo.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;

VkSemaphore imageAvailableSemaphore;
VkSemaphore renderFinishedSemaphore;

if (vkCreateSemaphore(device, &semaphoreInfo, nullptr, &imageAvailableSemaphore) != VK_SUCCESS ||
    vkCreateSemaphore(device, &semaphoreInfo, nullptr, &renderFinishedSemaphore) != VK_SUCCESS) {
    throw std::runtime_error("failed to create semaphores!");
}
```

### 2.4. 렌더링에 사용되는 세마포어

**`imageAvailableSemaphore`**:
- 스왑체인에서 이미지를 획득했을 때 Signaled
- GPU가 해당 이미지에 렌더링 시작 가능

**`renderFinishedSemaphore`**:
- 렌더링 명령이 모두 완료되었을 때 Signaled
- 화면에 이미지 표시 가능

---

## 3. 펜스 (Fence)

### 3.1. 펜스란?

펜스는 **CPU와 GPU 간 동기화**를 수행한다.

**특징**:
- CPU가 펜스 상태를 확인하고 대기 가능
- GPU 작업 완료를 CPU에 알림
- 이진 펜스: Unsignaled / Signaled 두 상태

### 3.2. 펜스 vs 세마포어

| | Fence | Semaphore |
|---|-------|-----------|
| **동기화 대상** | CPU ↔ GPU | GPU ↔ GPU |
| **CPU 접근** | 가능 | 불가능 |
| **주요 용도** | CPU가 GPU 완료 대기 | 큐 간 의존성 관리 |

### 3.3. 펜스 생성

```cpp
VkFenceCreateInfo fenceInfo{};
fenceInfo.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
fenceInfo.flags = VK_FENCE_CREATE_SIGNALED_BIT;  // 초기 Signaled 상태

VkFence inFlightFence;

if (vkCreateFence(device, &fenceInfo, nullptr, &inFlightFence) != VK_SUCCESS) {
    throw std::runtime_error("failed to create fence!");
}
```

**`VK_FENCE_CREATE_SIGNALED_BIT`**:
- 첫 프레임에서 `vkWaitForFences`가 즉시 통과하도록 초기 Signaled 상태로 생성

### 3.4. 펜스 사용

**CPU에서 대기**:
```cpp
vkWaitForFences(device, 1, &inFlightFence, VK_TRUE, UINT64_MAX);
```

**펜스 리셋**:
```cpp
vkResetFences(device, 1, &inFlightFence);
```

**큐 제출 시 펜스 지정**:
```cpp
vkQueueSubmit(graphicsQueue, 1, &submitInfo, inFlightFence);
// GPU 작업 완료 시 inFlightFence가 Signaled 됨
```

---

## 4. Frames in Flight

### 4.1. MAX_FRAMES_IN_FLIGHT의 필요성

**문제**: CPU가 GPU보다 빠르게 프레임을 제출하면:
- GPU 큐가 무한정 쌓임
- 메모리 부족 및 지연 증가

**해결**: 동시에 GPU에서 처리 중인 프레임 수를 제한

```cpp
const int MAX_FRAMES_IN_FLIGHT = 2;  // 최대 2개 프레임 동시 처리
```

### 4.2. 프레임별 동기화 객체

각 프레임마다 독립적인 동기화 객체가 필요:

```cpp
std::vector<VkSemaphore> imageAvailableSemaphores;
std::vector<VkSemaphore> renderFinishedSemaphores;
std::vector<VkFence> inFlightFences;

// 스왑체인 이미지가 어떤 펜스에 의해 사용 중인지 추적
std::vector<VkFence> imagesInFlight;

uint32_t currentFrame = 0;  // 현재 프레임 인덱스
```

### 4.3. 동기화 객체 생성

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
    fenceInfo.flags = VK_FENCE_CREATE_SIGNALED_BIT;

    for (size_t i = 0; i < MAX_FRAMES_IN_FLIGHT; i++) {
        if (vkCreateSemaphore(device, &semaphoreInfo, nullptr, &imageAvailableSemaphores[i]) != VK_SUCCESS ||
            vkCreateSemaphore(device, &semaphoreInfo, nullptr, &renderFinishedSemaphores[i]) != VK_SUCCESS ||
            vkCreateFence(device, &fenceInfo, nullptr, &inFlightFences[i]) != VK_SUCCESS) {
            throw std::runtime_error("failed to create synchronization objects for a frame!");
        }
    }
}
```

---

## 5. drawFrame 함수 - 렌더링 루프

### 5.1. drawFrame 개요

매 프레임 호출되며 다음 단계를 수행:

1. CPU가 이전 프레임 완료 대기 (Fence)
2. 스왑체인에서 이미지 획득
3. 해당 이미지가 사용 중이면 대기
4. 커맨드 버퍼 제출 (렌더링)
5. 화면에 이미지 표시 (Present)

### 5.2. drawFrame 구현

```cpp
void drawFrame() {
    // 1. 현재 프레임의 이전 작업 완료 대기
    vkWaitForFences(device, 1, &inFlightFences[currentFrame], VK_TRUE, UINT64_MAX);

    // 2. 스왑체인에서 이미지 획득
    uint32_t imageIndex;
    VkResult result = vkAcquireNextImageKHR(device, swapChain, UINT64_MAX,
                                             imageAvailableSemaphores[currentFrame],
                                             VK_NULL_HANDLE, &imageIndex);

    if (result == VK_ERROR_OUT_OF_DATE_KHR) {
        recreateSwapChain();
        return;
    } else if (result != VK_SUCCESS && result != VK_SUBOPTIMAL_KHR) {
        throw std::runtime_error("failed to acquire swap chain image!");
    }

    // 3. 이미지가 아직 사용 중인지 확인
    if (imagesInFlight[imageIndex] != VK_NULL_HANDLE) {
        vkWaitForFences(device, 1, &imagesInFlight[imageIndex], VK_TRUE, UINT64_MAX);
    }
    imagesInFlight[imageIndex] = inFlightFences[currentFrame];

    // 4. 커맨드 버퍼 제출
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

    vkResetFences(device, 1, &inFlightFences[currentFrame]);

    if (vkQueueSubmit(graphicsQueue, 1, &submitInfo, inFlightFences[currentFrame]) != VK_SUCCESS) {
        throw std::runtime_error("failed to submit draw command buffer!");
    }

    // 5. 화면에 표시
    VkPresentInfoKHR presentInfo{};
    presentInfo.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR;

    presentInfo.waitSemaphoreCount = 1;
    presentInfo.pWaitSemaphores = signalSemaphores;

    VkSwapchainKHR swapChains[] = {swapChain};
    presentInfo.swapchainCount = 1;
    presentInfo.pSwapchains = swapChains;
    presentInfo.pImageIndices = &imageIndex;

    result = vkQueuePresentKHR(presentQueue, &presentInfo);

    if (result == VK_ERROR_OUT_OF_DATE_KHR || result == VK_SUBOPTIMAL_KHR || framebufferResized) {
        framebufferResized = false;
        recreateSwapChain();
    } else if (result != VK_SUCCESS) {
        throw std::runtime_error("failed to present swap chain image!");
    }

    // 6. 다음 프레임으로 이동
    currentFrame = (currentFrame + 1) % MAX_FRAMES_IN_FLIGHT;
}
```

### 5.3. 단계별 상세 설명

#### 1단계: CPU 대기

```cpp
vkWaitForFences(device, 1, &inFlightFences[currentFrame], VK_TRUE, UINT64_MAX);
```

- `currentFrame` 인덱스에 해당하는 펜스가 Signaled 될 때까지 CPU 블록
- 이전에 이 프레임 슬롯을 사용한 GPU 작업이 완료되었음을 보장
- 안전하게 커맨드 버퍼 및 자원 재사용 가능

#### 2단계: 이미지 획득

```cpp
vkAcquireNextImageKHR(device, swapChain, UINT64_MAX,
                      imageAvailableSemaphores[currentFrame],
                      VK_NULL_HANDLE, &imageIndex);
```

- 스왑체인에서 다음 렌더링 대상 이미지 인덱스 획득
- `imageAvailableSemaphores[currentFrame]`를 Signaled 상태로 변경
- 타임아웃: `UINT64_MAX` (무한 대기)

**반환값**:
- `VK_SUCCESS`: 정상
- `VK_ERROR_OUT_OF_DATE_KHR`: 스왑체인 무효화 (재생성 필요)
- `VK_SUBOPTIMAL_KHR`: 사용 가능하지만 최적이 아님

#### 3단계: 이미지 사용 확인

```cpp
if (imagesInFlight[imageIndex] != VK_NULL_HANDLE) {
    vkWaitForFences(device, 1, &imagesInFlight[imageIndex], VK_TRUE, UINT64_MAX);
}
imagesInFlight[imageIndex] = inFlightFences[currentFrame];
```

- 획득한 이미지가 아직 다른 프레임에서 사용 중이면 대기
- 현재 프레임의 펜스를 해당 이미지에 할당

#### 4단계: 커맨드 버퍼 제출

```cpp
VkSubmitInfo submitInfo{};
submitInfo.waitSemaphoreCount = 1;
submitInfo.pWaitSemaphores = waitSemaphores;  // imageAvailableSemaphores
submitInfo.pWaitDstStageMask = waitStages;    // COLOR_ATTACHMENT_OUTPUT

submitInfo.commandBufferCount = 1;
submitInfo.pCommandBuffers = &commandBuffers[imageIndex];

submitInfo.signalSemaphoreCount = 1;
submitInfo.pSignalSemaphores = signalSemaphores;  // renderFinishedSemaphores

vkResetFences(device, 1, &inFlightFences[currentFrame]);
vkQueueSubmit(graphicsQueue, 1, &submitInfo, inFlightFences[currentFrame]);
```

**waitSemaphores**:
- `imageAvailableSemaphores[currentFrame]`가 Signaled 될 때까지 대기

**waitDstStageMask**:
- `VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT`
- 컬러 어태치먼트 출력 단계에서 대기

**signalSemaphores**:
- 렌더링 완료 시 `renderFinishedSemaphores[currentFrame]` Signaled

**fence**:
- 큐 제출 완료 시 `inFlightFences[currentFrame]` Signaled

#### 5단계: 화면 표시

```cpp
VkPresentInfoKHR presentInfo{};
presentInfo.waitSemaphoreCount = 1;
presentInfo.pWaitSemaphores = signalSemaphores;  // renderFinishedSemaphores

presentInfo.swapchainCount = 1;
presentInfo.pSwapchains = swapChains;
presentInfo.pImageIndices = &imageIndex;

vkQueuePresentKHR(presentQueue, &presentInfo);
```

- `renderFinishedSemaphores[currentFrame]`가 Signaled 될 때까지 대기
- 렌더링 완료된 이미지를 화면에 표시

#### 6단계: 프레임 인덱스 업데이트

```cpp
currentFrame = (currentFrame + 1) % MAX_FRAMES_IN_FLIGHT;
```

- 다음 프레임을 위한 인덱스 순환

---

## 6. 스왑체인 재생성

### 6.1. 재생성이 필요한 경우

**창 크기 변경**:
- 사용자가 창 크기 조정
- 스왑체인 이미지 크기가 더 이상 맞지 않음

**화면 속성 변경**:
- 해상도, 방향, 전체 화면/창 모드 전환

**Vulkan 에러 코드**:
- `VK_ERROR_OUT_OF_DATE_KHR`: 스왑체인 완전히 무효화
- `VK_SUBOPTIMAL_KHR`: 사용 가능하지만 최적이 아님

### 6.2. 창 크기 변경 감지

```cpp
bool framebufferResized = false;

static void framebufferResizeCallback(GLFWwindow* window, int width, int height) {
    auto app = reinterpret_cast<HelloTriangleApplication*>(glfwGetWindowUserPointer(window));
    app->framebufferResized = true;
}

void initWindow() {
    // ...
    glfwSetFramebufferSizeCallback(window, framebufferResizeCallback);
}
```

### 6.3. recreateSwapChain 함수

```cpp
void recreateSwapChain() {
    // 창 최소화 처리
    int width = 0, height = 0;
    glfwGetFramebufferSize(window, &width, &height);
    while (width == 0 || height == 0) {
        glfwGetFramebufferSize(window, &width, &height);
        glfwWaitEvents();
    }

    // GPU 작업 완료 대기
    vkDeviceWaitIdle(device);

    // 기존 자원 정리
    cleanupSwapChain();

    // 스왑체인 재생성
    createSwapChain();
    createImageViews();
    createRenderPass();
    createGraphicsPipeline();
    createFramebuffers();
    createCommandBuffers();
}
```

### 6.4. cleanupSwapChain 함수

```cpp
void cleanupSwapChain() {
    for (auto framebuffer : swapChainFramebuffers) {
        vkDestroyFramebuffer(device, framebuffer, nullptr);
    }

    vkFreeCommandBuffers(device, commandPool,
                         static_cast<uint32_t>(commandBuffers.size()),
                         commandBuffers.data());

    vkDestroyPipeline(device, graphicsPipeline, nullptr);
    vkDestroyPipelineLayout(device, pipelineLayout, nullptr);
    vkDestroyRenderPass(device, renderPass, nullptr);

    for (auto imageView : swapChainImageViews) {
        vkDestroyImageView(device, imageView, nullptr);
    }

    vkDestroySwapchainKHR(device, swapChain, nullptr);
}
```

**정리 순서**:
1. Framebuffer
2. Command Buffers
3. Graphics Pipeline
4. Pipeline Layout
5. Render Pass
6. Image Views
7. Swapchain

### 6.5. 창 최소화 처리

```cpp
int width = 0, height = 0;
glfwGetFramebufferSize(window, &width, &height);
while (width == 0 || height == 0) {
    glfwGetFramebufferSize(window, &width, &height);
    glfwWaitEvents();
}
```

- 창이 최소화되면 크기가 0이 됨
- 유효한 크기가 될 때까지 대기

---

## 7. 메인 루프

### 7.1. 렌더링 루프 구현

```cpp
void mainLoop() {
    while (!glfwWindowShouldClose(window)) {
        glfwPollEvents();
        drawFrame();
    }

    vkDeviceWaitIdle(device);
}
```

**`vkDeviceWaitIdle`**:
- 종료 전 모든 GPU 작업 완료 대기
- 사용 중인 자원을 안전하게 정리

### 7.2. 전체 초기화 흐름

```cpp
void run() {
    initWindow();
    initVulkan();
    mainLoop();
    cleanup();
}

void initVulkan() {
    createInstance();
    createSurface();
    pickPhysicalDevice();
    createLogicalDevice();
    createSwapChain();
    createImageViews();
    createRenderPass();
    createGraphicsPipeline();
    createFramebuffers();
    createCommandPool();
    createCommandBuffers();
    createSyncObjects();  // 동기화 객체 생성
}
```

---

## 8. 자원 정리

### 8.1. cleanup 함수

```cpp
void cleanup() {
    cleanupSwapChain();

    for (size_t i = 0; i < MAX_FRAMES_IN_FLIGHT; i++) {
        vkDestroySemaphore(device, renderFinishedSemaphores[i], nullptr);
        vkDestroySemaphore(device, imageAvailableSemaphores[i], nullptr);
        vkDestroyFence(device, inFlightFences[i], nullptr);
    }

    vkDestroyCommandPool(device, commandPool, nullptr);

    vkDestroyDevice(device, nullptr);
    vkDestroySurfaceKHR(instance, surface, nullptr);
    vkDestroyInstance(instance, nullptr);

    glfwDestroyWindow(window);
    glfwTerminate();
}
```

**정리 순서**:
1. Swapchain 관련 자원
2. 동기화 객체 (Semaphores, Fences)
3. Command Pool
4. Logical Device
5. Surface
6. Instance
7. GLFW Window

---

## 9. 동기화 흐름 정리

### 9.1. 프레임 0의 흐름

```
[CPU - Frame 0]
1. vkWaitForFences(inFlightFences[0])      → 초기 Signaled이므로 즉시 통과
2. vkResetFences(inFlightFences[0])        → Unsignaled로 변경
3. vkAcquireNextImageKHR(...)              → imageAvailableSemaphores[0] Signal
4. vkQueueSubmit(...)
   - Wait: imageAvailableSemaphores[0]
   - Signal: renderFinishedSemaphores[0]
   - Fence: inFlightFences[0]
5. vkQueuePresentKHR(...)
   - Wait: renderFinishedSemaphores[0]

[GPU - Frame 0]
- imageAvailableSemaphores[0] Signaled → 렌더링 시작
- 렌더링 완료 → renderFinishedSemaphores[0] Signal
- 큐 제출 완료 → inFlightFences[0] Signal
- renderFinishedSemaphores[0] Signaled → 화면 표시
```

### 9.2. 프레임 1의 흐름

```
[CPU - Frame 1]
1. currentFrame = 1
2. vkWaitForFences(inFlightFences[1])      → 초기 Signaled이므로 즉시 통과
3. Frame 0과 동일한 과정 반복

[GPU]
- Frame 0과 Frame 1이 동시에 처리 가능 (MAX_FRAMES_IN_FLIGHT = 2)
```

### 9.3. 프레임 2의 흐름

```
[CPU - Frame 2]
1. currentFrame = 0 (2 % 2 = 0)
2. vkWaitForFences(inFlightFences[0])      → Frame 0 완료 대기
3. Frame 0의 자원 재사용

[결과]
- 최대 2개 프레임만 동시에 GPU에서 처리
- CPU가 GPU보다 앞서가지 않음
```

---

## 10. 핵심 개념 정리

### 10.1. 세마포어 (Semaphore)

- GPU 큐 간 동기화
- CPU 접근 불가
- `imageAvailable` / `renderFinished`

### 10.2. 펜스 (Fence)

- CPU ↔ GPU 동기화
- CPU가 GPU 완료 대기
- `inFlightFences`

### 10.3. MAX_FRAMES_IN_FLIGHT

- 동시 처리 프레임 수 제한 (보통 2-3)
- CPU/GPU 과부하 방지
- 프레임별 독립적인 동기화 객체

### 10.4. drawFrame 단계

1. CPU 대기 (Fence)
2. 이미지 획득 (Acquire)
3. 커맨드 제출 (Submit)
4. 화면 표시 (Present)
5. 프레임 인덱스 순환

### 10.5. 스왑체인 재생성

- 창 크기 변경 감지
- GPU 작업 완료 대기
- 기존 자원 정리 → 재생성

---

## 11. 자주 발생하는 문제

### 11.1. 검은 화면만 보임

**원인**: 동기화 객체 미사용

**해결**:
```cpp
// 반드시 세마포어와 펜스를 vkQueueSubmit/Present에 전달
vkQueueSubmit(..., waitSemaphores, signalSemaphores, fence);
vkQueuePresentKHR(..., waitSemaphores);
```

### 11.2. 프레임 간 깜빡임

**원인**: `imagesInFlight` 추적 누락

**해결**:
```cpp
if (imagesInFlight[imageIndex] != VK_NULL_HANDLE) {
    vkWaitForFences(device, 1, &imagesInFlight[imageIndex], VK_TRUE, UINT64_MAX);
}
imagesInFlight[imageIndex] = inFlightFences[currentFrame];
```

### 11.3. 창 크기 변경 시 크래시

**원인**: 스왑체인 재생성 누락

**해결**:
```cpp
if (result == VK_ERROR_OUT_OF_DATE_KHR || result == VK_SUBOPTIMAL_KHR) {
    recreateSwapChain();
    return;
}
```

### 11.4. 종료 시 Validation Error

**원인**: 사용 중인 자원 정리

**해결**:
```cpp
void cleanup() {
    vkDeviceWaitIdle(device);  // 모든 GPU 작업 완료 대기
    // 자원 정리...
}
```

---

## 12. 다음 단계

이제 기본적인 렌더링 루프가 완성되었다. 다음 단계:

1. **Vertex Buffer**: 정점 데이터를 GPU 메모리로 전송
2. **Uniform Buffer**: 셰이더에 동적 데이터 전달
3. **Texture Mapping**: 이미지를 모델에 적용
4. **Depth Buffer**: 깊이 테스트 활성화

다음 편에서는 **Vertex Buffer**를 생성하여 실제 3D 모델 데이터를 렌더링한다.

---

**다음 편**: [Vulkan] EP12. Vertex Buffer
