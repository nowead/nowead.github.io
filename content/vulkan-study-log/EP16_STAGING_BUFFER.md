+++
date = '2025-10-04T10:00:00+09:00'
draft = false
title = '[Vulkan] EP16. 스테이징 버퍼(Staging Buffer)'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Staging Buffer", "Memory", "Buffer", "Data Transfer"]
categories = ["그래픽스 프로그래밍"]
summary = "Vulkan에서 CPU 메모리의 데이터를 GPU 전용 메모리로 효율적으로 전송하는 스테이징 버퍼 패턴을 다룹니다."
+++

## 시작하며

[EP15](EP15_VERTEX_INPUT_BUFFER.md)에서 정점 입력과 버퍼의 기본 개념을 살펴보았다. 이번 편에서는 **스테이징 버퍼**(Staging Buffer)를 활용한 효율적인 GPU 메모리 전송 패턴을 다룬다.

Vulkan에서 GPU의 효율적인 작동을 위해 대부분의 버퍼(정점 버퍼, 인덱스 버퍼, 이미지 등)는 GPU 전용 메모리(`VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT`)에 위치하는 것이 가장 좋다. 하지만 CPU는 이 GPU 전용 메모리에 직접 데이터를 쓸 수 없다. **스테이징 버퍼**(Staging Buffer)는 이러한 문제를 해결하기 위한 중간 단계 버퍼로, CPU가 데이터를 쓸 수 있는 메모리(`VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT`)에 생성된 임시 버퍼이다. 이 장에서는 스테이징 버퍼를 사용한 데이터 전송의 원리와 구현 방법을 상세히 다룬다.

---

## 1. 스테이징 버퍼의 필요성

### 1.1. 메모리 타입의 이분화

Vulkan은 시스템에 여러 종류의 메모리 타입을 노출한다.

| 메모리 속성 | 특징 |
|------------|------|
| `VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT` | GPU 전용 메모리, GPU가 가장 빠르게 접근 가능, CPU 접근 불가능/매우 느림 |
| `VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT` | CPU가 메모리 매핑을 통해 접근(읽기/쓰기) 가능, GPU 전용보다 느릴 수 있음 |

대부분의 렌더링 자원(정점/인덱스 버퍼, 이미지)은 GPU 전용 메모리에 저장된다.

### 1.2. 데이터 전송 효율

CPU에서 GPU 전용 메모리로 데이터를 직접 복사하는 것은 비효율적이거나 불가능할 수 있다.

**스테이징 버퍼의 장점:**

- CPU는 `HOST_VISIBLE` 버퍼에 데이터를 빠르게 쓸 수 있다
- GPU는 `HOST_VISIBLE` 버퍼에서 `DEVICE_LOCAL` 버퍼로 데이터를 고속으로 복사하는 전용 하드웨어를 활용할 수 있다

```plaintext
[CPU Memory]
     |
     v (memcpy - CPU 작업)
[Staging Buffer: HOST_VISIBLE]
     |
     v (vkCmdCopyBuffer - GPU DMA 전송)
[Vertex Buffer: DEVICE_LOCAL]
```

---

## 2. 스테이징 버퍼를 이용한 데이터 전송 과정

정점 데이터(`vertices`)를 GPU 전용 정점 버퍼(`vertexBuffer`)로 옮기는 단계는 다음과 같다.

### 2.1. 전체 흐름

```plaintext
1. 스테이징 버퍼 생성 (HOST_VISIBLE | HOST_COHERENT)
          |
          v
2. CPU 데이터 --> 스테이징 버퍼 (vkMapMemory + memcpy)
          |
          v
3. 정점 버퍼 생성 (DEVICE_LOCAL)
          |
          v
4. 스테이징 버퍼 --> 정점 버퍼 (vkCmdCopyBuffer)
          |
          v
5. 스테이징 버퍼 소멸
```

### 2.2. 단계별 상세 설명

#### 단계 1: 스테이징 버퍼 생성

`createBuffer` 함수를 호출하여 `VkBuffer` 객체와 `VkDeviceMemory` 객체를 생성한다.

| 속성 | 값 |
|-----|-----|
| **용도**(usage) | `VK_BUFFER_USAGE_TRANSFER_SRC_BIT` (데이터 전송의 소스) |
| **메모리 속성**(properties) | `VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT` \| `VK_MEMORY_PROPERTY_HOST_COHERENT_BIT` |

**메모리 속성 플래그 설명:**

- **`HOST_VISIBLE`:** CPU가 매핑하여 데이터를 쓸 수 있도록 한다
- **`HOST_COHERENT`:** 매핑된 메모리에 CPU가 쓴 데이터가 GPU에 즉시 가시적으로 되도록 보장한다. 이 플래그가 없으면 `vkFlushMappedMemoryRanges`를 호출하여 명시적으로 캐시를 플러시해야 한다

