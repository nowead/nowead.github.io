+++
date = '2025-09-27T10:00:00+09:00'
draft = false
title = '[Vulkan] EP13. 스왑체인 재생성'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Swapchain", "Window Resize", "Recreation"]
categories = ["그래픽스 프로그래밍"]
summary = "창 크기 변경 등의 이벤트에 대응하여 스왑체인과 관련 자원을 재생성하는 방법을 다룹니다."
+++

## 시작하며

[EP12](EP12_FRAMES_IN_FLIGHT.md)에서 Frames in Flight 개념을 통해 CPU-GPU 병렬 처리를 최적화했다. 이번 편에서는 **스왑체인 재생성**(Swapchain Recreation)을 다룬다.

Vulkan 애플리케이션에서 스왑체인은 화면에 이미지를 제시하는 데 핵심적인 역할을 한다. 하지만 창 크기 변경, 화면 회전, 모니터 해상도 변경 등 다양한 이유로 인해 기존 스왑체인이 더 이상 유효하지 않거나 최적화되지 않을 수 있다. 이 경우 스왑체인을 재생성해야 하며, 이 과정은 Vulkan 프로그래밍에서 중요한 부분을 차지한다.

---

## 1. 스왑체인 재생성의 필요성

### 1.1. 재생성이 필요한 시나리오

**창 크기 변경:**

- 가장 흔한 경우
- 사용자가 애플리케이션 창의 크기를 변경
- 스왑체인 이미지들도 새 크기에 맞게 조정 필요

**화면 회전:**

- 모바일 기기 등에서 화면 회전 시 발생
- 뷰포트와 렌더링 영역이 변경됨

**디스플레이 설정 변경:**

- 모니터 해상도 변경
- 새로고침 빈도 변경
- 전체 화면/창 모드 전환

### 1.2. Vulkan 에러 코드

`vkAcquireNextImageKHR` 또는 `vkQueuePresentKHR` 호출 시 다음 코드가 반환될 수 있다:

| 반환 코드 | 의미 | 대응 |
|-----------|------|------|
| `VK_ERROR_OUT_OF_DATE_KHR` | 스왑체인 완전 무효화 | 즉시 재생성 필수 |
| `VK_SUBOPTIMAL_KHR` | 사용 가능하나 최적 아님 | 재생성 권장 |

```cpp
VkResult result = vkAcquireNextImageKHR(device, swapChain, UINT64_MAX,
                                         imageAvailableSemaphore,
                                         VK_NULL_HANDLE, &imageIndex);

if (result == VK_ERROR_OUT_OF_DATE_KHR) {
    recreateSwapChain();
    return;
} else if (result != VK_SUCCESS && result != VK_SUBOPTIMAL_KHR) {
    throw std::runtime_error("failed to acquire swap chain image!");
}
```

---

## 2. 재생성 대상 객체

스왑체인 재생성은 단순히 `VkSwapchainKHR` 객체만 새로 만드는 것이 아니다. 스왑체인은 여러 다른 Vulkan 객체들과 밀접하게 연관되어 있다.

### 2.1. 의존성 체인

```plaintext
Swapchain
    |
    +-- Swapchain Images (자동 생성/소멸)
    |       |
    |       +-- Image Views
    |               |
    |               +-- Framebuffers
    |                       |
    |                       +-- Command Buffers (참조)
    |
    +-- Render Pass (포맷 의존)
    |       |
    |       +-- Graphics Pipeline (renderPass 불변)
    |               |
    |               +-- Pipeline Layout
```

### 2.2. 재생성 대상 목록

| 객체 | 재생성 필요 | 이유 |
|------|-------------|------|
| **Swapchain** | O | 근본 원인 |
| **Image Views** | O | 새 스왑체인 이미지에 맞춤 |
| **Render Pass** | O | 포맷/샘플 수 변경 가능 |
| **Graphics Pipeline** | O | renderPass가 불변 |
| **Pipeline Layout** | O | 파이프라인과 함께 재생성 |
| **Framebuffers** | O | 새 이미지 뷰/렌더 패스에 맞춤 |
| **Command Buffers** | O | 모든 참조가 변경됨 |

