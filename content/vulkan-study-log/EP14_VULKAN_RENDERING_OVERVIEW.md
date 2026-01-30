+++
date = '2025-09-28T10:00:00+09:00'
draft = false
title = '[Vulkan] EP14. Vulkan 렌더링 전체 흐름 정리'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Rendering", "Overview", "Summary"]
categories = ["그래픽스 프로그래밍"]
summary = "Vulkan 렌더링의 전체 흐름을 단계별로 정리합니다. Surface부터 렌더링 루프까지 모든 과정을 요약합니다."
+++

## 시작하며

[EP13](EP13_SWAPCHAIN_RECREATION.md)까지 Vulkan의 렌더링 파이프라인 구성 요소들을 하나씩 살펴보았다. 이번 편에서는 지금까지 배운 내용을 전체적으로 정리하고, Vulkan 렌더링의 큰 그림을 조망한다.

---

## 중간 정리: 핵심 객체 관계

### Surface와 Swapchain

하나의 **Surface**에는 하나의 **Swapchain**만 연결된다.

### Swapchain과 VkImage

하나의 **Swapchain**에는 여러 개의 `VkImage`가 있다. `VkImage`도 당연히 여러 개 있을 수 있다.

### VkImage와 VkImageView

보통 `VkImage` 하나와 `VkImageView`가 하나씩 대응되지만, 충분히 `VkImageView`가 여러 개 있을 수 있다.

### Framebuffer

**Framebuffer**는 `VkImageView`에 대응되어 여러 개 있다.

### RenderPass와 Framebuffer의 관계

- **RenderPass:** 설계도
- **Framebuffer:** 여러 `VkImageView`들을 꽂아 놓은 책장 같은 느낌
- **RenderPass**는 이 슬롯들을 이용하여 그림을 그린다

```plaintext
Surface (1개)
    |
    v
Swapchain (1개)
    |
    v
VkImage (여러 개)
    |
    v
VkImageView (VkImage당 1개 이상)
    |
    v
Framebuffer (VkImageView당 1개)
    |
    v
RenderPass (설계도 - Framebuffer와 연결되어 렌더링 수행)
```

---

## 1. 기본 환경 설정 (초기화)

### 1.1. VkInstance 생성

`vkCreateInstance`를 호출하여 Vulkan API 사용을 시작한다. 이때 렌더링에 필요한 확장 기능(예: `VK_KHR_surface`)을 활성화한다.

### 1.2. VkSurfaceKHR 생성

애플리케이션의 윈도우(창)와 Vulkan을 연결하는 `VkSurfaceKHR` 객체를 생성한다. (운영체제별 함수 사용, 예: `vkCreateWin32SurfaceKHR`)

### 1.3. VkPhysicalDevice 선택

`vkEnumeratePhysicalDevices`로 GPU 목록을 가져온 뒤, 원하는 기능(그래픽 처리 가능 여부, 서피스 지원 여부 등)을 갖춘 GPU를 `VkPhysicalDevice`로 선택한다.

### 1.4. VkDevice 및 VkQueue 생성

선택한 `VkPhysicalDevice`에 대해 `vkCreateDevice`를 호출하여 논리 장치(`VkDevice`)를 생성한다. 이 과정에서 그래픽 명령을 처리할 큐(Queue) 패밀리를 지정하고, `vkGetDeviceQueue`를 통해 실제 `VkQueue` 객체 핸들을 가져온다.

---

## 2. 스왑체인 설정 (이미지 버퍼)

### 2.1. VkSwapchainKHR 생성

`vkCreateSwapchainKHR`를 호출하여 스왑체인을 생성한다. 이때 서피스의 속성(해상도, 포맷)과 버퍼링 방식(예: 트리플 버퍼링)을 지정한다.

### 2.2. VkImage 획득

`vkGetSwapchainImagesKHR`를 호출하여 스왑체인이 자동으로 생성한 `VkImage`들의 핸들 목록을 배열로 받아온다.

### 2.3. VkImageView 생성

받아온 각 `VkImage`에 대해 `vkCreateImageView`를 호출하여 `VkImageView`를 생성한다. 이는 이미지를 어떻게 해석할지(예: 2D 컬러 텍스처)를 정의한다.

---

## 3. 렌더링 방식 정의 (파이프라인)

### 3.1. VkRenderPass 생성

`vkCreateRenderPass`를 호출하여 렌더링 작업의 구조를 정의한다.

**정의 내용:**
- 컬러 첨부 파일(Attachment) 1개 사용
- 렌더링 시작 시 화면을 지움(Clear)
- 렌더링 종료 시 내용을 저장

### 3.2. VkGraphicsPipeline 생성

