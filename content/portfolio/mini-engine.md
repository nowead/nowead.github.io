---
title: "Mini-Engine - Multi-Backend Rendering Engine"
date: 2025-09-01  
weight: 1
tags: ["C++20", "Vulkan", "WebGPU", "PBR", "RHI", "Graphics"]
github: "https://github.com/nowead/Mini-Engine"
summary: "467줄 단일 파일에서 25,000+ LOC PBR & GPU-Driven 엔진까지 — 5단계 아키텍처 진화 기록"
cover_image: "mini-engin-image/mini_engine_thumbnail.gif"
---

# Mini-Engine

> Vulkan Tutorial 단일 파일(467줄)에서 PBR & GPU-Driven 렌더링 엔진(25,000+ LOC)으로 진화

**C++20 | Vulkan 1.3 | WebGPU | GLSL/WGSL**

2025.09 ~ 2026.02 (5개월) | 1인 개발 | Linux, macOS, Windows, Web


---

## Overview

모놀리스 구조를 **RHI 기반 모듈형 아키텍처**로 진화시킨 자체 제작 렌더링 엔진.

**핵심 성과**: RHI 인터페이스 변경 **0건**으로 Vulkan → WebGPU 백엔드 추가 완료

| 항목 | 내용 |
|------|------|
| **기술 스택** | C++20, Vulkan 1.3, WebGPU, GLSL/WGSL, CMake, vcpkg |
| **규모** | 25,000+ LOC, 50+ 클래스 |
| **플랫폼** | Linux, macOS, Windows, Web (WASM) |
| **주요 기능** | Cook-Torrance PBR, IBL, GPU Frustum Culling, Indirect Draw, Shadow Mapping |

**Motivation**: Vulkan Tutorial을 따라하며 **"텍스처 하나 추가하려면 467줄 중 어디를 수정해야 하나?"**라는 질문에 답할 수 없었음. 이 경험이 계기가 되어 확장 가능한 아키텍처 설계를 목표로 설정.

---

## Stage 1: Layered Architecture — 크로스 플랫폼 지원

### What
467줄 단일 파일(`main.cpp`)에서 4-Layer 아키텍처로 전환. 11개 Phase에 걸쳐 점진적 분리.

```plaintext
Before: main.cpp (467 LOC, 모든 로직)
After:  Application → Rendering → Resource → Core (4-Layer, RAII 100%)
```

### Challenge: 플랫폼별 Vulkan 버전 차이
- **문제**: Linux는 Vulkan 1.1만 지원 (lavapipe), macOS/Windows는 1.3 지원. Dynamic Rendering API가 Linux에서 크래시.
- **선택지**:
  1. 최하위 버전(1.1)으로 통일 → 최신 기능 포기
  2. 플랫폼별 최적 경로 선택 → 코드 분기

### Solution
플랫폼별 최선의 API 경로 선택:
```cpp
#ifdef __linux__
    vkCmdBeginRenderPass(...);  // Traditional Render Pass (1.1)
#else
    vkCmdBeginRendering(...);    // Dynamic Rendering (1.3)
#endif
```

### Impact
- 단일 코드베이스로 3개 플랫폼 지원
- 각 플랫폼에서 최신 API 활용 가능
- **교훈**: "최하위 공통분모"가 항상 답은 아님

| 지표 | Before | After |
|------|--------|-------|
| **코드 구조** | 467줄 단일 파일 | 25+ 모듈, 4-Layer |
| **메모리 관리** | 수동 alloc/free | **RAII 100%** |
| **플랫폼** | 단일 | **Linux, macOS, Windows** |

---

## Stage 2: RHI Architecture — 멀티 백엔드 기반

### What
Vulkan 종속 코드를 **15개 추상 인터페이스**로 분리. WebGPU 스타일 API 설계.

```plaintext
Before: Renderer → Vulkan API (직접 호출)
After:  Renderer → RHI (15 interfaces) → Vulkan Backend (3,650 LOC)
```

### Design Journey: 3번의 시도
1. **Vulkan 얇은 래핑**: Descriptor Set, Pipeline Barrier 등 Vulkan 개념 그대로 노출 → 상위 레이어도 Vulkan 지식 필요 → **실패**
2. **OpenGL 상태 머신**: `bindTexture(slot, texture)` 암묵적 상태 관리 → "어디서 이 상태를 변경했지?" 디버깅 지옥 → **폐기**
3. **WebGPU Command Encoder 패턴** → **채택** (Vulkan보다 직관적, OpenGL보다 명시적)

### Challenge: Vulkan 동기화 버그
- **문제**: `present()`가 렌더링 완료를 기다리지 않고 다음 프레임에서 세마포어를 **이중 시그널링** → 크래시
- **원인**: `frame-in-flight` 인덱스 (0~1)와 `swapchain image` 인덱스 (0~N)를 혼용

