---
title: "Mini-Engine - Multi-Backend Rendering Engine"
date: 2025-09-01  
weight: 1
tags: ["C++20", "Vulkan", "WebGPU", "PBR", "RHI", "Graphics"]
github: "https://github.com/nowead/Mini-Engine"
summary: "467줄 단일 파일에서 25,000+ LOC PBR & GPU-Driven 엔진까지 — 4단계 아키텍처 진화 기록"
cover_image: "mini-engin-image/mini_engine_thumbnail.gif"
---

# Mini-Engine

> Vulkan Tutorial 단일 파일(467줄)에서 PBR & GPU-Driven 렌더링 엔진(25,000+ LOC)으로 진화

**C++20 | Vulkan 1.3 | WebGPU | GLSL/WGSL**

2025.09 ~ 2026.02 (5개월) | 1인 개발 | Linux, macOS, Windows, Web


---

## Overview

모놀리스 구조를 **RHI 기반 모듈형 아키텍처**로 진화시킨 자체 제작 렌더링 엔진.

**핵심 성과:** RHI 인터페이스 변경 **0건**으로 Vulkan -> WebGPU 백엔드 추가 완료

| 항목 | 내용 |
|------|------|
| **기술 스택** | C++20, Vulkan 1.3, WebGPU, GLSL/WGSL, CMake, vcpkg |
| **규모** | 25,000+ LOC, 50+ 클래스 |
| **플랫폼** | Linux, macOS, Windows, Web (WASM) |
| **주요 기능** | Cook-Torrance PBR, IBL, GPU Frustum Culling, Indirect Draw, Shadow Mapping |

**Motivation**: Vulkan Tutorial을 따라하며 "텍스처 하나 추가하려면 467줄 중 어디를 수정해야 하나?"라는 질문에 답할 수 없었음. 이 경험이 계기가 되어 확장 가능한 아키텍처 설계를 목표로 설정.

<div style="display: flex; gap: 10px; justify-content: center;">

<div style="flex: 1;">

![PBR + IBL Rendering](/portfolio/mini-engin-image/PBR+IBL.png)

*PBR + IBL: Cook-Torrance 모델 + Image-Based Lighting으로 현실적인 금속 재질 표현*

</div>

<div style="flex: 1;">

![GPU-Driven Rendering](/portfolio/mini-engin-image/mini-engine.png)

*GPU-Driven: Instancing + Frustum Culling으로 대규모 빌딩 씬 렌더링*

</div>

</div>

---

## Stage 1: Architecture Evolution — Monolith에서 RHI까지

### What
467줄 단일 파일에서 RHI 기반 멀티 백엔드 아키텍처로 진화. **3번의 아키텍처 재설계**를 거쳐 최종 형태 도달.

```plaintext
Monolith (467 LOC)
  ↓ 11 Phases
Layered (25+ modules, 4-Layer)
  ↓ RHI Migration
RHI Architecture (15 interfaces, Vulkan Backend 3,650 LOC)
```

### Journey 1: Monolith -> Layered (기능 분리)
**목표:** 467줄 `main.cpp`를 재사용 가능한 모듈로 분리

**시행착오**:
```cpp
// 처음 시도: 기능별로 무작정 분리
Camera.cpp, Renderer.cpp, Scene.cpp, ...
-> 모듈간 순환 의존성 발생
-> Scene이 Renderer 참조, Renderer가 Scene 참조
```

**깨달음**: "기능"이 아니라 **"책임과 계층"**으로 분리해야 함.

**최종 구조** (4-Layer):
- **Application**: 사용자 입력, 카메라, ImGui
- **Rendering**: Scene, Renderer, Pipeline 관리
- **Resource**: Texture, Mesh, Material 로딩
- **Core**: 수학 라이브러리, 유틸리티

**규칙**: 상위 레이어만 하위 레이어 참조 가능 (단방향 의존성)

### Journey 2: Layered -> RHI (Vulkan 추상화 1차 시도)
**목표:** 상위 레이어에서 Vulkan 의존성 제거

**1차 시도: Vulkan 얇은 래핑**
```cpp
class VulkanWrapper {
    void createDescriptorSet(...);
    void updateDescriptorSet(...);
    void pipelineBarrier(...);
};
```
**문제:** Descriptor Set, Pipeline Barrier 같은 Vulkan 개념이 그대로 노출 -> 상위 레이어도 Vulkan 지식 필요 -> **추상화 실패**

**2차 시도: OpenGL 스타일 상태 머신**
```cpp
class GraphicsContext {
    void bindTexture(int slot, Texture* tex);
    void bindPipeline(Pipeline* pipeline);
    void draw(...);
};
```
**문제:** 
- 암묵적 상태 변경 -> "어느 함수에서 이 상태를 변경했지?" 디버깅 지옥
- 멀티스레드 렌더링 불가능 (전역 상태)

**깨달음:** 
1. Vulkan을 직접 래핑하면 추상화가 아니라 단순 감싸기
2. OpenGL 스타일은 모던 API와 맞지 않음
3. 업계 표준을 조사해야 함 -> Unreal, Unity의 RHI 패턴 발견