---

## 3. cleanupSwapChain 함수

재생성 전에 기존 자원을 정리해야 한다.

### 3.1. 구현

```cpp
void cleanupSwapChain() {
    // 1. 프레임버퍼 소멸
    for (auto framebuffer : swapChainFramebuffers) {
        vkDestroyFramebuffer(device, framebuffer, nullptr);
    }

    // 2. 커맨드 버퍼 해제
    vkFreeCommandBuffers(device, commandPool,
                         static_cast<uint32_t>(commandBuffers.size()),
                         commandBuffers.data());

    // 3. 그래픽스 파이프라인 소멸
    vkDestroyPipeline(device, graphicsPipeline, nullptr);

    // 4. 파이프라인 레이아웃 소멸
    vkDestroyPipelineLayout(device, pipelineLayout, nullptr);

    // 5. 렌더 패스 소멸
    vkDestroyRenderPass(device, renderPass, nullptr);

    // 6. 이미지 뷰 소멸
    for (auto imageView : swapChainImageViews) {
        vkDestroyImageView(device, imageView, nullptr);
    }

    // 7. 스왑체인 소멸
    vkDestroySwapchainKHR(device, swapChain, nullptr);
}
```

### 3.2. 소멸 순서

소멸 순서는 생성 순서의 역순이어야 한다:

```plaintext
[소멸 순서]
1. Framebuffers      (Image Views, Render Pass 참조)
2. Command Buffers   (Framebuffers, Pipeline 참조)
3. Graphics Pipeline (Render Pass 참조)
4. Pipeline Layout   (Pipeline 참조)
5. Render Pass       (Framebuffers에서 참조됨)
6. Image Views       (Swapchain Images 참조)
7. Swapchain         (최하위 의존성)
```

---

## 4. recreateSwapChain 함수

### 4.1. 전체 구현

```cpp
void recreateSwapChain() {
    // 1. 최소화된 창 처리
    int width = 0, height = 0;
    glfwGetFramebufferSize(window, &width, &height);
    while (width == 0 || height == 0) {
        glfwGetFramebufferSize(window, &width, &height);
        glfwWaitEvents();
    }

    // 2. GPU 작업 완료 대기
    vkDeviceWaitIdle(device);

    // 3. 기존 자원 정리
    cleanupSwapChain();

    // 4. 스왑체인 관련 객체 재생성
    createSwapChain();
    createImageViews();
    createRenderPass();
    createGraphicsPipeline();
    createFramebuffers();
    createCommandBuffers();
}
```

### 4.2. 단계별 설명

#### 단계 1: 최소화된 창 처리

```cpp
int width = 0, height = 0;
glfwGetFramebufferSize(window, &width, &height);
while (width == 0 || height == 0) {
    glfwGetFramebufferSize(window, &width, &height);
    glfwWaitEvents();
}
```

**목적:**

- 창이 최소화되면 프레임버퍼 크기가 0이 됨
- 크기가 0인 스왑체인은 생성할 수 없음
- 유효한 크기가 될 때까지 대기

**동작:**

- `glfwGetFramebufferSize`로 현재 창 크기 확인
- 크기가 0이면 `glfwWaitEvents`로 이벤트 대기
- 창이 복원될 때까지 루프 반복

#### 단계 2: GPU 작업 완료 대기

```cpp
vkDeviceWaitIdle(device);
```

**목적:**

- 현재 GPU가 실행 중인 모든 작업 완료 대기
- 기존 자원이 GPU에서 사용 중인 상태에서 해제되지 않도록 보장

**주의:**

- 이 호출은 성능에 영향을 줄 수 있음
- 더 세밀한 동기화를 원하면 펜스 사용 고려

#### 단계 3: 기존 자원 정리

```cpp
cleanupSwapChain();
```

**동작:**

- 이전 섹션에서 설명한 `cleanupSwapChain` 함수 호출
- 모든 스왑체인 의존 객체 소멸

#### 단계 4: 스왑체인 관련 객체 재생성

```cpp
createSwapChain();
createImageViews();
createRenderPass();
createGraphicsPipeline();
createFramebuffers();
createCommandBuffers();
```