`vkCreateGraphicsPipelines`를 호출하여 그래픽 파이프라인을 생성한다. 이 객체는 렌더링의 모든 단계를 고정한다.

**파이프라인 구성 요소:**

| 구성 요소 | 설명 |
|----------|------|
| **VkShaderModule** | SPIR-V 코드로 컴파일된 셰이더(버텍스, 프래그먼트)를 로드 |
| **정점 입력**(Vertex Input) | 정점 데이터가 메모리에 어떻게 배치되어 있는지 정의 |
| **래스터화**(Rasterization) | 삼각형을 어떻게 그릴지(예: 앞면/뒷면 컬링) 정의 |
| **VkPipelineLayout** | 셰이더가 접근할 유니폼 버퍼나 텍스처 등의 리소스 레이아웃 정의 |
| **VkRenderPass** | 이 파이프라인이 호환되는 렌더 패스를 지정 |

---

## 4. 렌더링 대상 연결 (프레임 버퍼)

### 4.1. VkFramebuffer 생성

`vkCreateFramebuffer`를 호출하여 `VkRenderPass`와 `VkImageView`를 연결한다.

**중요:** 스왑체인의 `VkImageView`가 3개라면, 렌더 패스와 각 이미지 뷰를 묶는 `VkFramebuffer`도 3개를 생성해야 한다.

```plaintext
VkImageView[0] --> VkFramebuffer[0]
VkImageView[1] --> VkFramebuffer[1]
VkImageView[2] --> VkFramebuffer[2]
```

---

## 5. GPU 명령 준비 (커맨드 버퍼)

### 5.1. VkCommandPool 생성

`vkCreateCommandPool`을 호출하여 커맨드 버퍼를 할당할 메모리 풀을 생성한다.

### 5.2. VkCommandBuffer 할당

`vkAllocateCommandBuffers`를 호출하여 커맨드 풀로부터 실제 명령을 기록할 `VkCommandBuffer` 객체를 할당받는다.

---

## 6. 동기화 객체 준비

### 6.1. VkSemaphore 및 VkFence 생성

`vkCreateSemaphore`와 `vkCreateFence`를 호출하여 동기화 객체를 생성한다.

| 객체 | 용도 |
|------|------|
| **VkSemaphore** | GPU 작업 간의 순서 동기화 |
| **VkFence** | CPU-GPU 간의 동기화 |

---

## 7. 렌더링 루프 (매 프레임 반복 실행)

### 7.1. vkWaitForFences

CPU는 이전 프레임의 `vkQueueSubmit`이 완료되었다는 신호(펜스)를 받을 때까지 대기한다.

```cpp
vkWaitForFences(device, 1, &inFlightFence, VK_TRUE, UINT64_MAX);
vkResetFences(device, 1, &inFlightFence);
```

### 7.2. vkAcquireNextImageKHR

스왑체인에서 렌더링할 다음 이미지의 인덱스를 받아온다. 이때 **'이미지 획득 완료'** 신호를 보낼 **세마포어 A**를 전달한다.

```cpp
uint32_t imageIndex;
vkAcquireNextImageKHR(device, swapChain, UINT64_MAX,
                      imageAvailableSemaphore,  // 세마포어 A
                      VK_NULL_HANDLE, &imageIndex);
```

### 7.3. VkCommandBuffer 기록

```cpp
// 1. 커맨드 버퍼 기록 시작
vkBeginCommandBuffer(commandBuffer, &beginInfo);

// 2. 렌더 패스 시작 (획득한 인덱스에 맞는 Framebuffer 지정)
vkCmdBeginRenderPass(commandBuffer, &renderPassInfo, VK_SUBPASS_CONTENTS_INLINE);

// 3. 파이프라인 바인딩
vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, graphicsPipeline);

// 4. 드로우 콜
vkCmdDraw(commandBuffer, 3, 1, 0, 0);

// 5. 렌더 패스 종료
vkCmdEndRenderPass(commandBuffer);

// 6. 커맨드 버퍼 기록 완료
vkEndCommandBuffer(commandBuffer);
```

### 7.4. vkQueueSubmit

`VkQueue`에 커맨드 버퍼를 제출하여 GPU 실행을 요청한다.

```cpp
VkSubmitInfo submitInfo{};
submitInfo.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;

// Wait: 세마포어 A('이미지 획득 완료')를 기다림
VkSemaphore waitSemaphores[] = {imageAvailableSemaphore};
VkPipelineStageFlags waitStages[] = {VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT};
submitInfo.waitSemaphoreCount = 1;
submitInfo.pWaitSemaphores = waitSemaphores;
submitInfo.pWaitDstStageMask = waitStages;

// 커맨드 버퍼 지정
submitInfo.commandBufferCount = 1;
submitInfo.pCommandBuffers = &commandBuffer;

// Signal: 세마포어 B('렌더링 완료') 신호 설정
VkSemaphore signalSemaphores[] = {renderFinishedSemaphore};
submitInfo.signalSemaphoreCount = 1;
submitInfo.pSignalSemaphores = signalSemaphores;

// 펜스: '큐 작업 완료' 신호
vkQueueSubmit(graphicsQueue, 1, &submitInfo, inFlightFence);
```