```cpp
VkBuffer stagingBuffer;
VkDeviceMemory stagingBufferMemory;
createBuffer(bufferSize,
             VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
             VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
             stagingBuffer,
             stagingBufferMemory);
```

#### 단계 2: 데이터 매핑 및 복사 (CPU --> 스테이징 버퍼)

```cpp
// 1. 메모리 매핑
void* data;
vkMapMemory(device, stagingBufferMemory, 0, bufferSize, 0, &data);

// 2. 데이터 복사
memcpy(data, vertices.data(), (size_t) bufferSize);

// 3. 매핑 해제
vkUnmapMemory(device, stagingBufferMemory);
```

**`vkMapMemory` 매개변수:**

| 매개변수 | 설명 |
|---------|------|
| `device` | 논리적 디바이스 |
| `stagingBufferMemory` | 매핑할 메모리 객체 |
| `offset` | 메모리 시작 오프셋 (0부터 시작) |
| `size` | 매핑할 크기 |
| `flags` | 예약됨 (0) |
| `ppData` | 매핑된 포인터를 받을 변수 |

`HOST_COHERENT` 플래그를 사용했으므로 `vkUnmapMemory` 호출 시점에서 데이터는 GPU에 가시적이게 된다.

#### 단계 3: 정점 버퍼 생성

최종 `vertexBuffer` 객체와 `vertexBufferMemory` 객체를 생성한다.

| 속성 | 값 |
|-----|-----|
| **용도**(usage) | `VK_BUFFER_USAGE_VERTEX_BUFFER_BIT` \| `VK_BUFFER_USAGE_TRANSFER_DST_BIT` |
| **메모리 속성**(properties) | `VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT` |

```cpp
VkBuffer vertexBuffer;
VkDeviceMemory vertexBufferMemory;
createBuffer(bufferSize,
             VK_BUFFER_USAGE_TRANSFER_DST_BIT | VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
             VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
             vertexBuffer,
             vertexBufferMemory);
```

#### 단계 4: GPU 간 복사 (copyBuffer 함수)

`copyBuffer` 헬퍼 함수를 사용하여 스테이징 버퍼에서 최종 정점 버퍼로 데이터를 복사한다.

```cpp
copyBuffer(stagingBuffer, vertexBuffer, bufferSize);
```

#### 단계 5: 스테이징 버퍼 소멸

데이터 복사가 완료된 후에는 스테이징 버퍼와 그 메모리가 더 이상 필요 없으므로 소멸시킨다.

```cpp
vkDestroyBuffer(device, stagingBuffer, nullptr);
vkFreeMemory(device, stagingBufferMemory, nullptr);
```

---

## 3. copyBuffer 함수 구현

### 3.1. 함수 개요

```cpp
void copyBuffer(VkBuffer srcBuffer, VkBuffer dstBuffer, VkDeviceSize size) {
    // 1. 단일 사용 커맨드 버퍼 할당
    // 2. vkCmdCopyBuffer 명령 기록
    // 3. 커맨드 버퍼 제출 및 대기
    // 4. 커맨드 버퍼 해제
}
```

### 3.2. 단계별 구현

#### 단계 1: 단일 사용 커맨드 버퍼 할당

```cpp
VkCommandBufferAllocateInfo allocInfo{};
allocInfo.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
allocInfo.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
allocInfo.commandPool = commandPool;
allocInfo.commandBufferCount = 1;

VkCommandBuffer commandBuffer;
vkAllocateCommandBuffers(device, &allocInfo, &commandBuffer);

VkCommandBufferBeginInfo beginInfo{};
beginInfo.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
beginInfo.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;

vkBeginCommandBuffer(commandBuffer, &beginInfo);
```

**`VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT`:** 이 커맨드 버퍼가 한 번 사용되고 재기록될 것임을 알린다.

#### 단계 2: vkCmdCopyBuffer 명령 기록

```cpp
VkBufferCopy copyRegion{};
copyRegion.srcOffset = 0;  // 소스 오프셋
copyRegion.dstOffset = 0;  // 목적지 오프셋
copyRegion.size = size;    // 복사할 크기

vkCmdCopyBuffer(commandBuffer, srcBuffer, dstBuffer, 1, &copyRegion);
```

**`VkBufferCopy` 구조체:**

| 필드 | 설명 |
|-----|------|
| `srcOffset` | 소스 버퍼의 시작 오프셋 |
| `dstOffset` | 목적지 버퍼의 시작 오프셋 |
| `size` | 복사할 바이트 수 |

#### 단계 3: 커맨드 버퍼 종료 및 제출

