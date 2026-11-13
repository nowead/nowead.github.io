---
title: "OmniMed3D"
date: 2026-08-01
lastmod: 2026-11-12
weight: 1
stage: "outcome"
track: "TRACK 01 · MEDICAL 3D"
category_label: "Browser medical imaging"
status: "공개 데모"
architecture: "medical-volume"
period: "2026.08 시작 · 팀 프로젝트"
role: "3D 렌더링 · DICOM 처리"
role_note: "영상 데이터를 볼륨으로 구성하고, 팀의 AI 마스크를 화면에 합성합니다."
tags: ["C++20", "WebGPU", "WebAssembly", "Slang", "TypeScript", "DICOM"]
github: "https://github.com/OmniMed3D/omnimed3d"
demo: "https://omnimed3d.pages.dev/app/?demo=LIDC-IDRI-0001"
website: "https://omnimed3d.pages.dev/"
summary: "설치와 업로드 없이, 브라우저 안에서 DICOM 파싱부터 3D 볼륨 렌더링과 AI 폐 분할 표시까지 처리하는 의료 영상 연구 프로토타입입니다."
cover_image: "omnimed3d-image/segmentation.jpg"
cover_width: 1280
cover_height: 720
image_alt: "OmniMed3D에서 흉부 CT와 붉은 폐 분할 마스크를 함께 렌더링한 실제 화면"
image_caption: "공개·비식별 흉부 CT 데모. 붉은 영역은 lungmask R231 모델의 폐 분할 결과입니다."
brief:
  problem:
    title: "설치도, 업로드도 없이 의료 영상을"
    text: "IT 담당자가 없는 소규모 의원이나 프로그램 설치가 막힌 환경을 대상으로 했습니다. 원본 영상을 서버로 보내지 않고, 비개발자가 세 번 안에 조작을 마치는 것을 기준으로 정했습니다."
  solution:
    title: "C++ 렌더링 코어를 브라우저 GPU로"
    text: "C++20 DICOM 파서와 렌더링 코어를 WebAssembly로 빌드하고, WebGPU로 볼륨 렌더링과 단면 탐색, AI 마스크 합성을 구현했습니다."
  verification:
    title: "PR마다 실제 GPU에서 확인"
    text: "PR마다 엔진을 소스에서 빌드하고, 비식별 공개 CT를 불러와 뷰어 E2E 명세 21개를 GPU가 있는 러너에서 실행합니다."
metrics:
  - value: "0건"
    label: "서버로 전송하는 원본 영상"
  - value: "21개"
    label: "PR마다 실행하는 뷰어 E2E 명세"
  - value: "2·4·8×"
    label: "저메모리 모드 해상도 단계"
  - value: "3회 이내"
    label: "비개발자 조작 완료 목표 기준"
built_on: ["mini-engine"]
gallery:
  - image: "omnimed3d-image/segmentation.jpg"
    label: "흉부 CT 볼륨 · AI 폐 분할 마스크 합성"
    alt: "OmniMed3D에서 흉부 CT와 붉은 폐 분할 마스크를 함께 렌더링한 실제 화면"
    width: 1280
    height: 720
  - image: "omnimed3d-image/coronal.png"
    label: "CT 단면 탐색 · Coronal"
    alt: "OmniMed3D에서 흉부 CT를 관상면으로 탐색하는 실제 화면"
    width: 768
    height: 432
  - image: "omnimed3d-image/orbit.png"
    label: "3D Orbit · 볼륨 렌더링"
    alt: "OmniMed3D WebGPU 엔진에서 흉부 볼륨을 3D로 렌더링한 화면"
    width: 512
    height: 288
---

## 현장의 문제

3D 의료 영상을 보려면 보통 고가의 워크스테이션과 설치형 프로그램, 그리고 이를 관리할 사람이 필요합니다. OmniMed3D가 대상으로 삼은 곳은 그 조건을 갖추기 어려운 환경입니다.

- IT 담당자 없이 운영되는 **소규모 의원과 보건소**
- 프로그램 설치 권한이 없는 **제한된 업무 환경**
- 접근하기 쉬운 뷰어가 필요한 **연구자와 학생**

