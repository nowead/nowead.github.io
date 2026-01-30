+++
date = '2025-09-29T10:00:00+09:00'
draft = false
title = '[Vulkan] EP15. 정점 입력과 버퍼'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Vertex", "Buffer", "Memory", "Staging Buffer"]
categories = ["그래픽스 프로그래밍"]
summary = "Vulkan에서 정점 데이터를 정의하고 GPU 메모리에 버퍼로 전달하는 방법을 다룹니다."
+++

## 시작하며

[EP14](EP14_VULKAN_RENDERING_OVERVIEW.md)에서 Vulkan 렌더링의 전체 흐름을 정리했다. 이번 편에서는 **정점 입력**(Vertex Input)과 **정점 버퍼**(Vertex Buffer)를 다룬다.

Vulkan에서 그래픽스 파이프라인의 핵심 역할 중 하나는 3D 정점(vertex) 데이터를 화면의 2D 픽셀로 변환하는 것이다. 이 과정의 시작은 정점 데이터를 GPU에 전달하는 것인데, 이때 정점의 메모리 레이아웃과 데이터 형식을 Vulkan에 정확히 알려줘야 한다.

---

## 1. 정점 데이터의 구조

### 1.1. Vertex 구조체 정의

화면에 간단한 삼각형을 그리기 위해 각 정점이 위치(position)와 색상(color) 정보를 가지도록 정의한다.

```cpp
struct Vertex {
    glm::vec2 pos;   // 위치 (x, y)
    glm::vec3 color; // 색상 (r, g, b)
};
```

여기서 `glm::vec2`는 두 개의 float, `glm::vec3`는 세 개의 float를 의미한다.

### 1.2. 정점 데이터 배열

```cpp
const std::vector<Vertex> vertices = {
    {{0.0f, -0.5f}, {1.0f, 0.0f, 0.0f}}, // 정점 1: 중앙 아래, 빨간색
    {{0.5f, 0.5f}, {0.0f, 1.0f, 0.0f}},  // 정점 2: 오른쪽 위, 초록색
    {{-0.5f, 0.5f}, {0.0f, 0.0f, 1.0f}}  // 정점 3: 왼쪽 위, 파란색
};
```

이 배열은 GPU로 전송될 정점 데이터를 나타낸다.

---

## 2. 정점 입력 설명: 바인딩과 어트리뷰트

정점 셰이더는 `layout(location = x)` 한정자를 사용하여 특정 입력 데이터를 받는다. Vulkan은 이 셰이더 입력 변수들이 정점 버퍼의 어떤 데이터에 매핑되는지 명시적으로 정의해야 한다.

### 2.1. VkVertexInputBindingDescription (바인딩 설명)

정점 데이터가 GPU 메모리에서 어떻게 "바인딩"되는지, 즉 어떤 정점 버퍼에서 데이터를 가져올지 정의한다. 하나의 `VkVertexInputBindingDescription`은 하나의 정점 버퍼에 해당한다.

| 멤버 | 설명 |
|------|------|
| `binding` | 이 바인딩이 참조하는 정점 버퍼의 인덱스. `vkCmdBindVertexBuffers`에서 이 인덱스로 버퍼를 바인드 |
| `stride` | 정점 하나의 전체 크기(바이트 단위). 다음 정점까지의 오프셋 (예: `sizeof(Vertex)`) |
| `inputRate` | 정점 데이터가 정점 셰이더로 어떻게 공급되는지 정의 |

**inputRate 옵션:**

| 값 | 설명 |
|----|------|
| `VK_VERTEX_INPUT_RATE_VERTEX` | 정점별(per-vertex) 데이터. 각 정점마다 다음 데이터 사용 (일반적인 경우) |
| `VK_VERTEX_INPUT_RATE_INSTANCE` | 인스턴스별(per-instance) 데이터. 인스턴스 렌더링에 사용 |

### 2.2. VkVertexInputAttributeDescription (어트리뷰트 설명)

