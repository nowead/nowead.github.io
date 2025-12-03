+++
date = '2025-09-20T09:30:00+09:00'
draft = false
title = '[Vulkan] EP10. Framebuffer와 Command Buffer'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Framebuffer", "Command Buffer", "Rendering"]
categories = ["그래픽스 프로그래밍"]
+++

## 시작하며

[EP09]에서 Graphics Pipeline을 생성했다. 이제 실제로 렌더링하기 위해 필요한 두 가지 핵심 요소를 다룬다:

1. **Framebuffer**: Render Pass와 Image View를 연결
2. **Command Buffer**: GPU 명령을 기록하고 제출

---

## 1. Framebuffer

### 1.1. Framebuffer란?

Framebuffer는 렌더링 결과가 기록될 실제 메모리 자원을 정의하는 객체다.

**Render Pass vs Framebuffer:**
- **Render Pass**: 렌더링 작업의 *구조* 정의 (어떤 종류의 어태치먼트가 사용될지)
- **Framebuffer**: 그 구조에 연결될 *구체적인 Image View*들 제공

### 1.2. Framebuffer가 필요한 이유

**실제 대상 지정:**
- Render Pass는 어태치먼트의 포맷과 용도를 명세
- Framebuffer는 실제 어떤 Image View가 그 어태치먼트에 해당할지 지정

**다중 렌더링 대상:**
- 하나의 Render Pass로 여러 Framebuffer에 렌더링 가능
- 예: 각 Swapchain 이미지마다 별도의 Framebuffer 생성

**오프스크린 렌더링:**
- 화면에 직접 표시되지 않는 텍스처에 렌더링 가능
- 예: Shadow Map, Post-processing 버퍼

### 1.3. VkFramebufferCreateInfo 구조체

```cpp
VkFramebufferCreateInfo framebufferInfo{};
framebufferInfo.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
framebufferInfo.renderPass = renderPass;          // 호환될 Render Pass
framebufferInfo.attachmentCount = 1;              // 어태치먼트 개수
framebufferInfo.pAttachments = attachments;       // Image View 배열
framebufferInfo.width = swapChainExtent.width;    // 프레임버퍼 너비
framebufferInfo.height = swapChainExtent.height;  // 프레임버퍼 높이
framebufferInfo.layers = 1;                       // 레이어 수
```

**주요 필드:**
- `renderPass`: 이 Framebuffer가 호환될 Render Pass
- `attachmentCount`: 어태치먼트 개수 (Render Pass의 어태치먼트 개수와 일치)
- `pAttachments`: `VkImageView` 배열 (Render Pass의 `VkAttachmentDescription` 순서와 일치)
- `width`, `height`: Framebuffer 크기 (모든 Image View와 일치해야 함)
- `layers`: 레이어 수 (Stereoscopic 렌더링 등에서 사용)

### 1.4. Swapchain Image View용 Framebuffer 생성

각 Swapchain 이미지마다 하나의 Framebuffer를 생성한다:

```cpp
std::vector<VkFramebuffer> swapChainFramebuffers;

void createFramebuffers() {
    swapChainFramebuffers.resize(swapChainImageViews.size());

    for (size_t i = 0; i < swapChainImageViews.size(); i++) {
        VkImageView attachments[] = {
            swapChainImageViews[i]  // 현재 Swapchain Image View
        };

        VkFramebufferCreateInfo framebufferInfo{};
        framebufferInfo.sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
        framebufferInfo.renderPass = renderPass;
        framebufferInfo.attachmentCount = 1;
        framebufferInfo.pAttachments = attachments;
        framebufferInfo.width = swapChainExtent.width;
        framebufferInfo.height = swapChainExtent.height;
        framebufferInfo.layers = 1;

        if (vkCreateFramebuffer(device, &framebufferInfo, nullptr,
                                &swapChainFramebuffers[i]) != VK_SUCCESS) {
            throw std::runtime_error("failed to create framebuffer!");
        }
    }
}
```

**순서 중요성:**
`pAttachments` 배열의 순서는 Render Pass의 `VkAttachmentDescription` 배열 순서와 정확히 일치해야 한다.

### 1.5. Framebuffer 정리

```cpp
void cleanup() {
    for (auto framebuffer : swapChainFramebuffers) {
        vkDestroyFramebuffer(device, framebuffer, nullptr);
    }
}
```

Swapchain 재생성 시 (윈도우 리사이즈 등) Framebuffer도 함께 재생성해야 한다.

---

## 2. Command Buffer

### 2.1. Command Buffer란?

GPU에게 명령을 내리는 유일한 방법이다. 모든 렌더링 및 컴퓨팅 명령을 Command Buffer에 기록하고, 이를 GPU Queue에 제출한다.

