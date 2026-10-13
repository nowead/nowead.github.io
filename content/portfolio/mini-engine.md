---
title: "Mini-Engine"
date: 2025-09-01
lastmod: 2026-09-28
weight: 2
featured: true
category: "graphics"
category_label: "Rendering engine"
architecture: "multi-backend"
period: "2025.09 — 진행 중"
role: "엔진 설계 · 구현 · 통합"
tags: ["C++20", "Vulkan", "WebGPU", "Render Graph", "Volume Rendering"]
github: "https://github.com/nowead/Mini-Engine"
summary: "Vulkan 튜토리얼에서 시작해 PBR·GPU 기반 렌더링과 CT/MRI 볼륨 시각화까지 확장한 C++20 렌더링 엔진. 공통 RHI를 설계하고 대용량 볼륨의 메모리 사용을 최적화했습니다."
cover_image: "mini-engin-image/PBR+IBL.png"
image_alt: "Mini-Engine의 HDR 환경광 아래에서 렌더링한 PBR 재질 구체들"
image_caption: "PBR·IBL 재질 표현 실험. 엔진 개발 과정의 실제 렌더링 화면입니다."
highlights:
  - "Vulkan / WebGPU 공통 RHI"
  - "PBR · Render Graph · TAA"
  - "CT/MRI 볼륨 · Progressive DICOM"
---

## 렌더링 기법을 엔진으로 연결하다

Mini-Engine은 Vulkan 튜토리얼의 단일 애플리케이션에서 출발한 개인 렌더링 엔진 프로젝트입니다. 렌더링 기법을 구현하면서 **자원 관리와 패스 간 의존성을 정리하고, 새로운 기능을 추가할 수 있는 엔진 구조**로 발전시켰습니다.

현재는 Vulkan과 WebGPU 백엔드를 공유하는 PBR 장면 렌더러와 CT/MRI 볼륨 뷰어로 확장했습니다. 렌더링 품질뿐 아니라 자원 수명, 패스 의존성, 데이터 배치, 메모리 사용량을 함께 다루고 있습니다.

| 영역 | 구현 내용 |
| --- | --- |
| 언어·환경 | C++20, GLSL/WGSL, CMake, Emscripten |
| 그래픽스 기반 | Vulkan / WebGPU, RHI, Render Graph |
| 장면 렌더링 | Deferred PBR, IBL, 그림자, SSAO, Bloom, ACES, FXAA/TAA |
| 자산·GPU 작업 | glTF 2.0/glb, GPU frustum culling, indirect draw, GPU timestamp |
| 볼륨 시각화 | Ray marching, path tracing, 누적·A-trous denoising |
| 대용량 데이터 | Brick atlas, LRU/LOD streaming, NIfTI mmap, progressive DICOM |

## 01. 단일 애플리케이션에서 공통 RHI로

처음에는 디바이스 생성, swapchain, 렌더 루프와 자원 관리가 한 애플리케이션에 모여 있었습니다. 기능을 추가할수록 수정할 범위와 자원의 소유 관계를 파악하기 어려워졌습니다.

먼저 역할별 모듈로 나누고, 이후에는 **렌더링 의도와 그래픽스 API의 구체적인 작업을 분리**했습니다. Device, Buffer, Texture, Pipeline, CommandEncoder를 공통 인터페이스로 정의하고 Vulkan과 WebGPU가 각각 구현하도록 구성했습니다.

```text
Vulkan 튜토리얼
    ↓ 책임·자원 소유 관계 분리
렌더링 / 장면 / 자원 관리 모듈
    ↓ API별 구현 분리
공통 RHI + Vulkan / WebGPU 백엔드
    ↓ 같은 기반을 다른 문제에 적용
PBR 장면 렌더러 / CT·MRI 볼륨 뷰어
```

장면 렌더러와 볼륨 렌더러는 공통 그래픽스 기반을 사용하고, 파일 형식의 해석은 별도 로더가 담당합니다. DICOM 로더가 강도 데이터나 슬라이스 callback을 전달하면, 렌더러는 GPU 저장 방식과 시각화에 집중합니다.

Vulkan의 bindless textures와 병렬 shadow command recording은 백엔드 내부에서 처리하고, WebGPU에서는 브라우저의 파일 접근과 프레임 수명에 맞춰 자원을 관리합니다. **공통 인터페이스를 유지하면서 플랫폼별 처리 방식은 분리**했습니다.

## 02. 렌더링 패스와 자산 파이프라인 통합

장면 렌더러에는 Cook–Torrance PBR과 IBL을 시작으로 deferred G-buffer, 그림자, SSAO, Bloom, tone mapping, anti-aliasing을 연결했습니다. Render Graph는 패스의 자원 사용을 선언하고 의존성과 배리어를 관리합니다.

GPU frustum culling은 오브젝트 버퍼를 읽어 가시 인덱스와 indirect draw 데이터를 구성합니다. glTF는 cgltf로 파싱하고, `AssetImporter`에서 메시·머티리얼·텍스처를 엔진의 표현으로 변환합니다.