공통점은 "설치 없이, 서버 없이" 쓸 수 있어야 한다는 점이었습니다. 의료 영상을 외부 서버로 보내는 것 자체가 부담이기 때문에, 파싱·AI 추론·렌더링을 모두 사용자의 기기 안에서 처리하기로 했습니다.

## 문제 정의: 만들 것과 만들지 않을 것

팀은 제품 문서(PRD)에 요구사항을 번호(`REQ-*`)로 정의했습니다. 이 가운데 제가 맡은 렌더링과 DICOM 처리에 직접 걸리는 기준은 다음과 같습니다.

| 정의한 기준 | 내용 |
| --- | --- |
| 데이터 경계 | 원본 DICOM은 업로드하지 않습니다. 정적 호스팅만으로 배포합니다. |
| 사용성 기준 | 비개발자가 불러오기 → 회전 → 확대 → 단면 이동을 **도움 없이 세 번 안에** 마칩니다. |
| 마스크 계약 | AI 마스크는 원본 볼륨 해상도의 `uint8` 텍스처로, 슬라이스 단위로 점진적으로 도착합니다. 이전 볼륨의 마스크는 버립니다. |
| 만들지 않는 것 | 임상 진단 수준의 정확도, 인허가, PACS 연동은 범위에서 제외합니다. |

"직관적인 UI"처럼 모호한 요구는 사용성 기준으로 바꿔 측정할 수 있게 했습니다. 팀원이 만드는 AI 추론과 제가 만드는 렌더링 사이의 경계는 마스크 계약으로 고정했습니다. 두 파이프라인을 따로 개발하고도 합칠 수 있었던 근거입니다.

모듈의 소유와 범위도 결정 기록(ADR)으로 남겼습니다. DICOM 파서를 네이티브와 WASM이 공유하는 단일 모듈로 두고, 초기 범위를 비압축 픽셀 데이터로 제한한 결정이 여기에 해당합니다.

## 해결: DICOM에서 화면까지

### 맡은 영역

| 영역 | 구현 범위 |
| --- | --- |
| 3D 렌더링 | C++20 렌더링 코어, WebGPU 백엔드, 볼륨 렌더링과 전달받은 마스크의 합성 |
| DICOM 처리 | 네이티브와 WASM에서 공유하는 C++ 파서, Parse Worker, 볼륨 조립과 방향 정규화 |

### 파이프라인

파일 파싱과 GPU 렌더링을 독립된 단계로 나눴습니다.

1. **Parse Worker**가 C++ 파서의 WASM 모듈로 DICOM을 읽고 픽셀값과 메타데이터를 처리합니다.
2. **Shell**이 조립된 볼륨을 엔진에 전달하고, 슬라이스를 Inference Worker로 연결합니다.
3. **WebGPU 엔진**이 볼륨을 렌더링합니다.
4. **Inference Worker**가 반환하는 `mask-slice`를 받아 3D 마스크 텍스처를 점진적으로 갱신합니다.

Shell은 볼륨마다 `volumeId`를 부여하고, 이전 볼륨의 늦게 도착한 마스크를 버립니다. 파일을 바꾸는 동안에도 영상과 분할 결과가 올바르게 대응합니다. AI 추론이 끝나기를 기다리지 않고 영상을 먼저 보여 줍니다.

### 볼륨을 읽기 위한 렌더링

3D 텍스처 내부를 따라 샘플링하는 raymarching을 구현했습니다. CT의 window/level을 조절하고, 전달 함수와 흡수 모델로 내부 밀도를 색과 불투명도로 바꿉니다.

| 기능 | 해결한 문제 |
| --- | --- |
| Pre-integrated transfer function | 거친 샘플 간격에서 얇고 대비가 큰 구조를 놓치는 현상 완화 |
| Gradient 사전 계산 | 광선의 매 단계에서 반복하던 기울기 계산을 로딩 시 compute pass로 이동 |
| Jitter + temporal accumulation | 정지 화면의 샘플링 밴딩 완화 |
| 마스크 경계 합성 | 마스크 내부에서 색이 누적되어 과하게 불투명해지는 현상 수정 |