각 정점 셰이더 입력 변수(`layout(location = x)`)가 정점 버퍼의 특정 부분에 어떻게 매핑되는지 정의한다.

| 멤버 | 설명 |
|------|------|
| `binding` | 이 어트리뷰트가 가져올 데이터가 있는 정점 버퍼의 `binding` 인덱스 |
| `location` | 정점 셰이더의 `layout(location = x)`에 해당하는 값 |
| `format` | 어트리뷰트 데이터의 형식 (예: `VK_FORMAT_R32G32B32_SFLOAT` for `vec3`) |
| `offset` | 바인딩된 정점 버퍼 내에서 이 어트리뷰트 데이터가 시작되는 오프셋(바이트 단위) |

---

## 3. 정점 입력 설명 함수

### 3.1. getBindingDescription()

```cpp
static VkVertexInputBindingDescription getBindingDescription() {
    VkVertexInputBindingDescription bindingDescription{};
    bindingDescription.binding = 0;                          // 정점 버퍼 인덱스 0번
    bindingDescription.stride = sizeof(Vertex);              // Vertex 구조체 하나의 크기
    bindingDescription.inputRate = VK_VERTEX_INPUT_RATE_VERTEX; // 정점별 데이터
    return bindingDescription;
}
```

이는 단일 정점 버퍼에서 `Vertex` 구조체 단위로 데이터를 읽는다는 것을 정의한다.

### 3.2. getAttributeDescriptions()

```cpp
static std::array<VkVertexInputAttributeDescription, 2> getAttributeDescriptions() {
    std::array<VkVertexInputAttributeDescription, 2> attributeDescriptions{};

    // 위치 (pos) 어트리뷰트
    attributeDescriptions[0].binding = 0;                         // 0번 바인딩에서 데이터 가져옴
    attributeDescriptions[0].location = 0;                        // 셰이더의 layout(location = 0)에 매핑
    attributeDescriptions[0].format = VK_FORMAT_R32G32_SFLOAT;    // vec2 타입 (x, y)
    attributeDescriptions[0].offset = offsetof(Vertex, pos);      // Vertex 구조체 내 pos의 오프셋

    // 색상 (color) 어트리뷰트
    attributeDescriptions[1].binding = 0;                         // 0번 바인딩에서 데이터 가져옴
    attributeDescriptions[1].location = 1;                        // 셰이더의 layout(location = 1)에 매핑
    attributeDescriptions[1].format = VK_FORMAT_R32G32B32_SFLOAT; // vec3 타입 (r, g, b)
    attributeDescriptions[1].offset = offsetof(Vertex, color);    // Vertex 구조체 내 color의 오프셋

    return attributeDescriptions;
}
```

이 함수는 `Vertex` 구조체의 `pos`와 `color` 멤버가 각각 셰이더의 `location = 0`과 `location = 1` 입력 변수로 어떻게 매핑될지 정의한다.

---

## 4. 셰이더와의 연결

정점 셰이더는 어트리뷰트 설명을 기반으로 입력 데이터를 받는다.

### 4.1. 정점 셰이더 예시

```glsl
#version 450
#extension GL_ARB_separate_shader_objects : enable

layout(location = 0) in vec2 inPosition; // attributeDescriptions[0]과 연결
layout(location = 1) in vec3 inColor;    // attributeDescriptions[1]과 연결

layout(location = 0) out vec3 fragColor;

void main() {
    gl_Position = vec4(inPosition, 0.0, 1.0);
    fragColor = inColor;
}
```

### 4.2. 데이터 흐름

```plaintext
Vertex Buffer (GPU Memory)
    |
    v
VkVertexInputBindingDescription (바인딩 0, stride = sizeof(Vertex))
    |
    +-- VkVertexInputAttributeDescription[0] (location = 0, pos)
    |       |
    |       v
    |   layout(location = 0) in vec2 inPosition
    |
    +-- VkVertexInputAttributeDescription[1] (location = 1, color)
            |
            v
        layout(location = 1) in vec3 inColor
```

