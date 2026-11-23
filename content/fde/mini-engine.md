---
title: "Mini-Engine"
date: 2025-09-01
lastmod: 2026-09-28
weight: 2
stage: "foundation"
track: "TRACK 01 · MEDICAL 3D"
category_label: "Rendering engine"
status: "개인 프로젝트 · 진행 중"
architecture: "multi-backend"
period: "2025.09 — 진행 중"
role: "1인 개발"
tags: ["C++20", "Vulkan", "WebGPU", "Render Graph", "Volume Rendering"]
github: "https://github.com/nowead/Mini-Engine"
summary: "Vulkan과 WebGPU가 공유하는 C++20 렌더링 엔진입니다. CT/MRI 볼륨 렌더링까지 확장하면서, 대용량 데이터의 메모리 문제를 측정으로 찾아 해결했습니다."
cover_image: "mini-engine-image/pbr-ibl.png"
cover_width: 1287
cover_height: 749
image_alt: "Mini-Engine의 HDR 환경광 아래에서 렌더링한 PBR 재질 구체들"
image_caption: "PBR·IBL 재질 표현 실험. 엔진 개발 과정의 실제 렌더링 화면입니다."
leads_to: "omnimed3d"
handoff:
  - "Vulkan·WebGPU 공통 RHI 설계 → C++20 렌더링 코어를 브라우저에 올리는 구조"
  - "CT/MRI 볼륨 렌더링과 DICOM 로더 → 볼륨 렌더링과 공유 DICOM 파서"
  - "메모리 피크를 측정하고 줄인 경험 → 저메모리 모드와 축소 업로드"
brief:
  problem:
    title: "파일보다 훨씬 큰 메모리 피크"
    text: "CT/MRI 볼륨을 불러올 때 입력 데이터, 변환 중간 버퍼, GPU 저장 공간이 동시에 존재해 메모리 사용량이 파일 크기의 몇 배로 커졌습니다."
  solution:
    title: "전체 버퍼를 만들지 않는 로딩 경로"
    text: "네이티브에서는 mmap 소스에서 바로 패킹하고, 브라우저에서는 슬라이스가 도착하는 대로 올리도록 데이터 흐름을 바꿨습니다."
  verification:
    title: "측정값과 회귀 테스트로 확인"
    text: "프로세스 메모리를 주기적으로 측정해 전후를 비교하고, 로더의 예외 상황을 회귀 테스트로 고정했습니다. 효과가 없던 실험도 기록했습니다."
metrics:
  - value: "6.57 → 2.30 GB"
    label: "1024³ 볼륨 로딩 메모리 피크"
  - value: "약 65%"
    label: "메모리 피크 감소"
  - value: "512³"
    label: "iOS Safari에서 불러온 합성 CT"
  - value: "2개"
    label: "공통 RHI 백엔드 · Vulkan / WebGPU"
---

## 프로젝트

Mini-Engine은 Vulkan 튜토리얼의 단일 애플리케이션에서 출발한 개인 렌더링 엔진입니다. 렌더링 기법을 구현하면서 자원 관리와 패스 간 의존성을 정리해, 새로운 기능을 추가할 수 있는 엔진 구조로 발전시켰습니다. 현재는 Vulkan과 WebGPU 백엔드를 공유하는 PBR 장면 렌더러와 CT/MRI 볼륨 뷰어로 확장했습니다.

| 영역 | 구현 내용 |
| --- | --- |
| 언어·환경 | C++20, GLSL/WGSL, CMake, Emscripten |
| 그래픽스 기반 | Vulkan / WebGPU, RHI, Render Graph |
| 장면 렌더링 | Deferred PBR, IBL, 그림자, SSAO, Bloom, ACES, FXAA/TAA |
| 볼륨 시각화 | Ray marching, path tracing, 누적·A-trous denoising |
| 대용량 데이터 | Brick atlas, LRU/LOD streaming, NIfTI mmap, progressive DICOM |

{{< shot src="mini-engine-image/mini-engine.png" alt="Mini-Engine의 다중 오브젝트 렌더링 장면" caption="다중 오브젝트와 PBR 재질을 표현한 렌더링 장면." width="1080" height="692" >}}

## 문제 정의

### 기능을 더할수록 수정 범위가 넓어졌다

처음에는 디바이스 생성, swapchain, 렌더 루프와 자원 관리가 한 애플리케이션에 모여 있었습니다. 기능을 추가할수록 수정할 범위와 자원의 소유 관계를 파악하기 어려워졌습니다. 브라우저에서도 같은 렌더러를 실행하려면, 렌더링 의도와 그래픽스 API의 구체적인 작업을 먼저 분리해야 했습니다.

### 볼륨 데이터는 파일보다 큰 메모리를 요구했다

CT/MRI 볼륨은 표면 메시와 다른 문제를 만듭니다. 입력 데이터, 변환 중간 버퍼, GPU atlas가 동시에 존재하면 **파일 크기보다 훨씬 큰 메모리 피크**가 발생합니다. "느리다"나 "무겁다"가 아니라, 어느 단계에서 메모리가 얼마나 잡히는지를 숫자로 정의하는 것부터 시작했습니다. GPU atlas 할당량, 프로세스 working set, WASM heap을 나눠 측정했습니다.

## 해결

### 공통 RHI: 렌더링 의도와 API 구현의 분리

Device, Buffer, Texture, Pipeline, CommandEncoder를 공통 인터페이스로 정의하고 Vulkan과 WebGPU가 각각 구현하도록 구성했습니다.

