+++
date = '2025-10-11T10:00:00+09:00'
draft = false
title = '[Vulkan] EP17. 인덱스 버퍼(Index Buffer)'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Index Buffer", "Vertex", "Mesh", "Rendering"]
categories = ["그래픽스 프로그래밍"]
summary = "Vulkan에서 인덱스 버퍼를 사용하여 정점 데이터를 재사용하고 효율적으로 메시를 렌더링하는 방법을 다룹니다."
+++

## 시작하며

[EP16](EP16_STAGING_BUFFER.md)에서 스테이징 버퍼를 활용한 GPU 메모리 전송 패턴을 살펴보았다. 이번 편에서는 **인덱스 버퍼**(Index Buffer)를 활용한 효율적인 메시 렌더링을 다룬다.

정점 버퍼(Vertex Buffer)만으로도 지오메트리를 그릴 수 있지만, 복잡한 3D 모델을 효율적으로 렌더링하기 위해서는 인덱스 버퍼를 사용하는 것이 일반적이다. 인덱스 버퍼는 정점 데이터를 재사용하여 정점 버퍼의 크기를 줄이고 GPU 캐시 효율성을 높인다.

---

## 1. 인덱스 버퍼의 필요성

### 1.1. 정점 데이터 재사용

대부분의 3D 모델은 여러 면(삼각형)이 동일한 정점을 공유한다.

**예시: 큐브**

- 유일한 정점: 8개
- 면의 개수: 6개 (각 면은 2개의 삼각형)
- 총 삼각형: 12개
- 필요한 정점 참조: 36개 (12 x 3)

```plaintext
인덱스 버퍼 없이:
[v0, v1, v2, v0, v2, v3, v0, v3, v4, ...]  --> 36개 정점 데이터 중복 저장

인덱스 버퍼 사용:
정점 버퍼: [v0, v1, v2, v3, v4, v5, v6, v7]  --> 8개 정점만 저장
인덱스 버퍼: [0, 1, 2, 0, 2, 3, 0, 3, 4, ...]  --> 인덱스로 참조
```

### 1.2. 인덱스 버퍼의 장점

| 장점 | 설명 |
|------|------|
| **메모리 절약** | 중복된 정점 데이터를 한 번만 저장 |
| **GPU 캐시 효율성** | 정점이 연속 저장되어 캐시 히트율 향상 |
| **대역폭 감소** | 전송해야 할 데이터 양 감소 |

### 1.3. 사각형 예시

```plaintext
인덱스 버퍼 없이 (6개 정점):
삼각형 1: v0, v1, v2
삼각형 2: v2, v3, v0  --> v0, v2 중복!

    v0 -------- v1
    |  \        |
    |    \      |
    |      \    |
    v3 -------- v2

인덱스 버퍼 사용 (4개 정점 + 6개 인덱스):
정점: [v0, v1, v2, v3]
인덱스: [0, 1, 2, 2, 3, 0]
```

---

## 2. 인덱스 데이터의 구조

### 2.1. 인덱스 배열 정의

```cpp
// 4개의 유일한 정점으로 사각형 구성
const std::vector<Vertex> vertices = {
    {{-0.5f, -0.5f}, {1.0f, 0.0f, 0.0f}},  // 0: 좌하단 (빨강)
    {{ 0.5f, -0.5f}, {0.0f, 1.0f, 0.0f}},  // 1: 우하단 (초록)
    {{ 0.5f,  0.5f}, {0.0f, 0.0f, 1.0f}},  // 2: 우상단 (파랑)
    {{-0.5f,  0.5f}, {1.0f, 1.0f, 1.0f}}   // 3: 좌상단 (흰색)
};

// 2개의 삼각형을 구성하는 6개의 인덱스
const std::vector<uint16_t> indices = {
    0, 1, 2,  // 첫 번째 삼각형 (정점 0, 1, 2)
    2, 3, 0   // 두 번째 삼각형 (정점 2, 3, 0)
};
```

### 2.2. 인덱스 타입

| 타입 | 크기 | 최대 정점 수 |
|------|------|-------------|
| `uint16_t` | 2 bytes | 65,535 |
| `uint32_t` | 4 bytes | 4,294,967,295 |

**선택 기준:**

- 정점 수가 65,535개 이하: `uint16_t` 사용 (메모리 효율적)
- 정점 수가 65,535개 초과: `uint32_t` 사용

---

## 3. 인덱스 버퍼 생성

### 3.1. 멤버 변수 추가