**역할:**
- **GPU 명령 캡슐화**: `vkCmdDraw`, `vkCmdBindPipeline` 등 모든 GPU 명령을 담음
- **비동기 실행**: CPU가 미리 기록하고, GPU는 나중에 비동기적으로 실행
- **재사용성**: 한 번 기록한 Command Buffer를 여러 번 제출 가능

### 2.2. Command Pool

Command Buffer는 `VkCommandPool`에서 할당된다. Command Pool은 효율적인 메모리 관리를 제공한다.

#### 2.2.1. Command Pool 생성

```cpp
VkCommandPool commandPool;

void createCommandPool() {
    QueueFamilyIndices queueFamilyIndices = findQueueFamilies(physicalDevice);

    VkCommandPoolCreateInfo poolInfo{};
    poolInfo.sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    poolInfo.queueFamilyIndex = queueFamilyIndices.graphicsFamily.value();
    poolInfo.flags = 0;  // Optional flags

    if (vkCreateCommandPool(device, &poolInfo, nullptr, &commandPool) != VK_SUCCESS) {
        throw std::runtime_error("failed to create command pool!");
    }
}
```

**주요 필드:**
- `queueFamilyIndex`: Command Buffer가 제출될 Queue Family 인덱스
- `flags`:
  - `VK_COMMAND_POOL_CREATE_TRANSIENT_BIT`: Command Buffer가 자주 리셋/재할당될 경우
  - `VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT`: 개별 Command Buffer 리셋 허용

#### 2.2.2. Command Pool 정리

```cpp
void cleanup() {
    vkDestroyCommandPool(device, commandPool, nullptr);
    // Pool이 소멸되면 할당된 모든 Command Buffer도 함께 소멸
}
```

### 2.3. Command Buffer 할당

```cpp
std::vector<VkCommandBuffer> commandBuffers;

void createCommandBuffers() {
    commandBuffers.resize(swapChainFramebuffers.size());

    VkCommandBufferAllocateInfo allocInfo{};
    allocInfo.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    allocInfo.commandPool = commandPool;
    allocInfo.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocInfo.commandBufferCount = (uint32_t)commandBuffers.size();

    if (vkAllocateCommandBuffers(device, &allocInfo, commandBuffers.data()) != VK_SUCCESS) {
        throw std::runtime_error("failed to allocate command buffers!");
    }
}
```

**Command Buffer Level:**
- `VK_COMMAND_BUFFER_LEVEL_PRIMARY`: Queue에 직접 제출 가능
- `VK_COMMAND_BUFFER_LEVEL_SECONDARY`: Primary Command Buffer에서만 호출 가능

### 2.4. Command Buffer 기록

Command Buffer 기록은 `vkBeginCommandBuffer`로 시작하여 `vkEndCommandBuffer`로 종료한다.

```cpp
void createCommandBuffers() {
    // ... 할당 코드 ...

    for (size_t i = 0; i < commandBuffers.size(); i++) {
        // 1. 기록 시작
        VkCommandBufferBeginInfo beginInfo{};
        beginInfo.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        beginInfo.flags = 0;  // Optional
        beginInfo.pInheritanceInfo = nullptr;  // Secondary command buffer용

        if (vkBeginCommandBuffer(commandBuffers[i], &beginInfo) != VK_SUCCESS) {
            throw std::runtime_error("failed to begin recording command buffer!");
        }

        // 2. Render Pass 시작
        VkRenderPassBeginInfo renderPassInfo{};
        renderPassInfo.sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
        renderPassInfo.renderPass = renderPass;
        renderPassInfo.framebuffer = swapChainFramebuffers[i];
        renderPassInfo.renderArea.offset = {0, 0};
        renderPassInfo.renderArea.extent = swapChainExtent;

        // Clear 값 설정 (배경색)
        VkClearValue clearColor = {{{0.0f, 0.0f, 0.0f, 1.0f}}};
        renderPassInfo.clearValueCount = 1;
        renderPassInfo.pClearValues = &clearColor;

        vkCmdBeginRenderPass(commandBuffers[i], &renderPassInfo, VK_SUBPASS_CONTENTS_INLINE);

        // 3. Pipeline 바인딩
        vkCmdBindPipeline(commandBuffers[i], VK_PIPELINE_BIND_POINT_GRAPHICS, graphicsPipeline);

        // 4. Draw 명령
        vkCmdDraw(commandBuffers[i], 3, 1, 0, 0);
        // 파라미터: vertexCount, instanceCount, firstVertex, firstInstance

        // 5. Render Pass 종료
        vkCmdEndRenderPass(commandBuffers[i]);

        // 6. 기록 종료
        if (vkEndCommandBuffer(commandBuffers[i]) != VK_SUCCESS) {
            throw std::runtime_error("failed to record command buffer!");
        }
    }
}
```

