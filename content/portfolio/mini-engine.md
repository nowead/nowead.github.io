---
title: "Mini-Engine - Multi-Backend Rendering Engine"
date: 2025-09-01  
weight: 1
tags: ["C++20", "Vulkan", "WebGPU", "PBR", "RHI", "Graphics"]
github: "https://github.com/nowead/Mini-Engine"
summary: "RHI 기반 멀티 백엔드 렌더링 엔진 - Vulkan 1.3 & WebGPU 지원"
---

## 프로젝트 개요

Mini-Engine은 C++20로 구현된 현대적인 멀티 백엔드 렌더링 엔진으로, **RHI**(Render Hardware Interface) 아키텍처를 통해 Vulkan, WebGPU, DirectX 12, Metal 백엔드를 지원하도록 설계되었습니다. Vulkan-tutorial.com의 학습 자료에서 시작하여 확장 가능한 엔진 아키텍처로 발전했습니다.

## 핵심 기술 스택

- **언어:** C++20
- **그래픽 API:** Vulkan 1.3, WebGPU, DirectX 12 (예정), Metal (예정)
- **렌더링:** **PBR**(Physically Based Rendering), **IBL**(Image Based Lighting), GPU-Driven Rendering
- **빌드 시스템:** CMake 3.28+, Emscripten (WebAssembly)
- **플랫폼:** Linux, macOS, Windows, Web (WASM)

## 주요 기능

### 1. **RHI**(Render Hardware Interface) 아키텍처

15개의 순수 추상 인터페이스로 구성된 RHI 레이어를 통해 플랫폼 독립적인 렌더링을 구현:

```cpp
// RHI 추상화 예시
class RHIDevice;
class RHISwapchain;
class RHIPipeline;
class RHIBuffer;
class RHITexture;
// ... 15개 인터페이스
```

**계층 구조:**
```plaintext
- Layer 1: Application (플랫폼 독립적)
- Layer 2: High-Level Subsystems (API 독립적)
- Layer 3: RHI Abstractions (15개 인터페이스)
- Layer 4: Backend Implementations (Vulkan, WebGPU)
```

### 2. 물리 기반 렌더링 **PBR**(Physically Based Rendering)

**Cook-Torrance BRDF 구현:**
- Metallic/Roughness 워크플로우
- **NDF**(Normal Distribution Function) - GGX
- Fresnel-Schlick 근사
- Smith Geometry Function

**IBL**(Image Based Lighting):
- HDR 환경 맵 지원
- **Irradiance Convolution**(확산 조명)
- **Prefiltered Specular**(반사 조명)
- BRDF Integration LUT

### 3. GPU-Driven 렌더링

**성능 최적화:**
```cpp
// SSBO 기반 per-object 데이터
struct ObjectData {
    mat4 model;
    vec4 color;
    uint materialIndex;
    // 128 바이트 정렬
};

// Compute Shader Frustum Culling
layout(local_size_x = 256) in;
void main() {
    // AABB-plane test
    // Atomic indirect draw count
}
```

**성능 지표:**
- 100,000+ 오브젝트 @ 60 FPS
- Indirect Drawing으로 단일 드로우콜
- Compute Shader 기반 Frustum Culling

### 4. 멀티 백엔드 지원

#### Vulkan 1.3 Backend (완성)
- **VMA**(Vulkan Memory Allocator) 통합
- SPIR-V 셰이더 컴파일
- **Dynamic Rendering**(macOS/Windows)
- Layout Transition 자동 관리

#### WebGPU Backend (완성)
- Emscripten WASM 빌드
- SPIR-V -> WGSL 자동 변환
- 브라우저 WebGPU API 활용
- 185KB WASM 번들 크기

## 개발 과정 및 리팩터링

### Phase 1-7: Monolith to Layered Architecture

단일 파일 **main.cpp**(main.cpp) 구조에서 20+ 재사용 가능한 클래스로 분리:

**개선 지표:**
| 메트릭 | Before | After | 개선도 |
|--------|--------|-------|--------|
| 파일 수 | 1 | 50+ | 모듈화 |
| 클래스 수 | 0 | 20+ | 재사용성 |
| RAII 커버리지 | None | 100% | 메모리 안전 |
| 플랫폼 | 1 | 3+ | 크로스 플랫폼 |

### Phase 8-9: RHI Migration

완전한 플랫폼 독립 달성:

- Vulkan 의존성 제거 **Application Layer**(Application Layer)
- TextureLayout enum 추가
- Layout Transition 메소드 구현
- Zero Platform Leakage 달성

## 프로젝트 통계

```plaintext
총 코드 라인: ~24,900 LOC
- Vulkan Backend: ~8,000 LOC
- WebGPU Backend: ~6,500 LOC
- RHI Abstraction: ~400 LOC
- Application: ~9,000 LOC

파일 수: 100+
클래스 수: 20+
```

## 빌드 및 실행

### Desktop (Vulkan)
```bash
cmake --preset linux-default
make build
./build/vulkanGLFW
```

### Web (WebGPU)
```bash
make setup-emscripten  # 자동 Emscripten 설치
make wasm              # WASM 빌드
make serve-wasm        # http://localhost:8000
```

## 핵심 설계 원칙

1. **API Abstraction:** 그래픽 API가 백엔드 구현에만 격리
2. **Dependency Rule:** 상위 레이어는 RHI 추상화에만 의존
3. **Single Responsibility:** 각 클래스는 하나의 명확한 책임
4. **RAII:** `vk::raii::*` 래퍼를 통한 자동 리소스 관리
5. **Zero-Cost Abstraction:** 가상 함수 오버헤드 < 5%

## 향후 계획

- [ ] DirectX 12 Backend 구현
- [ ] Metal Backend 구현  
- [ ] 고급 애니메이션 시스템
- [ ] Scene Graph 최적화
- [ ] 물리 엔진 통합

## 기술 문서

- [프로젝트 요약](https://github.com/nowead/Mini-Engine/blob/main/docs/SUMMARY.md)
- [RHI 아키텍처](https://github.com/nowead/Mini-Engine/blob/main/docs/refactoring/layered-to-rhi/ARCHITECTURE.md)
- [WebGPU Backend](https://github.com/nowead/Mini-Engine/blob/main/docs/refactoring/webgpu-backend/SUMMARY.md)
- [빌드 가이드](https://github.com/nowead/Mini-Engine/blob/main/docs/BUILD_GUIDE.md)

---

**개발 기간:** 2025.09 ~ (진행 중)  
**주요 기술:** C++20, Vulkan 1.3, WebGPU, PBR, IBL, GPU-Driven Rendering, RAII, RHI Pattern