```cpp
VkBuffer indexBuffer;
VkDeviceMemory indexBufferMemory;
```

### 3.2. 생성 흐름

인덱스 버퍼 생성은 정점 버퍼와 동일한 스테이징 버퍼 패턴을 따른다.

```plaintext
1. 버퍼 크기 계산
        |
        v
2. 스테이징 버퍼 생성 (HOST_VISIBLE)
        |
        v
3. CPU 데이터 --> 스테이징 버퍼
        |
        v
4. 인덱스 버퍼 생성 (DEVICE_LOCAL)
        |
        v
5. 스테이징 버퍼 --> 인덱스 버퍼
        |
        v
6. 스테이징 버퍼 소멸
```

### 3.3. createIndexBuffer 함수 구현

```cpp
void createIndexBuffer() {
    VkDeviceSize bufferSize = sizeof(indices[0]) * indices.size();

    // 1. 스테이징 버퍼 생성
    VkBuffer stagingBuffer;
    VkDeviceMemory stagingBufferMemory;
    createBuffer(bufferSize,
                 VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                 VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
                 stagingBuffer,
                 stagingBufferMemory);

    // 2. CPU --> 스테이징 버퍼 복사
    void* data;
    vkMapMemory(device, stagingBufferMemory, 0, bufferSize, 0, &data);
    memcpy(data, indices.data(), (size_t) bufferSize);
    vkUnmapMemory(device, stagingBufferMemory);

    // 3. 인덱스 버퍼 생성 (GPU 전용)
    createBuffer(bufferSize,
                 VK_BUFFER_USAGE_TRANSFER_DST_BIT | VK_BUFFER_USAGE_INDEX_BUFFER_BIT,
                 VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
                 indexBuffer,
                 indexBufferMemory);

    // 4. 스테이징 버퍼 --> 인덱스 버퍼 복사
    copyBuffer(stagingBuffer, indexBuffer, bufferSize);

    // 5. 스테이징 버퍼 정리
    vkDestroyBuffer(device, stagingBuffer, nullptr);
    vkFreeMemory(device, stagingBufferMemory, nullptr);
}
```

### 3.4. 버퍼 용도 플래그 비교

| 버퍼 종류 | 용도 플래그 |
|----------|------------|
| 스테이징 버퍼 | `VK_BUFFER_USAGE_TRANSFER_SRC_BIT` |
| 정점 버퍼 | `VK_BUFFER_USAGE_TRANSFER_DST_BIT` \| `VK_BUFFER_USAGE_VERTEX_BUFFER_BIT` |
| 인덱스 버퍼 | `VK_BUFFER_USAGE_TRANSFER_DST_BIT` \| `VK_BUFFER_USAGE_INDEX_BUFFER_BIT` |

---

## 4. 인덱스 버퍼 바인딩

### 4.1. vkCmdBindIndexBuffer

렌더 패스 내에서 인덱스 버퍼를 바인딩한다.

```cpp
// 커맨드 버퍼 기록 중...
vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, graphicsPipeline);

VkBuffer vertexBuffers[] = {vertexBuffer};
VkDeviceSize offsets[] = {0};
vkCmdBindVertexBuffers(commandBuffer, 0, 1, vertexBuffers, offsets);

// 인덱스 버퍼 바인딩
vkCmdBindIndexBuffer(commandBuffer, indexBuffer, 0, VK_INDEX_TYPE_UINT16);
```

### 4.2. vkCmdBindIndexBuffer 매개변수

| 매개변수 | 설명 |
|---------|------|
| `commandBuffer` | 명령을 기록할 커맨드 버퍼 |
| `buffer` | 바인딩할 인덱스 버퍼 |
| `offset` | 인덱스 버퍼 내 시작 오프셋 (바이트) |
| `indexType` | 인덱스 데이터 타입 |

### 4.3. 인덱스 타입 상수

| 상수 | 대응 타입 |
|------|----------|
| `VK_INDEX_TYPE_UINT16` | `uint16_t` |
| `VK_INDEX_TYPE_UINT32` | `uint32_t` |

---

## 5. 인덱스 기반 드로잉

### 5.1. vkCmdDrawIndexed

`vkCmdDraw` 대신 `vkCmdDrawIndexed`를 사용한다.

```cpp
// 변경 전: 정점 기반 드로잉
// vkCmdDraw(commandBuffer, static_cast<uint32_t>(vertices.size()), 1, 0, 0);

// 변경 후: 인덱스 기반 드로잉
vkCmdDrawIndexed(commandBuffer, static_cast<uint32_t>(indices.size()), 1, 0, 0, 0);
```