**동기화 요약:**

| 설정 | 객체 | 역할 |
|------|------|------|
| **Wait** | 세마포어 A | '이미지 획득 완료' 대기 |
| **Signal** | 세마포어 B | '렌더링 완료' 신호 |
| **Fence** | 펜스 | '큐 작업 완료' 신호 (CPU에 알림) |

### 7.5. vkQueuePresentKHR

`VkQueue`에 화면 표시를 요청한다.

```cpp
VkPresentInfoKHR presentInfo{};
presentInfo.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR;

// Wait: 세마포어 B('렌더링 완료')를 기다림
VkSemaphore waitSemaphores[] = {renderFinishedSemaphore};
presentInfo.waitSemaphoreCount = 1;
presentInfo.pWaitSemaphores = waitSemaphores;

// 스왑체인과 이미지 인덱스 지정
VkSwapchainKHR swapChains[] = {swapChain};
presentInfo.swapchainCount = 1;
presentInfo.pSwapchains = swapChains;
presentInfo.pImageIndices = &imageIndex;

vkQueuePresentKHR(presentQueue, &presentInfo);
```

---

## 8. 전체 흐름 다이어그램

```plaintext
[초기화 단계]
VkInstance --> VkSurfaceKHR --> VkPhysicalDevice --> VkDevice/VkQueue

[스왑체인 설정]
VkSwapchainKHR --> VkImage[] --> VkImageView[]

[파이프라인 설정]
VkShaderModule + VkPipelineLayout --> VkRenderPass --> VkGraphicsPipeline

[프레임버퍼 설정]
VkImageView[] + VkRenderPass --> VkFramebuffer[]

[커맨드 설정]
VkCommandPool --> VkCommandBuffer[]

[동기화 설정]
VkSemaphore (이미지 획득용, 렌더링 완료용)
VkFence (CPU-GPU 동기화용)

[렌더링 루프]
1. vkWaitForFences       --> CPU가 이전 프레임 완료 대기
2. vkAcquireNextImageKHR --> 스왑체인에서 이미지 획득 (세마포어 A Signal)
3. vkBeginCommandBuffer  --> 커맨드 버퍼 기록 시작
4. vkCmdBeginRenderPass  --> 렌더 패스 시작
5. vkCmdBindPipeline     --> 파이프라인 바인딩
6. vkCmdDraw             --> 드로우 콜
7. vkCmdEndRenderPass    --> 렌더 패스 종료
8. vkEndCommandBuffer    --> 커맨드 버퍼 기록 완료
9. vkQueueSubmit         --> GPU에 작업 제출 (세마포어 A Wait, 세마포어 B Signal, 펜스)
10. vkQueuePresentKHR    --> 화면에 표시 (세마포어 B Wait)
```

---

## 9. 핵심 정리

### 9.1. 객체 관계

| 관계 | 설명 |
|------|------|
| Surface : Swapchain | 1 : 1 |
| Swapchain : VkImage | 1 : N |
| VkImage : VkImageView | 1 : N (보통 1:1) |
| VkImageView : Framebuffer | 1 : 1 |
| Framebuffer : RenderPass | N : 1 (호환성 필요) |

### 9.2. 동기화 객체 역할

| 객체 | 동기화 대상 | 주요 용도 |
|------|-------------|----------|
| **Semaphore** | GPU - GPU | 이미지 획득/렌더링 완료 신호 |
| **Fence** | CPU - GPU | CPU가 GPU 작업 완료 대기 |

### 9.3. 렌더링 루프 핵심 단계

1. **대기:** 이전 프레임 완료 대기 (Fence)
2. **획득:** 스왑체인 이미지 획득 (Acquire)
3. **기록:** 커맨드 버퍼에 명령 기록 (Record)
4. **제출:** 큐에 커맨드 버퍼 제출 (Submit)
5. **표시:** 화면에 이미지 표시 (Present)

---

## 마치며

이 문서에서는 Vulkan 렌더링의 전체 흐름을 정리했다. Surface부터 렌더링 루프까지 각 단계가 어떻게 연결되는지 이해하면, Vulkan의 명시적인 API 설계를 더 잘 활용할 수 있다.

다음 편에서는 실제 버텍스 데이터를 활용한 렌더링을 다룰 예정이다.