**VkCommandBufferBeginInfo flags:**
- `VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT`: 한 번만 제출
- `VK_COMMAND_BUFFER_USAGE_RENDER_PASS_CONTINUE_BIT`: Secondary command buffer용
- `VK_COMMAND_BUFFER_USAGE_SIMULTANEOUS_USE_BIT`: 여러 프레임에서 동시 사용

### 2.5. 주요 Command Buffer 명령들

**Render Pass:**
- `vkCmdBeginRenderPass` / `vkCmdEndRenderPass`: 렌더링 시작/종료
- `vkCmdNextSubpass`: 다음 서브패스로 이동

**Pipeline & Binding:**
- `vkCmdBindPipeline`: Graphics/Compute Pipeline 바인딩
- `vkCmdBindVertexBuffers`: Vertex Buffer 바인딩
- `vkCmdBindIndexBuffer`: Index Buffer 바인딩
- `vkCmdBindDescriptorSets`: Descriptor Set 바인딩

**Drawing:**
- `vkCmdDraw`: 정점 데이터로 그리기 (인덱스 없이)
- `vkCmdDrawIndexed`: Index Buffer로 그리기

**기타:**
- `vkCmdPipelineBarrier`: 메모리 장벽, 이미지 레이아웃 전환
- `vkCmdCopyBuffer`: 버퍼 복사

---

## 3. 렌더링 및 프레젠테이션

### 3.1. 동기화 객체

CPU와 GPU는 비동기적으로 작동한다. 동기화를 위해 **Semaphore**와 **Fence**를 사용한다.

#### 3.1.1. Semaphore (세마포어)

**역할**: GPU 내부에서 Queue 작업 간의 동기화

```cpp
VkSemaphore imageAvailableSemaphore;  // Swapchain 이미지 사용 가능 신호
VkSemaphore renderFinishedSemaphore;  // 렌더링 완료 신호

void createSemaphores() {
    VkSemaphoreCreateInfo semaphoreInfo{};
    semaphoreInfo.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;

    if (vkCreateSemaphore(device, &semaphoreInfo, nullptr, &imageAvailableSemaphore) != VK_SUCCESS ||
        vkCreateSemaphore(device, &semaphoreInfo, nullptr, &renderFinishedSemaphore) != VK_SUCCESS) {
        throw std::runtime_error("failed to create semaphores!");
    }
}
```

#### 3.1.2. Fence (펜스)

**역할**: CPU-GPU 간의 동기화 (CPU가 GPU 작업 완료를 대기)

```cpp
std::vector<VkFence> inFlightFences;
const int MAX_FRAMES_IN_FLIGHT = 2;

void createSyncObjects() {
    inFlightFences.resize(MAX_FRAMES_IN_FLIGHT);

    VkFenceCreateInfo fenceInfo{};
    fenceInfo.sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    fenceInfo.flags = VK_FENCE_CREATE_SIGNALED_BIT;  // 초기 signaled 상태

    for (size_t i = 0; i < MAX_FRAMES_IN_FLIGHT; i++) {
        if (vkCreateFence(device, &fenceInfo, nullptr, &inFlightFences[i]) != VK_SUCCESS) {
            throw std::runtime_error("failed to create fence!");
        }
    }
}
```

### 3.2. 렌더링 루프 (drawFrame)

```cpp
uint32_t currentFrame = 0;

void drawFrame() {
    // 1. CPU 대기: 이전 프레임 작업 완료 대기
    vkWaitForFences(device, 1, &inFlightFences[currentFrame], VK_TRUE, UINT64_MAX);
    vkResetFences(device, 1, &inFlightFences[currentFrame]);

    // 2. Swapchain에서 이미지 획득
    uint32_t imageIndex;
    vkAcquireNextImageKHR(device, swapChain, UINT64_MAX,
                          imageAvailableSemaphore, VK_NULL_HANDLE, &imageIndex);

    // 3. Command Buffer 제출
    VkSubmitInfo submitInfo{};
    submitInfo.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;

    VkSemaphore waitSemaphores[] = {imageAvailableSemaphore};
    VkPipelineStageFlags waitStages[] = {VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT};
    submitInfo.waitSemaphoreCount = 1;
    submitInfo.pWaitSemaphores = waitSemaphores;
    submitInfo.pWaitDstStageMask = waitStages;

    submitInfo.commandBufferCount = 1;
    submitInfo.pCommandBuffers = &commandBuffers[imageIndex];

    VkSemaphore signalSemaphores[] = {renderFinishedSemaphore};
    submitInfo.signalSemaphoreCount = 1;
    submitInfo.pSignalSemaphores = signalSemaphores;

    if (vkQueueSubmit(graphicsQueue, 1, &submitInfo, inFlightFences[currentFrame]) != VK_SUCCESS) {
        throw std::runtime_error("failed to submit draw command buffer!");
    }

    // 4. 화면에 제시 (Present)
    VkPresentInfoKHR presentInfo{};
    presentInfo.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR;
    presentInfo.waitSemaphoreCount = 1;
    presentInfo.pWaitSemaphores = signalSemaphores;

    VkSwapchainKHR swapChains[] = {swapChain};
    presentInfo.swapchainCount = 1;
    presentInfo.pSwapchains = swapChains;
    presentInfo.pImageIndices = &imageIndex;
    presentInfo.pResults = nullptr;  // Optional

    vkQueuePresentKHR(presentQueue, &presentInfo);

    // 5. 프레임 인덱스 업데이트
    currentFrame = (currentFrame + 1) % MAX_FRAMES_IN_FLIGHT;
}
```