---

## 5. 파이프라인 생성 시 적용

바인딩 및 어트리뷰트 설명은 그래픽스 파이프라인 생성 시 `VkPipelineVertexInputStateCreateInfo` 구조체에 포함된다.

```cpp
VkPipelineVertexInputStateCreateInfo vertexInputInfo{};
vertexInputInfo.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;

auto bindingDescription = Vertex::getBindingDescription();
auto attributeDescriptions = Vertex::getAttributeDescriptions();

vertexInputInfo.vertexBindingDescriptionCount = 1;
vertexInputInfo.pVertexBindingDescriptions = &bindingDescription;
vertexInputInfo.vertexAttributeDescriptionCount = static_cast<uint32_t>(attributeDescriptions.size());
vertexInputInfo.pVertexAttributeDescriptions = attributeDescriptions.data();
```

---

## 6. VkBuffer 객체의 역할

`VkBuffer`는 Vulkan에서 범용적인 메모리 버퍼를 나타낸다. 정점 데이터, 인덱스 데이터, 유니폼 데이터, 스토리지 데이터 등 다양한 종류의 데이터를 저장하는 데 사용된다.

**중요:** `VkBuffer` 객체 자체는 메모리 할당을 관리하지 않으며, 특정 종류의 데이터를 저장하기 위한 "메타데이터" 역할을 한다. 실제 메모리 할당은 별도의 `VkDeviceMemory` 객체를 통해 이루어진다.

---

## 7. 정점 버퍼 생성 과정

### 7.1. 버퍼 생성 정보 (VkBufferCreateInfo)

`VkBuffer` 객체를 생성할 때 `VkBufferCreateInfo` 구조체를 채운다.

```cpp
VkBufferCreateInfo bufferInfo{};
bufferInfo.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
bufferInfo.size = bufferSize;
bufferInfo.usage = VK_BUFFER_USAGE_VERTEX_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
bufferInfo.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
```

| 멤버 | 설명 |
|------|------|
| `size` | 버퍼의 전체 크기(바이트 단위). 예: `sizeof(vertices[0]) * vertices.size()` |
| `usage` | 버퍼의 용도를 지정하는 플래그 |
| `sharingMode` | 버퍼가 여러 큐 패밀리 간에 공유될지 여부 |

**usage 플래그:**

| 플래그 | 설명 |
|--------|------|
| `VK_BUFFER_USAGE_VERTEX_BUFFER_BIT` | 정점 버퍼로 사용 |
| `VK_BUFFER_USAGE_TRANSFER_DST_BIT` | 데이터 전송의 목적지로 사용 |
| `VK_BUFFER_USAGE_TRANSFER_SRC_BIT` | 데이터 전송의 소스로 사용 |

**sharingMode 옵션:**

| 값 | 설명 |
|----|------|
| `VK_SHARING_MODE_EXCLUSIVE` | 단일 큐 패밀리만 버퍼에 접근 (기본값) |
| `VK_SHARING_MODE_CONCURRENT` | 여러 큐 패밀리가 동시에 버퍼에 접근 가능 |

### 7.2. 버퍼 메모리 요구사항 조회

`VkBuffer` 객체는 생성되었지만, 아직 실제 메모리가 할당되지는 않았다. 버퍼에 필요한 메모리 타입과 크기를 확인해야 한다.

```cpp
VkMemoryRequirements memRequirements;
vkGetBufferMemoryRequirements(device, vertexBuffer, &memRequirements);
```

**VkMemoryRequirements 구조체:**

| 멤버 | 설명 |
|------|------|
| `size` | 버퍼에 필요한 최소 메모리 크기(바이트 단위) |
| `alignment` | 메모리 정렬 요구사항 |
| `memoryTypeBits` | 버퍼에 사용할 수 있는 메모리 타입들의 비트 마스크 |

### 7.3. 적합한 메모리 타입 찾기

