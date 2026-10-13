---
title: "OmniMed3D"
date: 2026-10-08
lastmod: 2026-10-08
weight: 1
featured: true
category: "graphics"
category_label: "Browser medical imaging"
tags: ["C++20", "WebGPU", "WebAssembly", "Slang", "TypeScript", "DICOM"]
role: "3D 렌더링 · DICOM 처리"
period: "2026"
github: "https://github.com/OmniMed3D/omnimed3d"
demo: "https://omnimed3d.pages.dev/app/?demo=LIDC-IDRI-0001"
website: "https://omnimed3d.pages.dev/"
summary: "DICOM 파싱부터 3D 볼륨 렌더링과 폐 분할 결과 표시까지, 브라우저 안에서 연결한 의료 영상 연구 프로토타입."
cover_image: "omnimed3d-image/segmentation.jpg"
image_alt: "OmniMed3D에서 흉부 CT와 붉은 폐 분할 마스크를 함께 렌더링한 실제 화면"
image_caption: "공개·비식별 흉부 CT 데모. 붉은 영역은 lungmask R231 모델의 폐 분할 결과입니다."
highlights:
  - "C++20 → WASM 렌더링 코어"
  - "WebGPU 볼륨 렌더링 · MPR"
  - "DICOM 파싱 · 좌표 정규화"
---

## 브라우저 안에 의료 영상 파이프라인을 만들다

OmniMed3D는 로컬 DICOM 파일을 읽고, CT·MR 볼륨을 렌더링하며, 온디바이스 AI가 만든 폐 분할 결과를 겹쳐 보여주는 연구 프로토타입입니다. 데이터 파싱, 추론, 렌더링을 사용자의 기기 안에서 처리합니다.

이 팀 프로젝트에서 **3D 렌더링과 DICOM 처리**를 담당했습니다. 파일의 픽셀값과 공간 정보를 해석해 볼륨을 구성하고, 브라우저의 GPU에서 탐색할 수 있는 영상으로 표현하는 데 집중했습니다.

프로젝트 전체 기능으로는 파일 로딩과 영상 탐색 UI, 온디바이스 AI 추론, 슬라이스별 분할 결과 갱신을 제공합니다. 아래에서는 이 팀 파이프라인과 제가 담당한 렌더링·DICOM 구현을 구분해 설명합니다.

## 맡은 영역

| 영역 | 구현 범위 |
| --- | --- |
| 3D 렌더링 | C++20 렌더링 코어, WebGPU 백엔드, 볼륨 렌더링과 전달받은 마스크의 합성 |
| DICOM 처리 | 네이티브와 WASM에서 공유하는 C++ 파서, Parse Worker, 볼륨 조립과 방향 정규화 |

웹 뷰어 UI와 전체 메시지 라우팅은 팀 프로젝트의 기능으로 소개합니다. AI 모델 변환·양자화와 Inference Worker는 `@hyuniverse`의 담당 영역입니다. 제 렌더링 영역에서는 전달받은 분할 마스크를 영상 위에 합성합니다.

## 01 / 팀 파이프라인과 담당 경계

프로젝트는 파일 로딩부터 AI 완료까지를 독립된 단계로 나눕니다. DICOM 처리와 렌더링 사이에 Shell이 데이터를 연결하고, 별도 Inference Worker가 AI 추론을 실행하는 구조입니다.

1. **Parse Worker**가 C++ 파서의 WASM 모듈을 사용해 DICOM을 읽고 픽셀값·메타데이터를 처리합니다.
2. **Shell**이 조립된 볼륨을 엔진에 전달하고, 슬라이스를 Inference Worker로 연결합니다.
3. **WebGPU 엔진**이 볼륨을 렌더링합니다.
4. **Inference Worker**가 반환하는 `mask-slice`를 받아 3D 마스크 텍스처를 점진적으로 갱신합니다.

프로젝트의 Shell은 볼륨마다 `volumeId`를 부여하고 이전 볼륨의 늦게 도착한 마스크를 버립니다. 파일을 바꾸는 동안 추론이 진행되어도 서로 다른 영상과 마스크가 섞이지 않도록 하는 팀 통합 경계입니다.

일반 모드에서는 렌더링과 추론을 병행합니다. 저메모리 모드에서는 GPU 경합을 줄이기 위해 추론 중 렌더링을 잠시 멈추는 경로도 제공합니다.

## 02 / 볼륨을 읽기 위한 렌더링

삼각형 표면 대신 3D 텍스처 내부를 따라 샘플링하는 raymarching을 구현했습니다. CT의 window/level을 조절하고, 전달 함수와 흡수 모델을 통해 내부 밀도를 화면의 색과 불투명도로 바꿉니다.

| 기능 | 해결한 문제 |
| --- | --- |
| Pre-integrated transfer function | 거친 샘플 간격에서 얇고 대비가 큰 구조를 놓치는 현상 완화 |
| Gradient 사전 계산 | 광선의 매 단계에서 반복하던 기울기 계산을 볼륨 로딩 시 compute pass로 이동 |
| Jitter + temporal accumulation | 정지 화면의 샘플링 밴딩 완화 |
| Clip box | 전체 볼륨 중 관심 범위만 잘라 내부 구조 탐색 |
| 마스크 경계 합성 | 마스크 내부의 매 샘플마다 색이 누적되어 과하게 불투명해지는 현상 수정 |