**주요 단계:**

1. **CPU 대기**: `vkWaitForFences`로 이전 프레임 완료 대기
2. **이미지 획득**: `vkAcquireNextImageKHR`로 Swapchain 이미지 얻기
3. **제출**: `vkQueueSubmit`으로 Command Buffer 제출
4. **제시**: `vkQueuePresentKHR`로 화면에 표시
5. **프레임 업데이트**: 다음 프레임 인덱스로 이동

### 3.3. MAX_FRAMES_IN_FLIGHT

동시에 렌더링될 수 있는 최대 프레임 수를 제한한다.

**이유:**
- CPU가 GPU보다 빠르게 Command Buffer 제출 → GPU 과부하 방지
- 일반적으로 2 또는 3으로 설정

---

## 4. 초기화 순서

지금까지 생성한 객체들의 초기화 순서:

```cpp
void initVulkan() {
    createInstance();
    createSurface();
    pickPhysicalDevice();
    createLogicalDevice();
    createSwapChain();
    createImageViews();
    createRenderPass();
    createGraphicsPipeline();
    createFramebuffers();        // ← 새로 추가
    createCommandPool();         // ← 새로 추가
    createCommandBuffers();      // ← 새로 추가
    createSyncObjects();         // ← 새로 추가
}
```

---

## 5. 정리 순서

```cpp
void cleanup() {
    // 동기화 객체
    for (size_t i = 0; i < MAX_FRAMES_IN_FLIGHT; i++) {
        vkDestroySemaphore(device, renderFinishedSemaphores[i], nullptr);
        vkDestroySemaphore(device, imageAvailableSemaphores[i], nullptr);
        vkDestroyFence(device, inFlightFences[i], nullptr);
    }

    // Command Pool (Command Buffer는 자동 해제)
    vkDestroyCommandPool(device, commandPool, nullptr);

    // Framebuffer
    for (auto framebuffer : swapChainFramebuffers) {
        vkDestroyFramebuffer(device, framebuffer, nullptr);
    }

    // Pipeline & Render Pass
    vkDestroyPipeline(device, graphicsPipeline, nullptr);
    vkDestroyPipelineLayout(device, pipelineLayout, nullptr);
    vkDestroyRenderPass(device, renderPass, nullptr);

    // Swapchain
    for (auto imageView : swapChainImageViews) {
        vkDestroyImageView(device, imageView, nullptr);
    }
    vkDestroySwapchainKHR(device, swapChain, nullptr);

    // Device & Instance
    vkDestroyDevice(device, nullptr);
    vkDestroySurfaceKHR(instance, surface, nullptr);
    vkDestroyInstance(instance, nullptr);
}
```

**정리 순서**: Sync Objects → Command Pool → Framebuffer → Pipeline → Render Pass → Image Views → Swapchain → Device → Surface → Instance

---

## 6. 핵심 개념 정리

### 6.1. Framebuffer

- Render Pass의 어태치먼트와 실제 Image View를 연결
- 각 Swapchain 이미지마다 별도의 Framebuffer 생성
- Swapchain 재생성 시 함께 재생성 필요

### 6.2. Command Buffer

- GPU 명령을 기록하는 유일한 방법
- Command Pool에서 할당
- Primary/Secondary 레벨 구분
- 재사용 가능

### 6.3. 동기화

- **Semaphore**: GPU Queue 작업 간 동기화
- **Fence**: CPU-GPU 간 동기화
- **MAX_FRAMES_IN_FLIGHT**: 동시 렌더링 프레임 수 제한

---

## 7. 다음 단계

Framebuffer와 Command Buffer를 생성했다. 이제 실제로 삼각형을 그리기 위해 필요한 것:

1. **Vertex Shader**: 정점 데이터 처리
2. **Fragment Shader**: 픽셀 색상 계산
3. **실제 렌더링**: `drawFrame` 루프 실행

다음 편에서는 **Shader 작성과 첫 번째 삼각형 그리기**를 다룬다.

---

**다음 편**: [Vulkan] EP11. 동기화와 삼각형 그리기