시스템의 GPU는 여러 종류의 메모리를 가질 수 있다 (예: 빠르지만 접근 불가능한 GPU 전용 메모리, 느리지만 CPU가 접근 가능한 통합 메모리 등).

```cpp
uint32_t findMemoryType(uint32_t typeFilter, VkMemoryPropertyFlags properties) {
    VkPhysicalDeviceMemoryProperties memProperties;
    vkGetPhysicalDeviceMemoryProperties(physicalDevice, &memProperties);

    for (uint32_t i = 0; i < memProperties.memoryTypeCount; i++) {
        if ((typeFilter & (1 << i)) &&
            (memProperties.memoryTypes[i].propertyFlags & properties) == properties) {
            return i;
        }
    }

    throw std::runtime_error("failed to find suitable memory type!");
}
```

**메모리 속성 플래그:**

| 플래그 | 설명 |
|--------|------|
| `VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT` | CPU가 메모리 매핑을 통해 접근(읽기/쓰기) 가능 |
| `VK_MEMORY_PROPERTY_HOST_COHERENT_BIT` | CPU-GPU 간 캐시 일관성 보장 |
| `VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT` | GPU 장치에 로컬(전용) 메모리. 가장 빠름 |

---

## 8. 스테이징 버퍼를 통한 데이터 전송

정점 데이터는 GPU가 자주 읽어야 하므로, `VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT` 속성을 가진 메모리에 저장하는 것이 이상적이다. 하지만 `HOST_VISIBLE` 속성은 없으므로 CPU가 직접 데이터를 쓸 수 없다. 따라서 **스테이징 버퍼**(staging buffer)를 사용한다.

### 8.1. 전송 과정 개요

```plaintext
CPU Memory (vertices 배열)
    |
    | memcpy
    v
Staging Buffer (HOST_VISIBLE | HOST_COHERENT)
    |
    | vkCmdCopyBuffer
    v
Vertex Buffer (DEVICE_LOCAL)
    |
    v
GPU Rendering Pipeline
```

### 8.2. 스테이징 버퍼 생성

```cpp
VkBuffer stagingBuffer;
VkDeviceMemory stagingBufferMemory;

// 스테이징 버퍼: 전송 소스, CPU 접근 가능
createBuffer(bufferSize,
             VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
             VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
             stagingBuffer, stagingBufferMemory);
```

### 8.3. 데이터 매핑 및 복사 (CPU --> 스테이징 버퍼)

```cpp
void* data;
vkMapMemory(device, stagingBufferMemory, 0, bufferSize, 0, &data);
memcpy(data, vertices.data(), (size_t)bufferSize);
vkUnmapMemory(device, stagingBufferMemory);
```

**단계별 설명:**

1. `vkMapMemory`: 스테이징 버퍼 메모리를 CPU 주소 공간에 매핑
2. `memcpy`: 정점 데이터를 매핑된 메모리 영역으로 복사
3. `vkUnmapMemory`: 메모리 매핑 해제

### 8.4. GPU 간 복사 명령 (스테이징 버퍼 --> 정점 버퍼)

```cpp
void copyBuffer(VkBuffer srcBuffer, VkBuffer dstBuffer, VkDeviceSize size) {
    // 단일 사용 커맨드 버퍼 할당
    VkCommandBufferAllocateInfo allocInfo{};
    allocInfo.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    allocInfo.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocInfo.commandPool = commandPool;
    allocInfo.commandBufferCount = 1;

    VkCommandBuffer commandBuffer;
    vkAllocateCommandBuffers(device, &allocInfo, &commandBuffer);

    // 커맨드 버퍼 기록 시작
    VkCommandBufferBeginInfo beginInfo{};
    beginInfo.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    beginInfo.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;

    vkBeginCommandBuffer(commandBuffer, &beginInfo);

    // 복사 명령 기록
    VkBufferCopy copyRegion{};
    copyRegion.srcOffset = 0;
    copyRegion.dstOffset = 0;
    copyRegion.size = size;
    vkCmdCopyBuffer(commandBuffer, srcBuffer, dstBuffer, 1, &copyRegion);

    vkEndCommandBuffer(commandBuffer);

    // 커맨드 버퍼 제출 및 완료 대기
    VkSubmitInfo submitInfo{};
    submitInfo.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    submitInfo.commandBufferCount = 1;
    submitInfo.pCommandBuffers = &commandBuffer;

    vkQueueSubmit(graphicsQueue, 1, &submitInfo, VK_NULL_HANDLE);
    vkQueueWaitIdle(graphicsQueue);

    // 커맨드 버퍼 해제
    vkFreeCommandBuffers(device, commandPool, 1, &commandBuffer);
}
```