### Solution
두 개념을 명확히 분리:
```cpp
class VulkanRHISwapchain {
    uint32_t m_currentFrame;       // 세마포어/펜스 (0~1)
    uint32_t m_currentImageIndex;  // Framebuffer (0~N)
};
// present(RHISemaphore*) 인터페이스로 세마포어 소비 명시
```

### Impact
- 동기화 버그 **0건**
- RHI가 Vulkan의 복잡한 동기화 개념을 올바르게 추상화했음을 검증
- **교훈**: 문서만 읽고는 부족, 크래시를 겪어야 이해

| 지표 | Before | After |
|------|--------|-------|
| **API 종속성** | Vulkan 100% | **0% (상위 레이어)** |
| **vtable 오버헤드** | - | **< 2%** |

---

## Stage 3: WebGPU Backend — WASM 빌드 최적화

### What
RHI 아키텍처 검증을 위해 두 번째 백엔드 구현. 웹 브라우저에서 동일 엔진 실행 성공.

```plaintext
Vulkan Backend (3,650 LOC) + WebGPU Backend (6,500 LOC)
→ RHI 인터페이스 변경 0건
```

### Challenge: WASM 빌드 "section too large" 실패
- **문제**: `WebGPUCommon.hpp`에 ~25개 enum 변환 inline 함수가 13개 .cpp에서 중복 인스턴스화 → 코드 비대화
- **디버깅 과정**: `nm` 명령으로 심볼 분석 → inline 함수가 각 translation unit마다 복제됨 발견

### Solution
선언/구현 분리 + Emscripten 최적화:
```cpp
// Before: WebGPUCommon.hpp
inline WGPUTextureFormat toWGPUFormat(...) { ... }  // 13개 .cpp마다 복제

// After: WebGPUCommon.cpp
WGPUTextureFormat toWGPUFormat(...) { ... }  // 단일 인스턴스
```
```bash
-Oz -flto  # 크기 최적화 + Link-Time Optimization
```

### Impact
- 빌드 실패 → 성공, **WASM 156KB** (gzip 후 ~40KB)
- 모바일 환경에서도 즉시 로드 가능
- **교훈**: 헤더 inline 함수는 WASM에서 치명적

| 지표 | 결과 |
|------|------|
| **WebGPU Backend** | 15개 클래스, 6,500 LOC |
| **WASM 크기** | **156KB** |
| **RHI 수정** | **0건** (추상화 검증 완료) |
| **지원 플랫폼** | Linux, macOS, Windows, **Web** |

---

## Stage 4: GPU Instancing — Shadow Map 좌표계

### What
단일 OBJ 렌더러를 수천 개 오브젝트 처리 가능한 인스턴싱 엔진으로 확장. Shadow Mapping 추가.

```plaintext
Before: 1 object = 1 draw call (Blinn-Phong, 그림자 없음)
After:  N objects = 1 draw call (GPU Instancing, PCF Shadow)
```

### Challenge: Shadow Map이 씬 절반만 렌더링
- **문제**: Shadow map이 씬의 절반만 렌더링. 가까운 오브젝트 그림자 사라짐.
- **디버깅**: ImGui로 shadow map을 texture로 시각화 → 절반이 검은색
- **원인**: `glm::ortho`는 OpenGL 스타일로 Z를 [-1, 1]로 매핑. Vulkan은 [0, 1] 기대 → 음수 Z 클리핑

### Solution
Light projection matrix Z를 Vulkan NDC로 수동 변환:
```cpp
lightProj[2][2] = -1.0f / (farPlane - nearPlane);
lightProj[3][2] = -nearPlane / (farPlane - nearPlane);  // [0, 1]
```
추가: Shadow Pass에 **front-face culling** 적용 → Peter Panning 제거 (bias 불필요)

### Impact
- 씬 전체를 커버하는 정확한 그림자
- **교훈**: OpenGL/Vulkan NDC 차이는 shadow, IBL 등에서 반복적으로 문제 발생. **시각화가 최고의 디버깅 도구**.

---

## Stage 5: PBR & GPU-Driven — CPU 병목 발견

### What
Blinn-Phong을 **Cook-Torrance PBR + IBL**로 교체. CPU 드라이브 인스턴싱을 **GPU-Driven 간접 렌더링**으로 전환.

```plaintext
Before: CPU가 draw call 발행 (Blinn-Phong)
After:  GPU가 draw call 결정 (PBR + IBL + Frustum Culling + Indirect Draw)
```

