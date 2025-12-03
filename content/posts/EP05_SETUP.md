+++
date = '2025-09-09T14:00:00+09:00'
draft = false
title = '[Vulkan] Ep05. 개발 환경 구축'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Setup", "CMake", "vcpkg", "Mac", "Linux", "Makefile"]
categories = ["그래픽스 프로그래밍"]
+++

## 시작하며

[Ep04]까지 이론을 다뤘다면, 이제 실제로 Vulkan 코드를 작성할 환경을 구축한다.

Mac과 Linux에서 Vulkan 개발 환경을 구축하려면 다음이 필요하다:
- Vulkan SDK 설치 및 환경변수 설정
- CMake, 컴파일러, vcpkg 설치
- CMakePresets.json과 Makefile 설정

이 글에서는 vcpkg + CMakePresets + Makefile 조합을 사용한다.

> **참고**: Windows 환경은 현재 준비 중이다.

---

## 1. Vulkan SDK 설치

### 1.1. SDK 다운로드 및 설치

[LunarG Vulkan SDK](https://vulkan.lunarg.com/)에서 각 OS에 맞는 SDK를 다운로드한다.

#### Linux (Ubuntu/Debian)

방법 1: **패키지 설치** (권장)

```bash
# 공식 저장소 추가
wget -qO - https://packages.lunarg.com/lunarg-signing-key-pub.asc | sudo apt-key add -
sudo wget -qO /etc/apt/sources.list.d/lunarg-vulkan-1.3.296-jammy.list \
  https://packages.lunarg.com/vulkan/1.3.296/lunarg-vulkan-1.3.296-jammy.list

# 설치
sudo apt update
sudo apt install vulkan-sdk
```

방법 2: **tarball 설치**

```bash
# 홈 디렉터리에 압축 해제
cd ~
tar -xf vulkansdk-linux-x86_64-1.3.296.0.tar.gz
```

#### macOS

1. `.dmg` 파일 다운로드 및 실행
2. 기본 경로에 설치: `/Users/사용자명/VulkanSDK/1.3.296.0/`
3. Mac은 Vulkan을 직접 지원하지 않아 MoltenVK(Vulkan → Metal 변환 레이어)가 함께 설치된다

### 1.2. 설치 확인

```bash
vulkaninfo
vkcube  # 3D 큐브 데모
```

"command not found" 오류 발생 시 환경변수 설정이 필요하다.

---

## 2. 환경변수 설정

Mac과 Linux는 환경변수 수동 설정이 필요하다. 동적 라이브러리 경로, SDK 위치, Validation Layer 경로를 직접 지정한다.

### 2.1. Linux 환경변수 설정

`~/.bashrc` 또는 `~/.zshrc` 파일에 추가:

```bash
export VULKAN_SDK="$HOME/1.3.296.0/x86_64"
export PATH="$VULKAN_SDK/bin:$PATH"
export LD_LIBRARY_PATH="$VULKAN_SDK/lib:$LD_LIBRARY_PATH"
export VK_LAYER_PATH="$VULKAN_SDK/share/vulkan/explicit_layer.d"
```

설정 후 적용:

```bash
source ~/.bashrc
```

검증:

```bash
echo $VULKAN_SDK
vulkaninfo | head -20
```

### 2.2. macOS 환경변수 설정

`~/.zshrc` 파일에 추가:

```bash
export VULKAN_SDK="$HOME/VulkanSDK/1.3.296.0/macOS"
export PATH="$VULKAN_SDK/bin:$PATH"
export DYLD_LIBRARY_PATH="$VULKAN_SDK/lib:$DYLD_LIBRARY_PATH"
export VK_ICD_FILENAMES="$VULKAN_SDK/share/vulkan/icd.d/MoltenVK_icd.json"
export VK_LAYER_PATH="$VULKAN_SDK/share/vulkan/explicit_layer.d"

# Homebrew LLVM
export PATH="/opt/homebrew/opt/llvm/bin:$PATH"
export LDFLAGS="-L/opt/homebrew/opt/llvm/lib/c++"
export CPPFLAGS="-I/opt/homebrew/opt/llvm/include"
```

설정 후 적용:

```bash
source ~/.zshrc
```

### 2.3. 환경변수 설명

**`LD_LIBRARY_PATH` (Linux)**:
- 동적 라이브러리(`.so`) 검색 경로
- 미설정 시 `libvulkan.so`를 찾지 못해 실행 실패

**`DYLD_LIBRARY_PATH` (Mac)**:
- Linux의 `LD_LIBRARY_PATH`와 동일한 역할
- Mac은 보안상 이 변수가 무시되는 경우가 있어 CMake에서 `rpath` 설정 필요
- MoltenVK 사용을 위해 `VK_ICD_FILENAMES` 필수

---

## 3. 빌드 도구 설치

### 3.1. CMake 설치

#### Linux

```bash
sudo apt install cmake ninja-build
```

#### macOS

```bash
brew install cmake ninja
```

검증 (3.15 이상 필요):

```bash
cmake --version
```

### 3.2. 컴파일러 설정

#### Linux

```bash
sudo apt install clang-18 clang++-18
```

#### macOS

```bash
xcode-select --install
brew install llvm
```

### 3.3. vcpkg 설치

vcpkg는 C++ 라이브러리 패키지 매니저다. GLFW, GLM 등 외부 라이브러리를 자동으로 다운로드하고 빌드한다.

#### Linux/macOS

```bash
cd ~
git clone https://github.com/microsoft/vcpkg.git
cd vcpkg
./bootstrap-vcpkg.sh
```

검증:

```bash
~/vcpkg/vcpkg version
```

---

## 4. CMake Presets

CMake Presets는 플랫폼별 빌드 설정을 파일로 저장해 간단한 이름으로 호출할 수 있게 한다.

### 4.1. CMakePresets.json 생성

프로젝트 루트에 `CMakePresets.json` 생성:

```json
{
    "version": 3,
    "configurePresets": [
        {
            "name": "mac-default",
            "displayName": "Mac Default Config",
            "description": "Default build using vcpkg",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "CMAKE_TOOLCHAIN_FILE": "/Users/사용자명/vcpkg/scripts/buildsystems/vcpkg.cmake",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "TRUE",
                "CMAKE_C_COMPILER": "/opt/homebrew/opt/llvm/bin/clang",
                "CMAKE_CXX_COMPILER": "/opt/homebrew/opt/llvm/bin/clang++",
                "CMAKE_CXX_FLAGS": "-stdlib=libc++ -isysroot /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk",
                "CMAKE_EXE_LINKER_FLAGS": "-L/opt/homebrew/opt/llvm/lib/c++ -Wl,-rpath,/opt/homebrew/opt/llvm/lib/c++"
            },
            "environment": {
                "VCPKG_TARGET_TRIPLET": "x64-osx"
            }
        },
        {
            "name": "linux-default",
            "displayName": "Linux Default Config",
            "description": "Default build for Linux using vcpkg with Clang 18",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "CMAKE_TOOLCHAIN_FILE": "$env{HOME}/vcpkg/scripts/buildsystems/vcpkg.cmake",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "TRUE",
                "CMAKE_C_COMPILER": "/usr/bin/clang-18",
                "CMAKE_CXX_COMPILER": "/usr/bin/clang++-18",
                "CMAKE_CXX_FLAGS": "-pthread",
                "CMAKE_EXE_LINKER_FLAGS": "-lpthread",
                "VULKAN_SDK": "$env{HOME}/1.3.296.0/x86_64"
            },
            "environment": {
                "VCPKG_TARGET_TRIPLET": "x64-linux",
                "VULKAN_SDK": "$env{HOME}/1.3.296.0/x86_64",
                "PATH": "/home/사용자명/vcpkg/downloads/tools/ninja/1.13.1-linux:$penv{PATH}",
                "LD_LIBRARY_PATH": "/usr/lib/x86_64-linux-gnu:$penv{LD_LIBRARY_PATH}"
            }
        }
    ],
    "buildPresets": [
        {
            "name": "mac-default",
            "configurePreset": "mac-default"
        },
        {
            "name": "linux-default",
            "configurePreset": "linux-default"
        }
    ]
}
```

주의사항:
- `CMAKE_TOOLCHAIN_FILE`의 vcpkg 경로를 실제 설치 경로로 수정
- `VULKAN_SDK` 환경변수 경로도 실제 설치 경로로 수정

### 4.2. 사용법

```bash
# Preset 사용
cmake --preset linux-default  # 또는 mac-default
cmake --build build
```

---

## 5. Makefile

Makefile은 환경변수 설정과 빌드 과정을 자동화한다.

### 5.1. Makefile이 해결하는 문제

CMake Presets를 사용해도 여전히 불편한 점:
- Linux/Mac에서 `LD_LIBRARY_PATH`, `VULKAN_SDK`, `DYLD_LIBRARY_PATH` 등 환경변수를 매번 설정해야 함
- vcpkg 경로가 다른 환경에서 작업할 때마다 수정 필요
- `cmake --preset` → `cmake --build` → 실행 과정을 매번 반복

### 5.2. Makefile의 역할

- OS 자동 감지 (Linux vs macOS)
- 플랫폼별 환경변수 자동 설정
- CMake Preset 자동 선택
- 빌드 디렉터리 관리

### 5.3. 사용법

```bash
make         # 설정 + 빌드
make run     # 빌드 + 실행
make clean   # 빌드 결과물 정리
make re      # 처음부터 다시 빌드
make info    # 현재 빌드 설정 출력
```

---

## 6. 프로젝트 구조와 CMakeLists.txt

### 6.1. 디렉터리 구조

```text
VulkanProject/
├── CMakeLists.txt          # CMake 빌드 설정
├── CMakePresets.json       # 플랫폼별 프리셋
├── Makefile                # 빌드 자동화
├── vcpkg.json              # vcpkg 의존성 정의
├── main.cpp                # 메인 소스 코드
├── build/                  # 빌드 결과물 (자동 생성)
└── vcpkg_installed/        # vcpkg 라이브러리 (자동 생성)
```

### 6.2. vcpkg.json 생성

프로젝트 루트에 `vcpkg.json` 생성:

```json
{
    "name": "vulkan-project",
    "version": "1.0.0",
    "dependencies": [
        "glfw3",
        "glm",
        "stb"
    ]
}
```

**의미**:

- `glfw3`: 윈도우 생성 및 입력 처리
- `glm`: 벡터/행렬 수학 라이브러리
- `stb`: 이미지 로딩 (나중에 텍스처 사용 시)

vcpkg는 CMake 실행 시 이 파일을 읽고 자동으로 라이브러리를 다운로드/빌드한다.

### 6.3. CMakeLists.txt 작성

```cmake
cmake_minimum_required(VERSION 3.15)
project(VulkanApp VERSION 1.0)

# C++17 표준 사용
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Vulkan 패키지 찾기
find_package(Vulkan REQUIRED)

# vcpkg를 통해 설치된 라이브러리 찾기
find_package(glfw3 CONFIG REQUIRED)
find_package(glm CONFIG REQUIRED)

# 실행 파일 생성
add_executable(vulkanGLFW main.cpp)

# 라이브러리 링크
target_link_libraries(vulkanGLFW
    PRIVATE
    Vulkan::Vulkan
    glfw
    glm::glm
)

# 헤더 파일 경로
target_include_directories(vulkanGLFW
    PRIVATE
    ${Vulkan_INCLUDE_DIRS}
)

# Mac 전용 설정
if(APPLE)
    # MoltenVK를 위한 rpath 설정
    set_target_properties(vulkanGLFW PROPERTIES
        BUILD_RPATH "${VULKAN_SDK}/lib"
        INSTALL_RPATH "${VULKAN_SDK}/lib"
    )

    # MoltenVK 관련 링크 플래그
    target_link_options(vulkanGLFW PRIVATE
        "-Wl,-rpath,${VULKAN_SDK}/lib"
    )
endif()

# Linux 전용 설정
if(UNIX AND NOT APPLE)
    # pthread 및 dl 라이브러리 링크
    target_link_libraries(vulkanGLFW PRIVATE dl pthread)

    # rpath 설정
    set_target_properties(vulkanGLFW PROPERTIES
        BUILD_RPATH "${VULKAN_SDK}/lib"
        INSTALL_RPATH "${VULKAN_SDK}/lib"
    )
endif()

# 컴파일 정의 (디버그 정보)
target_compile_definitions(vulkanGLFW PRIVATE
    $<$<CONFIG:Debug>:DEBUG>
)

# 컴파일 옵션
target_compile_options(vulkanGLFW PRIVATE -Wall -Wextra -pedantic)
```

### 6.4. 주요 CMake 개념

- `find_package`: 필요한 라이브러리를 시스템에서 찾음
- `target_link_libraries`: 실행 파일에 라이브러리 연결
- `rpath`: 실행 파일이 동적 라이브러리를 찾을 경로 (Mac/Linux 필수)

---

## 7. 테스트 코드 작성 및 빌드

### 7.1. main.cpp 작성

간단한 테스트 코드:

```cpp
#define GLFW_INCLUDE_VULKAN
#include <GLFW/glfw3.h>

#include <iostream>
#include <stdexcept>
#include <cstdlib>

class HelloTriangleApplication {
public:
    void run() {
        initWindow();
        initVulkan();
        mainLoop();
        cleanup();
    }

private:
    GLFWwindow* window;
    const uint32_t WIDTH = 800;
    const uint32_t HEIGHT = 600;

    void initWindow() {
        glfwInit();
        glfwWindowHint(GLFW_CLIENT_API, GLFW_NO_API);
        glfwWindowHint(GLFW_RESIZABLE, GLFW_FALSE);

        window = glfwCreateWindow(WIDTH, HEIGHT, "Vulkan", nullptr, nullptr);
    }

    void initVulkan() {
        // Vulkan 초기화 (나중에 구현)
    }

    void mainLoop() {
        while (!glfwWindowShouldClose(window)) {
            glfwPollEvents();
        }
    }

    void cleanup() {
        glfwDestroyWindow(window);
        glfwTerminate();
    }
};

int main() {
    HelloTriangleApplication app;

    try {
        app.run();
    } catch (const std::exception& e) {
        std::cerr << e.what() << std::endl;
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
```

### 7.2. 빌드 및 실행

```bash
make
make run

# 또는 수동으로
cmake --preset linux-default  # 또는 mac-default
cmake --build build
./build/vulkanGLFW
```

성공 시 800x600 빈 윈도우가 나타난다.

---

## 8. 문제 해결

### 8.1. "vulkaninfo: command not found"

원인: PATH에 Vulkan SDK bin 경로 누락

```bash
export PATH="$VULKAN_SDK/bin:$PATH"
source ~/.bashrc
```

### 8.2. "error while loading shared libraries: libvulkan.so.1"

원인: 동적 라이브러리 경로 미설정

```bash
# Linux
export LD_LIBRARY_PATH="$VULKAN_SDK/lib:$LD_LIBRARY_PATH"

# Mac
export DYLD_LIBRARY_PATH="$VULKAN_SDK/lib:$DYLD_LIBRARY_PATH"
```

또는 CMakeLists.txt의 `rpath` 설정 확인

### 8.3. Mac "dyld: Library not loaded"

원인: rpath 미설정 또는 MoltenVK 미발견

해결:
1. CMakeLists.txt rpath 설정 확인
2. 환경변수 확인: `echo $VK_ICD_FILENAMES`

### 8.4. CMake가 Vulkan을 못 찾음

원인: `VULKAN_SDK` 환경변수 미설정 또는 잘못된 경로

```bash
echo $VULKAN_SDK
```

### 8.5. vcpkg가 라이브러리를 못 찾음

원인: `CMAKE_TOOLCHAIN_FILE` 잘못 설정

해결:
1. CMakePresets.json에서 vcpkg 경로 확인
2. vcpkg 설치 확인: `~/vcpkg/vcpkg version`

### 8.6. "No CMAKE_CXX_COMPILER could be found"

원인: C++ 컴파일러 미설치 또는 경로 오류

```bash
# Linux
sudo apt install clang-18

# Mac
brew install llvm
```

---

## 9. 플랫폼별 체크리스트

### Linux

필수 설정:
- `LD_LIBRARY_PATH` 설정
- `VULKAN_SDK` 환경변수 설정
- `VK_LAYER_PATH` 설정
- clang-18 설치

### macOS

필수 설정:
- `VK_ICD_FILENAMES` 설정 (MoltenVK)
- `VK_LAYER_PATH` 설정
- CMake rpath 설정
- Homebrew LLVM 설치

---

## 10. 환경 검증

### 기본 확인

```bash
vulkaninfo | head -20
vkcube
cmake --version  # 3.15 이상
clang++ --version
~/vcpkg/vcpkg version
```

### 환경변수 확인

```bash
echo $VULKAN_SDK
echo $LD_LIBRARY_PATH  # 또는 $DYLD_LIBRARY_PATH (Mac)
echo $VK_LAYER_PATH
```

### 빌드 확인

```bash
make info
make
make run
```

성공 조건:
- 빌드 에러 없음
- 800x600 윈도우 출력
- 정상 종료

---

## 마치며

Mac과 Linux에서 Vulkan 개발 환경을 구축했다:

1. vcpkg: 외부 라이브러리 자동 관리
2. CMakePresets.json: 플랫폼별 설정 저장
3. Makefile: 환경변수 및 빌드 자동화

다음 편에서는 VkInstance와 VkDevice를 생성한다.

---

**다음 편**: [Vulkan] Ep06. Instance와 Device