셰이더는 Slang으로 작성해 WGSL로 컴파일합니다. 엔진 코어는 C++20으로 작성하고 Emscripten을 통해 브라우저에서 실행합니다.

![OmniMed3D의 WebGPU 기반 흉부 CT 볼륨 렌더링과 window/level 조절 화면](/portfolio/omnimed3d-image/rendering.jpg)

*볼륨 렌더링과 window/level 컨트롤의 실제 실행 화면.*

## 03 / 파일의 좌표를 화면의 좌표로

의료 영상은 파일 순서와 실제 공간상의 슬라이스 순서가 항상 같지 않습니다. `ImageOrientationPatient`와 `ImagePositionPatient`를 사용해 슬라이스를 정렬하고, 방향을 canonical LPS 좌표계로 정규화했습니다.

축에 정렬된 영상은 빠른 경로로 처리하고, 기울어진 전체 시리즈는 삼선형 보간으로 기준 격자에 재표본화합니다. 변환된 볼륨과 원본 슬라이스를 별도로 유지해 재구성된 영상과 원본을 각각 볼 수 있게 했습니다.

- **3D Orbit:** 볼륨 회전·확대 및 밀도 기반 렌더링
- **Axial / Sagittal / Coronal:** 동일한 볼륨을 세 방향의 단면으로 탐색
- **Native:** 원본 파일의 순서와 해상도를 유지한 슬라이스 표시

CT용 고정 프리셋만으로 MR 영상을 표시하면 영상이 과하게 밝아질 수 있어, 파일에 저장된 VOI window 값을 적용하는 경로도 연결했습니다.

## 04 / 기기의 메모리 한계에 대응하기

3D 볼륨은 밀도·마스크뿐 아니라 shading용 gradient 텍스처까지 GPU 메모리를 사용합니다. 화질 설정만 낮추는 것으로 해결되지 않는 메모리 문제를 별도 로딩 옵션으로 다뤘습니다.

- 저메모리 모드에서는 큰 gradient 텍스처를 만들지 않고 샘플링 시 계산합니다.
- 볼륨과 마스크를 X/Y 방향으로 2·4·8배 축소해 업로드할 수 있습니다.
- 원본 해상도로 도착하는 AI 마스크에도 동일한 축소 규칙을 적용합니다.
- 엔진은 GPU timestamp query 지원 여부를 확인해 pass별 측정값과 device loss 상태를 제공합니다. 팀 뷰어는 이를 시간 표시와 복구 안내에 사용합니다.

속도, 메모리, 화질의 선택을 하나의 추상적인 품질 값에 숨기지 않고 실제 비용이 발생하는 단계에 배치했습니다.

## 현재 범위와 검증

현재 배포된 렌더링 경로는 **WebGPU/WASM**입니다. 네이티브 Vulkan용 인터페이스 설계는 있지만 Vulkan `Device` 구현은 아직 없습니다.

브라우저 통합 테스트는 실제 DICOM, Worker, WASM을 연결해 볼륨 표시, 마스크 반영, 순서가 다른 슬라이스 전달과 오래된 `volumeId` 거부 등을 확인합니다. 모델 품질을 검사하는 AI 측 검증과 렌더링 연결을 검사하는 통합 테스트는 구분합니다.

AI 분할은 현재 **폐 전용 lungmask R231**을 사용합니다. 다장기 분할, 거리·각도 측정, 협업 주석과 PACS 연결은 향후 범위입니다. DICOM 파서는 비압축 Little Endian 형식을 지원하며 압축 전송 구문은 지원하지 않습니다.

주요 지원 대상은 WebGPU를 사용할 수 있는 Chrome입니다. Safari/iOS의 AI는 WASM fallback으로 제한되어 느리며, 모든 브라우저에서 동일한 기능·성능을 보장하지 않습니다.

이 프로젝트는 연구 프로토타입으로, 인증된 의료기기나 진단용 제품이 아닙니다.

## 프로젝트와 구현 근거

- [프로젝트 소개](https://omnimed3d.pages.dev/) · [공개 CT 데모 실행](https://omnimed3d.pages.dev/app/?demo=LIDC-IDRI-0001)
- [소스 코드와 현재 지원 범위](https://github.com/OmniMed3D/omnimed3d)
- [저장소 모듈별 관리 구조 / CODEOWNERS](https://github.com/OmniMed3D/omnimed3d/blob/main/.github/CODEOWNERS)
- [렌더링 구현 명세](https://github.com/OmniMed3D/omnimed3d/blob/main/engine/docs/RENDERING_SPEC.md)
- [DICOM Parse Worker와 방향 정규화](https://github.com/OmniMed3D/omnimed3d/blob/main/viewer/src/workers/parse-worker/README.md)

2026년 10월 13일 확인. 공개 저장소의 [2026년 10월 8일 main 커밋 `73ab759`](https://github.com/OmniMed3D/omnimed3d/commit/73ab759c25272ba979f5529d28feacbd58cd6639)을 기준으로 작성했습니다.