### Journey 3: RHI Pattern 채택 (최종)
**Why WebGPU 스타일?**
- Vulkan보다 **직관적** (Descriptor Set -> Bind Group)
- OpenGL보다 **명시적** (Command Encoder로 상태 캡슐화)
- 멀티 백엔드 확장에 **검증된 패턴**

**핵심 설계 결정:**
1. **Command Encoder 패턴:** 렌더 커맨드를 명시적으로 기록
```cpp
// OpenGL 스타일 (암묵적 상태)
bindTexture(0, texture);
draw();  // 어떤 텍스처를 쓰는지 불명확

// RHI 스타일 (명시적 커맨드)
encoder->setTexture(0, texture);
encoder->drawIndexed(...);  // 커맨드가 self-contained
```

2. **15개 인터페이스 설계**:
```cpp
class RHIDevice { /* 디바이스 생성, 리소스 팩토리 */ };
class RHICommandEncoder { /* 렌더 커맨드 기록 */ };
class RHIBuffer { /* 버퍼 추상화 */ };
class RHITexture { /* 텍스처 추상화 */ };
// ... 15개
```

3. **Layout Transition 자동화:**
```cpp
// Vulkan: 수동 barrier
vkCmdPipelineBarrier(..., VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, ...);

// RHI: 자동 추론
encoder->setTexture(0, texture);  // RHI가 SHADER_READ로 자동 전환
encoder->beginRenderPass(...);     // RHI가 COLOR_ATTACHMENT로 전환
```

### Challenge: Vulkan 동기화 버그
**문제:** `present()`가 렌더링 완료를 기다리지 않고 다음 프레임에서 세마포어를 **이중 시그널링** -> 크래시

**원인:** `frame-in-flight` 인덱스 (CPU 논리 프레임, `0~1`)와 `swapchain image` 인덱스 (GPU 물리 이미지, `0~N`)를 혼용

**해결:** RHI 인터페이스로 개념 분리
```cpp
class RHISwapchain {
    uint32_t m_currentFrame;       // 세마포어/펜스용 (0~1)
    uint32_t m_currentImageIndex;  // Framebuffer용 (0~N)
    
    RHISemaphore* acquireNextImage();  // 이미지 획득
    void present(RHISemaphore* wait);   // 세마포어 소비 명시
};
```

### Tradeoff: vtable 오버헤드 vs 확장성
**고민**: 가상 함수 호출이 성능에 영향을 주지 않을까?

**측정 결과**:
- Direct Vulkan call: 100 프레임 평균 **16.2ms**
- RHI interface call: 100 프레임 평균 **16.5ms**
- **오버헤드 < 2%** (vtable lookup + indirect call)

**결정**: 2%는 용인 가능. 멀티 백엔드 확장성이 더 중요.

### Impact
- Vulkan 종속성 제거 (상위 레이어 API 독립)
- 동기화 버그 **0건** (RHI가 복잡한 개념을 올바르게 추상화)
- WebGPU 백엔드 추가 시 RHI 수정 **0건** (추상화 검증 완료)

| 지표 | Monolith | Layered | RHI |
|------|----------|---------|-----|
| **코드 구조** | 467줄 단일 파일 | 25+ 모듈, 4-Layer | 15 interfaces + backends |
| **API 종속성** | Vulkan 100% | Vulkan 90% | **0%** (상위) |
| **플랫폼** | 단일 | 3개 | Linux, macOS, Windows, **Web** |
| **메모리 관리** | 수동 | RAII | RAII |

**교훈:**
- **3번의 시도 끝에 올바른 추상화 발견:** 직접 래핑과 모방은 실패, 업계 패턴 학습이 핵심
- **인터페이스 설계 > 구현:** RHI를 먼저 설계하고 Vulkan을 맞춤
- **Tradeoff는 측정으로 결정:** 가상 함수 오버헤드는 2%, 확장성은 무한대

**GPU Frustum Culling 최적화 효과:**

![16 Triangles](/portfolio/mini-engin-image/16.png)

*16 Triangles: 106 FPS - 경량 씬에서 컬링 효과 미미 (모든 객체 가시)*

![1K Triangles](/portfolio/mini-engin-image/1k.png)

*1,000 Triangles: 49.2 FPS (최적화 전 `~42 FPS`) - 약 17% 성능 향상*

![10K Triangles](/portfolio/mini-engin-image/10k.png)

*10,000 Triangles: 8.7 FPS (최적화 전 `~3.2 FPS`) - **약 2.7배 성능 향상***

![100K Triangles](/portfolio/mini-engin-image/100k.png)

*100,000 Triangles: 1.6 FPS (최적화 전 `~0.5 FPS`) - **약 3배+ 성능 향상***

> **최적화 핵심:** GPU 기반 Frustum Culling + Indirect Draw로 화면 밖 객체를 GPU에서 조기 제거. 대규모 씬에서 CPU->GPU 데이터 전송량 감소 및 렌더링 부하 최소화.

---

## Stage 2: WebGPU Backend — WASM 빌드 최적화

### What
RHI 아키텍처 검증을 위해 두 번째 백엔드 구현. 웹 브라우저에서 동일 엔진 실행 성공.