```cpp
vkEndCommandBuffer(commandBuffer);

VkSubmitInfo submitInfo{};
submitInfo.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
submitInfo.commandBufferCount = 1;
submitInfo.pCommandBuffers = &commandBuffer;

vkQueueSubmit(graphicsQueue, 1, &submitInfo, VK_NULL_HANDLE);
vkQueueWaitIdle(graphicsQueue);
```

**왜 `vkQueueWaitIdle`을 사용하는가?**

간단한 복사 작업이므로 펜스 사용보다 `WaitIdle`이 편리하다. 제출이 완료될 때까지 CPU를 블록한다.

#### 단계 4: 커맨드 버퍼 해제

```cpp
vkFreeCommandBuffers(device, commandPool, 1, &commandBuffer);
```

### 3.3. 전체 copyBuffer 함수

```cpp
void copyBuffer(VkBuffer srcBuffer, VkBuffer dstBuffer, VkDeviceSize size) {
    VkCommandBufferAllocateInfo allocInfo{};
    allocInfo.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    allocInfo.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocInfo.commandPool = commandPool;
    allocInfo.commandBufferCount = 1;

    VkCommandBuffer commandBuffer;
    vkAllocateCommandBuffers(device, &allocInfo, &commandBuffer);

    VkCommandBufferBeginInfo beginInfo{};
    beginInfo.sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    beginInfo.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;

    vkBeginCommandBuffer(commandBuffer, &beginInfo);

    VkBufferCopy copyRegion{};
    copyRegion.size = size;
    vkCmdCopyBuffer(commandBuffer, srcBuffer, dstBuffer, 1, &copyRegion);

    vkEndCommandBuffer(commandBuffer);

    VkSubmitInfo submitInfo{};
    submitInfo.sType = VK_STRUCTURE_TYPE_SUBMIT_INFO;
    submitInfo.commandBufferCount = 1;
    submitInfo.pCommandBuffers = &commandBuffer;

    vkQueueSubmit(graphicsQueue, 1, &submitInfo, VK_NULL_HANDLE);
    vkQueueWaitIdle(graphicsQueue);

    vkFreeCommandBuffers(device, commandPool, 1, &commandBuffer);
}
```

---

## 4. createBuffer 함수 구현

`VkBuffer` 객체와 `VkDeviceMemory`를 생성하고 바인딩하는 공통 로직을 캡슐화한다.

### 4.1. 함수 시그니처

```cpp
void createBuffer(VkDeviceSize size,
                  VkBufferUsageFlags usage,
                  VkMemoryPropertyFlags properties,
                  VkBuffer& buffer,
                  VkDeviceMemory& bufferMemory);
```

### 4.2. 구현

```cpp
void createBuffer(VkDeviceSize size,
                  VkBufferUsageFlags usage,
                  VkMemoryPropertyFlags properties,
                  VkBuffer& buffer,
                  VkDeviceMemory& bufferMemory) {
    // 1. VkBufferCreateInfo 설정 및 vkCreateBuffer 호출
    VkBufferCreateInfo bufferInfo{};
    bufferInfo.sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    bufferInfo.size = size;
    bufferInfo.usage = usage;
    bufferInfo.sharingMode = VK_SHARING_MODE_EXCLUSIVE;

    if (vkCreateBuffer(device, &bufferInfo, nullptr, &buffer) != VK_SUCCESS) {
        throw std::runtime_error("failed to create buffer!");
    }

    // 2. VkMemoryRequirements 조회
    VkMemoryRequirements memRequirements;
    vkGetBufferMemoryRequirements(device, buffer, &memRequirements);

    // 3. VkMemoryAllocateInfo 설정 및 vkAllocateMemory 호출
    VkMemoryAllocateInfo allocInfo{};
    allocInfo.sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    allocInfo.allocationSize = memRequirements.size;
    allocInfo.memoryTypeIndex = findMemoryType(memRequirements.memoryTypeBits, properties);

    if (vkAllocateMemory(device, &allocInfo, nullptr, &bufferMemory) != VK_SUCCESS) {
        throw std::runtime_error("failed to allocate buffer memory!");
    }

    // 4. vkBindBufferMemory 호출
    vkBindBufferMemory(device, buffer, bufferMemory, 0);
}
```

### 4.3. 버퍼 생성 흐름

```plaintext
VkBufferCreateInfo 설정
         |
         v
vkCreateBuffer (VkBuffer 생성)
         |
         v
vkGetBufferMemoryRequirements (메모리 요구사항 조회)
         |
         v
findMemoryType (적합한 메모리 타입 찾기)
         |
         v
vkAllocateMemory (메모리 할당)
         |
         v
vkBindBufferMemory (버퍼와 메모리 바인딩)
```

---

## 5. 전체 정점 버퍼 생성 코드