### 8.5. 최종 정점 버퍼 생성 및 데이터 전송

```cpp
// 정점 버퍼: 전송 목적지, GPU 전용 메모리
createBuffer(bufferSize,
             VK_BUFFER_USAGE_TRANSFER_DST_BIT | VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
             VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
             vertexBuffer, vertexBufferMemory);

// 스테이징 버퍼에서 정점 버퍼로 복사
copyBuffer(stagingBuffer, vertexBuffer, bufferSize);

// 스테이징 버퍼 정리
vkDestroyBuffer(device, stagingBuffer, nullptr);
vkFreeMemory(device, stagingBufferMemory, nullptr);
```

---

## 9. 버퍼 소멸

애플리케이션 종료 시 버퍼와 메모리를 정리해야 한다.

```cpp
void cleanup() {
    // ... 다른 정리 코드 ...

    vkDestroyBuffer(device, vertexBuffer, nullptr);
    vkFreeMemory(device, vertexBufferMemory, nullptr);

    // ... 나머지 정리 코드 ...
}
```

**정리 순서:**
1. `vkDestroyBuffer`: `VkBuffer` 객체 소멸
2. `vkFreeMemory`: 할당된 `VkDeviceMemory` 해제

---

## 10. 핵심 정리

### 10.1. 정점 입력 설명

| 구조체 | 역할 |
|--------|------|
| `VkVertexInputBindingDescription` | 정점 버퍼의 레이아웃 (스트라이드, 입력 속도) 정의 |
| `VkVertexInputAttributeDescription` | 정점 버퍼 내 특정 데이터 필드가 셰이더의 어떤 입력 변수에 매핑되는지 정의 |

### 10.2. 메모리 타입 선택

| 용도 | 메모리 속성 |
|------|-------------|
| 스테이징 버퍼 | `HOST_VISIBLE` \| `HOST_COHERENT` |
| 정점 버퍼 | `DEVICE_LOCAL` |

### 10.3. 데이터 전송 흐름

```plaintext
1. CPU Memory (vertices)
       |
       v [memcpy]
2. Staging Buffer (HOST_VISIBLE)
       |
       v [vkCmdCopyBuffer]
3. Vertex Buffer (DEVICE_LOCAL)
       |
       v
4. GPU Rendering
```

### 10.4. 버퍼 생성 단계

1. `VkBufferCreateInfo` 구조체 채우기
2. `vkCreateBuffer`로 `VkBuffer` 생성
3. `vkGetBufferMemoryRequirements`로 메모리 요구사항 조회
4. `findMemoryType`으로 적합한 메모리 타입 찾기
5. `vkAllocateMemory`로 메모리 할당
6. `vkBindBufferMemory`로 버퍼와 메모리 바인딩

---

## 마치며

이 문서에서는 Vulkan에서 정점 데이터를 정의하고 GPU 메모리로 전달하는 방법을 살펴보았다. `VkVertexInputBindingDescription`과 `VkVertexInputAttributeDescription`을 통해 정점 버퍼의 레이아웃을 정의하고, 스테이징 버퍼를 통해 CPU 메모리의 데이터를 GPU 전용 메모리로 효율적으로 전송하는 패턴을 이해했다.

다음 편에서는 인덱스 버퍼를 활용한 효율적인 메시 렌더링을 다룰 예정이다.