```plaintext
Vulkan Backend (3,650 LOC) + WebGPU Backend (6,500 LOC)
-> RHI 인터페이스 변경 0건
```

![WebGPU Backend](/portfolio/mini-engin-image/webgpu-example.png)

*WebGPU 백엔드: 동일한 RHI 코드로 WASM 빌드, 브라우저에서 실행*

### Challenge: WASM 빌드 "section too large" 실패
- **문제:** `WebGPUCommon.hpp`에 `~25개` enum 변환 inline 함수가 13개 .cpp에서 중복 인스턴스화 -> 코드 비대화
- **디버깅 과정:** `nm` 명령으로 심볼 분석 -> inline 함수가 각 translation unit마다 복제됨 발견

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
- 빌드 실패 -> 성공, **WASM 156KB** (gzip 후 `~40KB`)
- 모바일 환경에서도 즉시 로드 가능
- **교훈**: 헤더 inline 함수는 WASM에서 치명적

| 지표 | 결과 |
|------|------|
| **WebGPU Backend** | 15개 클래스, 6,500 LOC |
| **WASM 크기** | **156KB** |
| **RHI 수정** | **0건** (추상화 검증 완료) |
| **지원 플랫폼** | Linux, macOS, Windows, **Web** |

---

## Stage 3: GPU Instancing — Shadow Map 좌표계

### What
단일 OBJ 렌더러를 수천 개 오브젝트 처리 가능한 인스턴싱 엔진으로 확장. Shadow Mapping 추가.

```plaintext
Before: 1 object = 1 draw call (Blinn-Phong, 그림자 없음)
After:  N objects = 1 draw call (GPU Instancing, PCF Shadow)
```

### Challenge: Shadow Map이 씬 절반만 렌더링
- **문제:** Shadow map이 씬의 절반만 렌더링. 가까운 오브젝트 그림자 사라짐.
- **디버깅:** ImGui로 shadow map을 texture로 시각화 -> 절반이 검은색
- **원인:** `glm::ortho`는 OpenGL 스타일로 Z를 [-1, 1]로 매핑. Vulkan은 [0, 1] 기대 -> 음수 Z 클리핑

### Solution
Light projection matrix Z를 Vulkan NDC로 수동 변환:
```cpp
lightProj[2][2] = -1.0f / (farPlane - nearPlane);
lightProj[3][2] = -nearPlane / (farPlane - nearPlane);  // [0, 1]
```
추가: Shadow Pass에 **front-face culling** 적용 -> Peter Panning 제거 (bias 불필요)

### Impact
- 씬 전체를 커버하는 정확한 그림자
- **교훈:** OpenGL/Vulkan NDC 차이는 shadow, **IBL** 등에서 반복적으로 문제 발생. **시각화가 최고의 디버깅 도구**.

---

## Stage 4: PBR & GPU-Driven — CPU 병목 발견

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
- **문제:** Apple M1은 dedicated compute queue 없음. Timeline Semaphore 미지원 -> 크래시
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
- Frustum Culling **O(1)** (Compute Shader 병렬성 입증)
- **GPU 530ms << Frame 2022ms** -> ObjectData 생성이 CPU 병목
- **다음 최적화:** Persistent SSBO + dirty tracking

![1K Objects](/portfolio/mini-engin-image/1k.png)
*1K 오브젝트 (47 FPS)*

![10K Objects](/portfolio/mini-engin-image/10k.png)
*10K 오브젝트 (8 FPS)*

![100K Objects](/portfolio/mini-engin-image/100k.png)
*100K 오브젝트 (0.5 FPS) — GPU 530ms vs Frame 2022ms: CPU 병목 입증*

### Impact
- Cook-Torrance PBR + IBL 구현 완료
- GPU-Driven으로 100K+ 오브젝트 처리
- **교훈:** GPU를 빠르게 만들수록 CPU 병목이 더 선명하게 드러남. 측정 없이는 추측만 할 뿐.

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
  │ `~8,000 LOC`    │ `~6,500 LOC`     │
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
- **3번의 시도 끝에 WebGPU 스타일 채택:** Vulkan 직접 래핑, OpenGL 상태 머신 모두 실패 -> Command Encoder 패턴
- **Tradeoff 이해:** vtable 오버헤드 2% vs 멀티 백엔드 확장성 -> 후자 선택, RHI 수정 0건으로 검증

### Problem Solving
- **문서만으로는 부족:** Vulkan 동기화, NDC 좌표계 모두 크래시를 겪고 나서야 이해
- **시각화가 디버깅의 핵심:** ImGui로 shadow map 렌더링하여 문제 즉시 파악
- **하드웨어 다양성 대응:** M1 workgroup size, compute queue 크래시 경험 -> 모든 고급 기능에 capability check 추가

### Performance
- **측정 없이는 추측만 할 뿐:** GPU Profiler로 정량화 -> 100K에서 CPU가 진짜 병목임을 발견
- **GPU-Driven의 역설:** GPU를 빠르게 만들수록 CPU 병목이 더 선명하게 드러남

---

*개발 기간: 2025.09 ~ 2026.02