```text
Vulkan 튜토리얼
    ↓ 책임·자원 소유 관계 분리
렌더링 / 장면 / 자원 관리 모듈
    ↓ API별 구현 분리
공통 RHI + Vulkan / WebGPU 백엔드
    ↓ 같은 기반을 다른 문제에 적용
PBR 장면 렌더러 / CT·MRI 볼륨 뷰어
```

장면 렌더러와 볼륨 렌더러는 같은 그래픽스 기반을 사용하고, 파일 형식의 해석은 별도 로더가 담당합니다. DICOM 로더가 강도 데이터나 슬라이스 callback을 전달하면, 렌더러는 GPU 저장 방식과 시각화에 집중합니다.

{{< shot src="mini-engine-image/webgpu-example.png" alt="브라우저에서 실행한 Mini-Engine WebGPU 백엔드의 인스턴싱 테스트 화면" caption="같은 RHI 코드를 WebAssembly로 빌드해 브라우저에서 실행한 WebGPU 백엔드 테스트." width="1751" height="1284" >}}

### Native: 전체 변환 버퍼를 피하는 NIfTI mmap

기존 경로는 int16 데이터를 float로 풀고 다시 half로 변환하면서 큰 중간 버퍼를 보유했습니다. mmap 소스에서 필요한 데이터를 읽어 brick을 패킹하도록 바꿔, 전체 float·half 변환 버퍼를 거치지 않는 경로를 추가했습니다.

| 측정 항목 | 기존 경로 | mmap 직접 패킹 |
| --- | ---: | ---: |
| 관측 peak working set | 6.57 GB | 2.30 GB |
| 정착 후 working set | 2.38 GB | 2.30 GB |

**1024³ 합성 int16 NIfTI의 streaming 경로에서 관측한 메모리 피크를 약 65% 줄였습니다.** Windows 11, RTX 4070, 시스템 RAM 32 GB 환경에서 프로세스 working set을 4초 간격으로 측정한 결과입니다.

### Browser: 슬라이스가 도착하는 대로 올리기

브라우저 DICOM 로딩은 전체 볼륨의 half 버퍼를 모으는 대신, 슬라이스를 **66장 ring buffer**에 넣고 완성된 brick 행을 staging slab으로 올리도록 바꿨습니다. 소비한 가상 파일도 해제해 중복 보유를 줄였습니다.

```text
DICOM 메타데이터 확인·정렬
    → 슬라이스 디코드
    → Ring buffer
    → 완성된 brick 행 패킹
    → Staging slab / GPU atlas 업로드
```

iOS 18.7 Safari에서 **512³ 합성 CT를 불러왔습니다.** 16-bit 데이터 기준 256 MiB의 볼륨입니다. 얇거나 불규칙한 볼륨에는 축별 brick 크기와 마지막 brick 축소를 적용했고, 공개 DICOM 샘플 4종에서 dense 저장 대비 atlas의 추가 공간은 약 6% 이하였습니다.

## 검증

### 효과가 없던 실험도 기록한다

Vulkan의 shadow cascade 기록을 워커 스레드로 분산하고 A/B 측정을 추가했습니다. 그러나 테스트한 인스턴싱 장면에서는 커맨드 기록량이 적어, 병렬화가 기록 시간의 이득으로 이어지지 않았습니다.

**병렬 실행을 구현하는 일과 현재 장면의 병목을 해결하는 일은 별개의 판단**임을 확인했습니다. 기능을 추가한 뒤에는 측정 대상을 구분하고, 효과가 없던 실험도 다음 설계의 근거로 남깁니다.

### 로더의 예외 상황을 회귀 테스트로

ThreadPool과 NIfTI/raw·DICOM 로더에 회귀 테스트를 추가하고 CTest에 연결했습니다. 잘린 데이터, 음수 rescale, 슬라이스 정렬, float/half/progressive 경로의 결과 일치를 검사합니다.

테스트가 실제로 찾아낸 문제는 다음과 같습니다.

- NIfTI mmap 경로에서 음수 slope일 때 min/max가 잘못 계산되는 오류
- 빌드 대상에서 누락된 소스 파일
- Windows WASM 빌드 스크립트의 종료 코드와 산출물 경로 문제

## OmniMed3D로 이어진 것

[OmniMed3D](/fde/omnimed3d/)는 팀 프로젝트이고 사용자가 있는 제품입니다. 이 엔진에서 혼자 먼저 만들고 측정해 본 것들이 그 프로젝트에서 판단의 근거가 됐습니다.

- **공통 RHI** — Vulkan과 WebGPU를 함께 지원하도록 설계한 경험이, C++20 렌더링 코어를 WebAssembly로 빌드해 브라우저 GPU에서 실행하는 구조로 이어졌습니다.
- **볼륨 렌더링과 DICOM** — ray marching과 DICOM 로더를 먼저 구현해 보았기 때문에, 슬라이스 정렬과 방향 정규화 같은 문제를 미리 알고 시작했습니다.
- **메모리 측정** — 메모리 피크가 어디서 생기는지 측정해 본 경험이, 사양이 낮은 기기를 위한 저메모리 모드와 축소 업로드를 설계하는 근거가 됐습니다.

## 코드와 개발 기록

- [GitHub 소스 코드](https://github.com/nowead/Mini-Engine)
- [엔진 아키텍처](https://github.com/nowead/Mini-Engine/blob/main/docs/ARCHITECTURE.md)
- [NIfTI mmap · 메모리 측정 기록](https://github.com/nowead/Mini-Engine/blob/main/docs/current/medical-volume/baselines/BASELINE_2026-06-10_DISK_PAGING_STEP5.md)