**구현**: Compute Shader Frustum Culling + Atomic Indirect Draw
```glsl
// 64 threads parallel
for (int i = 0; i < 6; i++) {  // 6개 frustum plane
    if (isAABBOutsidePlane(frustumPlanes[i], bboxMin, bboxMax)) {
        visible = false; break;
    }
}
if (visible) atomicAdd(indirect.instanceCount, 1);  // GPU가 결정
```

### Challenge 1: Async Compute 하드웨어 폴백
- **문제**: Apple M1은 dedicated compute queue 없음. Timeline Semaphore 미지원 → 크래시
- **해결**: Capability check + fallback
```cpp
if (features.dedicatedComputeQueue && features.timelineSemaphores) {
    // Async compute on dedicated queue
} else {
    // Fallback: inline compute on graphics queue
}
```

### Challenge 2: 100K 오브젝트에서 CPU 병목 발견
GPU Profiling으로 측정한 결과 **CPU가 진짜 병목**:

| 오브젝트 | Frustum (ms) | Shadow (ms) | Main (ms) | GPU Total (ms) | Frame (ms) |
|---------|-------------|-------------|-----------|---------------|------------|
| **1K** | 1 | 6 | 10 | 17 | 21 |
| **10K** | 1 | 34 | 61 | 95 | 125 |
| **100K** | 2 | 193 | 329 | **530** | **2022** |

**Discovery**:
- Frustum Culling **O(1)** — Compute Shader 병렬성 입증
- **GPU 530ms << Frame 2022ms** → ObjectData 생성이 CPU 병목
- **다음 최적화**: Persistent SSBO + dirty tracking

![1K Objects](mini-engin-image/1k.png)
*1K 오브젝트 (47 FPS)*

![10K Objects](mini-engin-image/10k.png)
*10K 오브젝트 (8 FPS)*

![100K Objects](mini-engin-image/100k.png)
*100K 오브젝트 (0.5 FPS) — GPU 530ms vs Frame 2022ms: CPU 병목 입증*

### Impact
- Cook-Torrance PBR + IBL 구현 완료
- GPU-Driven으로 100K+ 오브젝트 처리
- **교훈**: GPU를 빠르게 만들수록 CPU 병목이 더 선명하게 드러남. 측정 없이는 추측만 할 뿐.

---

## 최종 아키텍처

```plaintext
Application Layer (플랫폼 독립적)
  Application, Camera, Input, ImGui (PBR controls, GPU timing)
      ↓
High-Level Subsystems (API 독립적)
  Renderer, IBLManager, ShadowRenderer, ResourceManager
      ↓
RHI (15개 추상 인터페이스)
  RHIDevice, RHICommandEncoder, RHIBuffer, RHIPipeline, ...
      ↓
Backend Implementations
  ┌─────────────────┬──────────────────┐
  │ Vulkan Backend  │ WebGPU Backend   │
  │ VMA, SPIR-V     │ Emscripten, WGSL │
  │ ~8,000 LOC      │ ~6,500 LOC       │
  └─────────────────┴──────────────────┘
```

---

## 전체 성과

| 지표 | 시작점 | 최종 |
|------|--------|------|
| **코드 구조** | 467줄 단일 파일 | 25,000+ LOC, 50+ 클래스 |
| **그래픽스 API** | Vulkan only | Vulkan + WebGPU |
| **렌더링** | Blinn-Phong | Cook-Torrance PBR + IBL |
| **오브젝트** | 단일 모델 | 100K+ GPU-Driven Indirect Draw |
| **Culling** | 없음 | GPU Frustum Culling (Compute Shader) |
| **플랫폼** | 단일 | Linux, macOS, Windows, Web |

---

## Key Takeaways

### Design
- **3번의 시도 끝에 WebGPU 스타일 채택**: Vulkan 직접 래핑, OpenGL 상태 머신 모두 실패 → Command Encoder 패턴
- **Tradeoff 이해**: vtable 오버헤드 2% vs 멀티 백엔드 확장성 → 후자 선택, RHI 수정 0건으로 검증

### Problem Solving
- **문서만으로는 부족**: Vulkan 동기화, NDC 좌표계 모두 크래시를 겪고 나서야 이해
- **시각화가 디버깅의 핵심**: ImGui로 shadow map 렌더링하여 문제 즉시 파악
- **하드웨어 다양성 대응**: M1 workgroup size, compute queue 크래시 경험 → 모든 고급 기능에 capability check 추가

### Performance
- **측정 없이는 추측만 할 뿐**: GPU Profiler로 정량화 → 100K에서 CPU가 진짜 병목임을 발견
- **GPU-Driven의 역설**: GPU를 빠르게 만들수록 CPU 병목이 더 선명하게 드러남

---

*개발 기간: 2025.09 ~ 2026.02 | 문서 작성: 2026-02-10*