**생성 순서:**

```plaintext
[생성 순서]
1. Swapchain         -> 새 크기로 생성
2. Image Views       -> 새 스왑체인 이미지에 맞춤
3. Render Pass       -> 새 포맷에 맞춤 (보통 동일)
4. Graphics Pipeline -> 새 렌더 패스 참조
5. Framebuffers      -> 새 이미지 뷰 + 렌더 패스 참조
6. Command Buffers   -> 새 프레임버퍼 + 파이프라인 참조
```

---

## 5. 창 크기 변경 감지

### 5.1. 콜백 설정

GLFW를 사용하여 창 크기 변경을 감지한다:

```cpp
bool framebufferResized = false;

static void framebufferResizeCallback(GLFWwindow* window, int width, int height) {
    auto app = reinterpret_cast<HelloTriangleApplication*>(
        glfwGetWindowUserPointer(window));
    app->framebufferResized = true;
}

void initWindow() {
    glfwInit();
    glfwWindowHint(GLFW_CLIENT_API, GLFW_NO_API);
    
    window = glfwCreateWindow(WIDTH, HEIGHT, "Vulkan", nullptr, nullptr);
    
    glfwSetWindowUserPointer(window, this);
    glfwSetFramebufferSizeCallback(window, framebufferResizeCallback);
}
```

### 5.2. 플래그 사용 이유

**왜 콜백에서 직접 재생성하지 않는가:**

- 콜백은 메인 스레드에서 호출되지 않을 수 있음
- Vulkan 함수는 스레드 안전성을 보장하지 않음
- 렌더링 루프 중간에 재생성하면 상태 불일치 발생 가능

**플래그 방식:**

- 콜백에서는 플래그만 설정
- 렌더링 루프에서 플래그를 확인하고 재생성

---

## 6. drawFrame에서 재생성 처리

### 6.1. 이미지 획득 시

```cpp
uint32_t imageIndex;
VkResult result = vkAcquireNextImageKHR(device, swapChain, UINT64_MAX,
                                         imageAvailableSemaphores[currentFrame],
                                         VK_NULL_HANDLE, &imageIndex);

if (result == VK_ERROR_OUT_OF_DATE_KHR) {
    recreateSwapChain();
    return;  // 이번 프레임은 스킵
} else if (result != VK_SUCCESS && result != VK_SUBOPTIMAL_KHR) {
    throw std::runtime_error("failed to acquire swap chain image!");
}
```

**처리 로직:**

- `VK_ERROR_OUT_OF_DATE_KHR`: 즉시 재생성 후 리턴
- `VK_SUBOPTIMAL_KHR`: 계속 진행 (프레젠테이션에서 처리)
- 기타 에러: 예외 발생

### 6.2. 프레젠테이션 시

```cpp
result = vkQueuePresentKHR(presentQueue, &presentInfo);

if (result == VK_ERROR_OUT_OF_DATE_KHR || 
    result == VK_SUBOPTIMAL_KHR || 
    framebufferResized) {
    framebufferResized = false;
    recreateSwapChain();
} else if (result != VK_SUCCESS) {
    throw std::runtime_error("failed to present swap chain image!");
}
```

**처리 로직:**

- `VK_ERROR_OUT_OF_DATE_KHR`: 재생성 필요
- `VK_SUBOPTIMAL_KHR`: 재생성 권장
- `framebufferResized`: 콜백에서 감지한 크기 변경

**주의:**

- `VK_SUBOPTIMAL_KHR`은 `vkAcquireNextImageKHR`에서도 반환될 수 있음
- 프레젠테이션까지 완료한 후 재생성하는 것이 일반적

---

## 7. 전체 흐름

