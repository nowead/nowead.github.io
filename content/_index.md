+++
title = "Home"
+++

<div class="about-header">

# 민대원

**Graphics & Game Engine Developer**

그래픽스와 게임 엔진 아키텍처를 전문으로 합니다.

</div>

<div class="about-section">

## 주요 프로젝트

### Mini-Engine: PBR & GPU-Driven 렌더링 엔진
- **RHI 멀티 백엔드 아키텍처**: Vulkan 1.3 + WebGPU 크로스 플랫폼 지원
- **Cook-Torrance PBR**: 물리 기반 렌더링 (GGX, Smith Geometry, Fresnel-Schlick)
- **Image Based Lighting**: HDR 환경맵 기반 IBL 파이프라인
- **GPU-Driven Rendering**: Compute Shader Frustum Culling + Indirect Draw
- **100,000+ 오브젝트** 실시간 렌더링 지원
- **GPU 프로파일링**: Timestamp Query 기반 per-pass 타이밍 측정
- **상세 문서**: [GitHub](https://github.com/nowead/Mini-Engine)

</div>

<div class="about-section">

## 기술 스택

**Graphics APIs**
- Vulkan 1.3
- WebGPU

**Programming Languages**
- C++20
- C
- Python

**Graphics Libraries & Tools**
- GLFW, GLM, STB
- Vulkan Memory Allocator (VMA)
- ImGui
- Compute Shaders (GLSL, WGSL)

**Build System & Development**
- CMake 3.28+, vcpkg
- Git
- Linux
- Vim, GDB, Valgrind
- Docker, Emscripten (WebAssembly)

</div>

<div class="about-section">

## 기술 스킬

### 그래픽스 렌더링
- **Physically Based Rendering (PBR)**: Cook-Torrance BRDF, Metallic/Roughness Workflow
- **Image Based Lighting (IBL)**: HDR Environment Maps, Irradiance Convolution, Prefiltered Specular, BRDF LUT
- **Shadow Mapping**: Directional Light PCF Shadows
- **Tone Mapping**: ACES Filmic Tonemapping

### GPU 최적화 & 렌더링 아키텍처
- **GPU-Driven Rendering**: SSBO-based Object Data, Compute Shader Frustum Culling, Indirect Draw
- **대규모 씬 처리**: 100,000+ 오브젝트 실시간 렌더링
- **GPU 프로파일링**: Timestamp Queries, Per-pass Performance Measurement
- **메모리 최적화**: Transient Resources, Memory Aliasing
- **비동기 컴퓨트**: Timeline Semaphores, Dedicated Compute Queue

### 엔진 아키텍처
- **RHI (Render Hardware Interface) 패턴**: 그래픽스 API 추상화 계층 설계
- **멀티 백엔드 지원**: Vulkan, WebGPU 백엔드 구현
- **RAII 패턴**: 안전한 리소스 관리
- **크로스 플랫폼**: Linux, macOS (MoltenVK), Web (WebAssembly)

### Vulkan API
- 렌더링 파이프라인 구축 및 최적화
- Descriptor Sets, Push Constants, Storage Buffers
- 동기화 (Semaphores, Fences, Timeline Semaphores)
- 메모리 관리 (VMA, Staging Buffers)
- Compute Pipelines

### 시스템 프로그래밍
- C++20 Modern Features
- CMake 크로스 플랫폼 빌드 시스템
- Linux 시스템 프로그래밍
- 네트워크 프로그래밍 (kqueue)
- 쉘 스크립팅 및 자동화

</div>

<div class="about-section">

## 전문 분야

### 물리 기반 렌더링 (PBR)
Cook-Torrance BRDF 기반 사실적인 재질 표현 및 IBL 파이프라인 구현

### GPU-Driven 렌더링
대규모 씬을 위한 Compute Shader 기반 Frustum Culling 및 Indirect Draw 최적화

### 게임 엔진 아키텍처
RHI 패턴 기반 멀티 백엔드 그래픽스 추상화 계층 설계 및 구현

### 크로스 플랫폼 그래픽스
Vulkan과 WebGPU를 통한 Desktop과 Web 환경 지원

</div>

<div class="about-section">

## 학력

**강원대학교** | 컴퓨터정보통신공학과
2015.03 ~ 2021.08
평점평균: 4.11 / 4.5

**42Seoul**
- Kadet (2023년 10월 ~)
- Transcender (2025년 8월 ~)

</div>

<div class="about-section">

## Contact

- **Email**: dwm951017@gmail.com
- **GitHub**: [github.com/nowead](https://github.com/nowead)

</div>