### 5.2. vkCmdDrawIndexed 매개변수

```cpp
void vkCmdDrawIndexed(
    VkCommandBuffer commandBuffer,
    uint32_t        indexCount,
    uint32_t        instanceCount,
    uint32_t        firstIndex,
    int32_t         vertexOffset,
    uint32_t        firstInstance
);
```

| 매개변수 | 설명 |
|---------|------|
| `indexCount` | 그릴 인덱스 개수 |
| `instanceCount` | 인스턴스 개수 (일반적으로 1) |
| `firstIndex` | 인덱스 버퍼에서 시작할 위치 |
| `vertexOffset` | 정점 인덱스에 더해질 오프셋 |
| `firstInstance` | 첫 번째 인스턴스 ID |

### 5.3. vertexOffset 활용 예시

```plaintext
정점 버퍼: [모델A 정점들..., 모델B 정점들...]
                         ^
                         | vertexOffset = 모델A 정점 수

인덱스 버퍼에서 인덱스 0은 실제로 정점 버퍼의
(0 + vertexOffset) 위치를 참조
```

---

## 6. 리소스 정리

### 6.1. cleanup 함수에 추가

```cpp
void cleanup() {
    // ... 기존 정리 코드 ...

    vkDestroyBuffer(device, indexBuffer, nullptr);
    vkFreeMemory(device, indexBufferMemory, nullptr);

    vkDestroyBuffer(device, vertexBuffer, nullptr);
    vkFreeMemory(device, vertexBufferMemory, nullptr);

    // ... 나머지 정리 코드 ...
}
```

---

## 7. 전체 렌더링 흐름

```plaintext
초기화 단계:
createVertexBuffer()  --> 정점 데이터를 GPU로 전송
createIndexBuffer()   --> 인덱스 데이터를 GPU로 전송

렌더링 단계 (매 프레임):
vkCmdBeginRenderPass(...)
    |
    v
vkCmdBindPipeline(...)
    |
    v
vkCmdBindVertexBuffers(...)  --> 정점 버퍼 바인딩
    |
    v
vkCmdBindIndexBuffer(...)    --> 인덱스 버퍼 바인딩
    |
    v
vkCmdDrawIndexed(...)        --> 인덱스 기반 드로잉
    |
    v
vkCmdEndRenderPass(...)
```

---

## 8. 메모리 효율성 비교

### 8.1. 사각형 예시

| 방식 | 정점 데이터 | 인덱스 데이터 | 총 크기 |
|------|------------|--------------|--------|
| 인덱스 없음 | 6 x 20 bytes = 120 bytes | 없음 | 120 bytes |
| 인덱스 사용 | 4 x 20 bytes = 80 bytes | 6 x 2 bytes = 12 bytes | 92 bytes |

**절약률:** 약 23%

### 8.2. 복잡한 모델 예시 (10,000 삼각형)

| 방식 | 정점 데이터 | 인덱스 데이터 | 총 크기 |
|------|------------|--------------|--------|
| 인덱스 없음 | 30,000 x 32 bytes | 없음 | 960 KB |
| 인덱스 사용 | 10,000 x 32 bytes | 30,000 x 2 bytes | 380 KB |

**절약률:** 약 60%

---

## 9. 요약

| 항목 | 내용 |
|------|------|
| **목적** | 정점 데이터 재사용으로 메모리 절약 및 캐시 효율 향상 |
| **생성 방식** | 스테이징 버퍼 패턴 (정점 버퍼와 동일) |
| **버퍼 용도** | `VK_BUFFER_USAGE_INDEX_BUFFER_BIT` |
| **바인딩** | `vkCmdBindIndexBuffer()` |
| **드로잉** | `vkCmdDrawIndexed()` |
| **인덱스 타입** | `uint16_t` (65K 이하) 또는 `uint32_t` |

---

## 마치며

이 문서에서는 인덱스 버퍼를 사용하여 정점 데이터를 효율적으로 재사용하는 방법을 살펴보았다. 인덱스 버퍼는 메모리 절약과 GPU 캐시 효율성 향상에 필수적인 기능이며, 복잡한 3D 모델을 렌더링할 때 큰 성능 이점을 제공한다.

다음 편에서는 유니폼 버퍼(Uniform Buffer)와 디스크립터를 활용하여 셰이더에 변환 행렬 등의 데이터를 전달하는 방법을 다룰 예정이다.