```cpp
void createVertexBuffer() {
    VkDeviceSize bufferSize = sizeof(vertices[0]) * vertices.size();

    // 스테이징 버퍼 생성
    VkBuffer stagingBuffer;
    VkDeviceMemory stagingBufferMemory;
    createBuffer(bufferSize,
                 VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                 VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
                 stagingBuffer,
                 stagingBufferMemory);

    // CPU --> 스테이징 버퍼 복사
    void* data;
    vkMapMemory(device, stagingBufferMemory, 0, bufferSize, 0, &data);
    memcpy(data, vertices.data(), (size_t) bufferSize);
    vkUnmapMemory(device, stagingBufferMemory);

    // 정점 버퍼 생성 (GPU 전용)
    createBuffer(bufferSize,
                 VK_BUFFER_USAGE_TRANSFER_DST_BIT | VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                 VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
                 vertexBuffer,
                 vertexBufferMemory);

    // 스테이징 버퍼 --> 정점 버퍼 복사
    copyBuffer(stagingBuffer, vertexBuffer, bufferSize);

    // 스테이징 버퍼 정리
    vkDestroyBuffer(device, stagingBuffer, nullptr);
    vkFreeMemory(device, stagingBufferMemory, nullptr);
}
```

---

## 6. 버퍼 용도 플래그 정리

| 플래그 | 설명 |
|--------|------|
| `VK_BUFFER_USAGE_TRANSFER_SRC_BIT` | 데이터 전송의 소스로 사용 |
| `VK_BUFFER_USAGE_TRANSFER_DST_BIT` | 데이터 전송의 목적지로 사용 |
| `VK_BUFFER_USAGE_VERTEX_BUFFER_BIT` | 정점 버퍼로 사용 |
| `VK_BUFFER_USAGE_INDEX_BUFFER_BIT` | 인덱스 버퍼로 사용 |
| `VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT` | 유니폼 버퍼로 사용 |

---

## 7. 메모리 속성 플래그 정리

| 플래그 | 설명 |
|--------|------|
| `VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT` | GPU 전용, 가장 빠른 GPU 접근 |
| `VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT` | CPU에서 매핑 가능 |
| `VK_MEMORY_PROPERTY_HOST_COHERENT_BIT` | CPU 쓰기가 GPU에 즉시 가시적 |
| `VK_MEMORY_PROPERTY_HOST_CACHED_BIT` | CPU 읽기가 캐시됨 (읽기 최적화) |

---

## 8. 성능 고려사항

### 8.1. 전송 전용 큐 사용

일부 GPU는 그래픽스 큐와 별도로 전송 전용 큐(Transfer Queue)를 제공한다. 이를 활용하면 그래픽스 작업과 데이터 전송을 병렬로 수행할 수 있다.

```plaintext
Graphics Queue: 렌더링 작업
         |
         | (병렬 실행)
         v
Transfer Queue: 데이터 복사 작업
```

### 8.2. 메모리 풀링

빈번한 메모리 할당/해제는 비용이 크다. 대규모 프로젝트에서는 VMA(Vulkan Memory Allocator) 같은 메모리 관리 라이브러리를 사용하여 메모리 풀을 관리하는 것이 좋다.

### 8.3. 배치 전송

여러 버퍼를 전송할 때는 개별 `copyBuffer` 호출 대신 하나의 커맨드 버퍼에 여러 복사 명령을 기록하여 배치로 처리하는 것이 효율적이다.

---

## 9. 요약

| 단계 | 설명 |
|------|------|
| 1 | 스테이징 버퍼 생성 (`HOST_VISIBLE` \| `HOST_COHERENT`, `TRANSFER_SRC`) |
| 2 | `vkMapMemory` + `memcpy`로 CPU 데이터 복사 |
| 3 | 최종 버퍼 생성 (`DEVICE_LOCAL`, `TRANSFER_DST`) |
| 4 | `vkCmdCopyBuffer`로 GPU 복사 수행 |
| 5 | 스테이징 버퍼 소멸 |

스테이징 버퍼는 Vulkan에서 CPU 메모리에서 GPU 전용 메모리로 데이터를 효율적으로 전송하기 위한 필수적인 패턴이다. `HOST_VISIBLE` 속성을 가진 임시 스테이징 버퍼에 CPU가 데이터를 먼저 쓰고, 이 데이터를 `TRANSFER_SRC`로 지정된 스테이징 버퍼에서 `TRANSFER_DST`로 지정된 GPU 전용 버퍼로 GPU 전송 명령을 통해 복사한다.

---

## 마치며

이 문서에서는 Vulkan의 스테이징 버퍼 패턴을 상세히 살펴보았다. CPU에서 GPU 전용 메모리로 데이터를 효율적으로 전송하기 위해 중간 단계 버퍼를 사용하는 이 패턴은 Vulkan의 명시적인 메모리 관리와 최적화 전략을 잘 보여준다.

다음 편에서는 인덱스 버퍼를 활용한 효율적인 메시 렌더링을 다룰 예정이다.
