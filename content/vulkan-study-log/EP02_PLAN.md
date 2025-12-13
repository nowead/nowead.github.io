+++
date = '2025-09-06T10:33:42+09:00'
draft = false
title = '[Vulkan] Ep02. 학습 계획'
series = ["Vulkan 학습"]
tags = ["Vulkan", "학습계획", "Tutorial"]
categories = ["그래픽스 프로그래밍"]
+++

## 시작하며

Vulkan을 배우겠다는 설레는 마음으로 [Vulkan Tutorial](https://docs.vulkan.org/tutorial/latest/00_Introduction.html) 사이트에 들어갔다.

역시 모르는 단어가 너무 많다. 하지만 걱정하지 않는다. **모르는 단어와 개념은 일단 암기한다. 암기는 이해를 돕고, 이해는 암기를 돕는다.**

공식 튜토리얼의 목차를 기준으로 학습 계획을 세웠다.

### Khronos Vulkan Tutorial 목차

- Introduction
- Overview
- Development environment
- Drawing a triangle
- Vertex buffers
- Uniform buffers
- Texture mapping
- Depth buffering
- Loading models
- Generating Mipmaps
- Multisampling
- Compute Shader
- Ecosystem Utilities and GPU Compatibility
- Vulkan Profiles
- Android
- Migrating to Modern Asset Formats: glTF and KTX2
- Rendering Multiple Objects
- Multithreading
- Ray Tracing
- FAQ
- GitHub Repository

## 1차 학습 목표: "Loading models"까지

"**Loading models 챕터까지 완료하면 Vulkan의 핵심 그래픽스 파이프라인을 처음부터 끝까지 완성하는 것**"이 1차 목표다.

### 1단계: 기본 설정 (Introduction ~ Development environment)

- 인스턴스, 디바이스, 큐(Queue) 등 Vulkan의 기본 구조 설정
- 개발 환경 구축

### 2단계: 화면 출력 (Drawing a triangle)

- **핵심 구조 이해**:
  - 스왑 체인(Swap chain)
  - 렌더 패스(Render pass)
  - 프레임 버퍼(Framebuffer)

- **파이프라인 구성**:
  - 기본적인 셰이더(Shader) 컴파일
  - 커맨드 버퍼(Command buffer) 기록 및 제출
  - 동기화 객체 (세마포어, 펜스)

### 3단계: 데이터 공급 (Vertex buffers)

- 정점(Vertex) 데이터를 CPU에서 GPU 메모리로 전송하는 방법
- 파이프라인의 정점 입력 설정

### 4단계: 변환 및 상수 (Uniform buffers)

- MVP (Model-View-Projection) 매트릭스 같은 데이터를 셰이더로 전달하는 방법
- 유니폼 버퍼의 역할과 활용

### 5단계: 리소스 바인딩 (Descriptor layout/pool/sets)

Vulkan에서 가장 중요하고 복잡한 부분 중 하나다. 유니폼 버퍼나 텍스처 같은 리소스를 셰이더가 접근할 수 있도록 연결하는 방법을 배운다.

### 6단계: 텍스처링 (Texture mapping)

- 이미지를 GPU로 전송하는 방법
- 샘플러(Sampler)를 통해 셰이더에서 텍스처를 사용하는 방법
- 디스크립터를 활용한 리소스 바인딩 실습

### 7단계: 3D 처리 (Depth buffering)

3D 공간에서 앞뒤 물체를 올바르게 가려주기 위한 깊이 테스트를 구현한다.

### 8단계: 종합 (Loading models)

단순한 삼각형이 아닌, **실제 3D 모델 파일(.obj 등)을 읽어와 화면에 렌더링**한다.

이 과정에서 앞서 배운 모든 개념을 종합적으로 사용하게 된다:

- 정점 버퍼
- 인덱스 버퍼
- 텍스처
- MVP 변환
- 디스크립터 세트

### 1차 학습의 의미

여기까지 완료하면, **하나의 완성된 3D 객체를 Vulkan을 이용해 화면에 띄우는 전체 과정**을 이해하게 된다. 이것이 **Vulkan의 가장 핵심적인 뼈대**다.

---

## 2차 학습 및 프로젝트 진행

1차 학습을 마친 후, 본인의 프로젝트를 시작하면서 필요한 기능들을 튜토리얼의 나머지 부분에서 발췌하여 적용해볼 수 있다.

### 품질 향상

- **Generating Mipmaps**
  - 텍스처 품질을 높이고 성능을 개선한다
  - 원거리 텍스처의 앨리어싱을 줄인다

- **Multisampling**
  - 안티앨리어싱(MSAA)을 적용하여 계단 현상을 줄인다
  - 시각적 품질 향상

### 효율 및 구조 개선

- **Rendering Multiple Objects**
  - 여러 객체를 효율적으로 그리는 방법을 다룬다
  - 1차 학습 후 가장 먼저 보면 좋은 챕터다

- **Multithreading**
  - 커맨드 버퍼 생성을 병렬화하여 CPU 부하를 줄인다
  - 멀티코어 CPU를 효율적으로 활용한다

### 고급 기능

- **Compute Shader**
  - 그래픽스 파이프라인과 별개로 GPU를 이용한 범용 계산(GPGPU)을 수행한다
  - 물리 시뮬레이션, 파티클 시스템 등에 활용

- **Ray Tracing**
  - 실시간 레이 트레이싱 기능을 구현한다
  - 현실적인 반사, 굴절, 그림자 표현

### 플랫폼 및 생태계

- **Vulkan Profiles**: 다양한 하드웨어 호환성 관리
- **Android**: 모바일 플랫폼 대응
- **Migrating to Modern Asset Formats**: glTF, KTX2 등 최신 포맷 활용

---

## 마치며

이 학습 계획은 Vulkan의 방대한 내용을 체계적으로 학습하기 위한 로드맵이다. 1차 목표를 달성하면 Vulkan의 핵심을 이해하게 되고, 2차 학습을 통해 실전에서 필요한 다양한 기능을 익힐 수 있다.

중요한 것은 **한 걸음씩 차근차근 진행하는 것**이다. 서두르지 말고, 각 단계를 확실히 이해하고 넘어가자.