```plaintext
[렌더링 루프]
    |
    v
vkAcquireNextImageKHR()
    |
    +-- VK_ERROR_OUT_OF_DATE_KHR --> recreateSwapChain() --> return
    |
    v
[렌더링 수행]
    |
    v
vkQueuePresentKHR()
    |
    +-- VK_ERROR_OUT_OF_DATE_KHR
    |   VK_SUBOPTIMAL_KHR        --> recreateSwapChain()
    |   framebufferResized
    |
    v
[다음 프레임]


[recreateSwapChain]
    |
    v
창 최소화 확인 (크기 0이면 대기)
    |
    v
vkDeviceWaitIdle()
    |
    v
cleanupSwapChain()
    |
    v
createSwapChain()
createImageViews()
createRenderPass()
createGraphicsPipeline()
createFramebuffers()
createCommandBuffers()
    |
    v
[완료]
```

---

## 8. 최적화 고려사항

### 8.1. oldSwapchain 활용

```cpp
VkSwapchainCreateInfoKHR createInfo{};
// ... 설정 ...
createInfo.oldSwapchain = oldSwapChain;  // 기존 스왑체인 힌트

vkCreateSwapchainKHR(device, &createInfo, nullptr, &swapChain);

// 이후 기존 스왑체인 소멸
vkDestroySwapchainKHR(device, oldSwapChain, nullptr);
```

**장점:**

- 드라이버가 리소스를 재활용할 수 있음
- 전환이 더 부드러워질 수 있음

### 8.2. 동적 상태 활용

뷰포트와 시저를 동적 상태로 설정하면 파이프라인 재생성을 피할 수 있다:

```cpp
// 파이프라인 생성 시
std::vector<VkDynamicState> dynamicStates = {
    VK_DYNAMIC_STATE_VIEWPORT,
    VK_DYNAMIC_STATE_SCISSOR
};

VkPipelineDynamicStateCreateInfo dynamicState{};
dynamicState.sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO;
dynamicState.dynamicStateCount = static_cast<uint32_t>(dynamicStates.size());
dynamicState.pDynamicStates = dynamicStates.data();

// 렌더링 시
vkCmdSetViewport(commandBuffer, 0, 1, &viewport);
vkCmdSetScissor(commandBuffer, 0, 1, &scissor);
```

### 8.3. 렌더 패스 호환성

포맷이 동일하면 렌더 패스를 재생성하지 않아도 된다:

```cpp
void recreateSwapChain() {
    // ...
    
    VkFormat oldFormat = swapChainImageFormat;
    
    createSwapChain();
    createImageViews();
    
    // 포맷이 변경된 경우에만 렌더 패스 재생성
    if (swapChainImageFormat != oldFormat) {
        createRenderPass();
        createGraphicsPipeline();
    }
    
    createFramebuffers();
    createCommandBuffers();
}
```

---

## 9. 핵심 정리

### 9.1. 재생성 트리거

- `VK_ERROR_OUT_OF_DATE_KHR` 반환
- `VK_SUBOPTIMAL_KHR` 반환
- `framebufferResized` 플래그

### 9.2. 재생성 순서

```plaintext
1. 창 최소화 처리
2. GPU 작업 완료 대기
3. 기존 자원 정리 (역순)
4. 새 자원 생성 (정순)
```

### 9.3. 재생성 대상

- Swapchain
- Image Views
- Render Pass (선택적)
- Graphics Pipeline
- Framebuffers
- Command Buffers

---

## 10. 자주 발생하는 문제

### 10.1. 최소화 시 크래시

**원인:** 크기 0인 스왑체인 생성 시도

**해결:**

```cpp
while (width == 0 || height == 0) {
    glfwGetFramebufferSize(window, &width, &height);
    glfwWaitEvents();
}
```

### 10.2. 재생성 후 검은 화면

**원인:** 커맨드 버퍼 재기록 누락

**해결:** `createCommandBuffers()` 호출 확인

### 10.3. Validation 에러

**원인:** GPU 작업 완료 전 자원 소멸

**해결:** `vkDeviceWaitIdle()` 호출 확인

---

## 다음 단계

스왑체인 재생성을 이해했다면, 다음 단계로:

1. **Vertex Buffer:** 정점 데이터를 GPU 메모리로 전송
2. **Index Buffer:** 정점 재사용을 통한 효율적인 렌더링
3. **Uniform Buffer:** 셰이더에 동적 데이터 전달

---

**다음 편:** [Vulkan] EP14. Vertex Buffer