{{< shot src="omnimed3d-image/rendering.jpg" alt="OmniMed3D의 WebGPU 기반 흉부 CT 볼륨 렌더링과 window/level 조절 화면" caption="볼륨 렌더링과 window/level 컨트롤의 실제 실행 화면." width="1280" height="720" >}}

### 파일의 좌표를 화면의 좌표로

의료 영상은 파일 순서와 실제 공간의 슬라이스 순서가 항상 같지 않습니다. `ImageOrientationPatient`와 `ImagePositionPatient`로 슬라이스를 정렬하고, 방향을 표준 좌표계(LPS)로 정규화했습니다. 기울어진 시리즈는 삼선형 보간으로 기준 격자에 다시 표본화합니다.

- **3D Orbit** — 볼륨 회전·확대와 밀도 기반 렌더링
- **Axial / Sagittal / Coronal** — 같은 볼륨을 세 방향 단면으로 탐색
- **Native** — 원본 파일의 순서와 해상도를 유지한 슬라이스 표시

{{< shot src="omnimed3d-image/mask-slice.png" alt="흉부 CT 시상면 위에 AI 폐 분할 마스크를 붉게 합성한 화면" caption="팀의 AI 폐 분할 결과를 단면 위에 합성한 화면." width="512" height="288" >}}

### 기기의 메모리 한계에 대응하기

대상 사용자의 기기는 워크스테이션이 아닙니다. 화질 설정만 낮춰서는 해결되지 않는 메모리 문제를 별도 로딩 옵션으로 다뤘습니다.

- 저메모리 모드에서는 큰 gradient 텍스처를 만들지 않고 샘플링할 때 계산합니다.
- 볼륨과 마스크를 X/Y 방향으로 2·4·8배 축소해 올릴 수 있습니다.
- 저메모리 모드에서는 GPU 경합을 줄이기 위해 추론 중 렌더링을 잠시 멈춥니다.
- GPU 장치를 잃은 상태(device loss)를 뷰어에 전달해 사용자에게 알립니다.

## 검증: PR마다 실제 GPU에서

렌더링 결과는 눈으로 한 번 확인하는 것으로 끝나지 않습니다. 저장소의 CI는 모든 PR에서 다음을 실행합니다.

| 단계 | 내용 |
| --- | --- |
| 단위 테스트 | 볼륨 조립, 방향 정규화, half-float 변환 등 |
| 엔진 빌드 | C++ 엔진을 소스에서 WASM으로 빌드 |
| 뷰어 E2E | 비식별 공개 흉부 CT를 불러와 Playwright 명세 21개 실행 |

E2E는 WebGPU 어댑터가 있는 macOS 러너에서 실행합니다. 데모 CT 불러오기, 저메모리 모드의 gradient·축소 경로, 마스크와 볼륨의 기하 일치, 터치 카메라 조작, 추론 중 렌더링 일시 정지, GPU 장치 손실 처리가 명세에 포함됩니다. C++ DICOM 파서에는 별도의 네이티브 테스트를 두었습니다.

누구나 결과를 확인할 수 있도록 공개 데모를 운영합니다. 데모 데이터는 공개·비식별 흉부 CT(LIDC-IDRI)이며, 연구용 프로토타입으로 임상 진단용이 아닙니다.

## Mini-Engine에서 이어진 것

OmniMed3D의 렌더링 코어는 처음부터 새로 만든 것이 아닙니다. 개인 프로젝트인 **[Mini-Engine](/fde/mini-engine/)**에서 먼저 만들고 측정해 본 것들이 그대로 판단의 근거가 됐습니다.

- Vulkan과 WebGPU가 공유하는 **RHI 설계** → C++20 코어를 WASM으로 올리는 구조
- CT/MRI **볼륨 렌더링과 DICOM 로더** → 볼륨 렌더링과 공유 DICOM 파서
- 대용량 볼륨의 **메모리 피크 측정과 최적화** → 저메모리 모드와 축소 업로드

## 프로젝트 링크

- [프로젝트 소개](https://omnimed3d.pages.dev/)
- [CT 데모 실행](https://omnimed3d.pages.dev/app/?demo=LIDC-IDRI-0001)
- [GitHub 소스 코드](https://github.com/OmniMed3D/omnimed3d)