![Mini-Engine의 다중 오브젝트 렌더링 장면](/portfolio/mini-engin-image/mini-engine.png)

*다중 오브젝트와 PBR 재질을 표현한 렌더링 장면.*

TAA를 통합할 때는 모션 벡터와 프레임 간 히스토리 자원의 수명을 함께 다뤘습니다. 새로운 효과를 추가하는 작업이 셰이더 작성만으로 끝나지 않고, 기존 패스와 데이터 구조의 연결을 바꾸는 일임을 확인했습니다.

## 03. 대용량 볼륨의 메모리 문제 해결

CT/MRI 볼륨은 표면 메시와 다른 문제를 만듭니다. 입력 데이터, 변환 중간 버퍼, GPU atlas가 동시에 존재하면 **파일 크기보다 훨씬 큰 메모리 피크**가 발생합니다. 이를 줄이기 위해 native와 브라우저의 데이터 흐름을 각각 개선했습니다.

### Native: 전체 변환 버퍼를 피하는 NIfTI mmap

기존 경로는 int16 데이터를 float로 풀고 다시 half로 변환하면서 큰 중간 버퍼를 보유했습니다. mmap 소스에서 필요한 데이터를 읽어 brick을 패킹하도록 바꿔, 전체 float·half 변환 버퍼를 거치지 않는 경로를 추가했습니다.

| 측정 항목 | 기존 경로 | mmap 직접 패킹 |
| --- | ---: | ---: |
| 관측 peak working set | 6.57 GB | 2.30 GB |
| 정착 후 working set | 2.38 GB | 2.30 GB |

**1024³ 합성 int16 NIfTI의 streaming 경로에서 관측한 메모리 피크를 약 65% 줄였습니다.** Windows 11, RTX 4070, 시스템 RAM 32 GB 환경에서 프로세스 working set을 4초 간격으로 측정한 결과입니다.

### Browser: 슬라이스가 도착하는 대로 brick 업로드

브라우저 DICOM 로딩은 전체 볼륨의 half 버퍼를 모으는 대신, 슬라이스를 **66장 ring buffer**에 넣고 완성된 brick 행을 staging slab으로 업로드하도록 변경했습니다. 소비한 가상 파일도 해제해 불필요한 중복 보유를 줄였습니다.

```text
DICOM 메타데이터 확인·정렬
    → 슬라이스 디코드
    → Ring buffer
    → 완성된 brick 행 패킹
    → Staging slab / GPU atlas 업로드
```

iOS 18.7 Safari에서 **512³ 합성 CT를 로드**했습니다. 16-bit 데이터 기준 256 MiB의 볼륨을 처리하며, 전체 변환 버퍼를 한꺼번에 보유하지 않는 로딩 흐름을 적용했습니다.

얇거나 불규칙한 볼륨에는 축별 brick 크기와 마지막 brick 축소를 적용했습니다. 공개 DICOM 샘플 4종에서 dense 저장 대비 atlas의 추가 공간은 약 6% 이하였습니다.

Progressive DICOM은 Static atlas 경로에 연결하고, Streaming/LOD는 별도의 데이터 경로로 구성했습니다.

## 04. 측정으로 설계 판단을 확인하다

Vulkan의 shadow cascade 기록을 워커 스레드로 분산하고 A/B 측정을 추가했습니다. 그러나 테스트한 인스턴싱 장면에서는 커맨드 기록량이 적어 병렬화가 기록 시간의 이득으로 이어지지 않았습니다.

이 결과를 통해 **병렬 실행을 구현하는 일과 현재 장면의 병목을 해결하는 일은 별개의 판단**임을 확인했습니다. 기능 추가 뒤에는 측정 대상을 구분하고, 효과가 없었던 실험도 다음 설계의 근거로 남기고 있습니다.

메모리를 최적화할 때도 GPU atlas 할당량, 프로세스 working set, WASM heap을 나눠 측정해 어느 단계에서 비용이 발생하는지 추적했습니다.

## 05. 로더의 예외 처리와 회귀 테스트

ThreadPool과 NIfTI/raw·DICOM 로더에 회귀 테스트를 추가했습니다. 잘린 데이터, 음수 rescale, 슬라이스 정렬, float/half/progressive 결과 일치 등을 검사하고 CTest에 연결했습니다.

이 과정에서 NIfTI mmap 경로의 음수 slope에 따른 min/max 오류와 빌드 소스 누락, Windows WASM 스크립트의 종료 코드·산출물 경로 문제를 수정했습니다.

## 코드와 개발 기록

- [GitHub 소스 코드](https://github.com/nowead/Mini-Engine)
- [엔진 아키텍처](https://github.com/nowead/Mini-Engine/blob/main/docs/ARCHITECTURE.md)
- [NIfTI mmap · 메모리 측정 기록](https://github.com/nowead/Mini-Engine/blob/main/docs/current/medical-volume/baselines/BASELINE_2026-06-10_DISK_PAGING_STEP5.md)
