+++
date = '2025-09-09T14:00:00+09:00'
draft = false
title = '[Vulkan] Ep05. 개발 환경 구축 - 완벽 가이드'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Setup", "CMake", "vcpkg", "Mac", "Linux", "Windows"]
categories = ["그래픽스 프로그래밍"]
+++

## 시작하며

드디어 손을 움직일 시간이다. [Ep04]까지 이론적인 개념들을 정리했다면, 이제는 실제로 Vulkan 코드를 작성할 환경을 만들어야 한다.

"간단하게 SDK 설치하고 프로젝트 하나 만들면 되겠지?" 라는 순진한 생각은 3시간 만에 산산조각 났다. **Mac, Linux, Windows 각각의 환경에서 Vulkan을 제대로 구축하는 것은 생각보다 훨씬 복잡했다.** 동적 라이브러리 경로 설정부터 SDK 위치 직접 지정, Mac의 경우 MoltenVK 설정, 그리고 의존성 관리까지...

하지만 결국 찾아낸 해법이 있다: **vcpkg + CMakePresets + Makefile**. 이 조합으로 세 플랫폼 모두에서 일관된 개발 환경을 구축할 수 있었다.

이번 글에서는 **실제로 겪은 시행착오를 그대로 담아**, Windows, Mac, Linux에서 Vulkan 개발 환경을 구축하는 전 과정을 정리한다.

---

## 1. Vulkan SDK 설치

### 1.1. SDK 다운로드 및 설치

[LunarG Vulkan SDK](https://vulkan.lunarg.com/) 사이트에서 각 OS에 맞는 SDK를 다운로드한다.

#### Windows

1. Windows용 `.exe` 설치 파일 다운로드
2. 설치 시 "Add to PATH" 옵션 체크
3. 기본 경로: `C:\VulkanSDK\1.3.296.0\`

**주의**: 설치 후 **터미널을 재시작**해야 환경변수가 적용된다.

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
3. **중요**: Mac은 Vulkan을 직접 지원하지 않아 **MoltenVK**(Vulkan → Metal 변환 레이어)가 함께 설치된다

### 1.2. 설치 확인

터미널에서 다음 명령어로 확인:

```bash
vulkaninfo
# 또는
vkcube  # 3D 큐브가 회전하는 데모
```

**문제 발생**: "command not found" 오류가 나타나면 환경변수 설정이 필요하다.

---

## 2. 환경변수 설정 - 가장 까다로운 관문

**솔직히 이 부분에서 가장 많이 막혔다.** Windows는 SDK가 대부분 자동으로 설정해주지만, **Mac과 Linux는 수동 설정이 필요하다.** 동적 라이브러리 경로, SDK 위치, Validation Layer 경로를 모두 직접 지정해줘야 한다.

### 2.1. Linux 환경변수 설정

`~/.bashrc` 또는 `~/.zshrc` 파일 **맨 아래**에 추가:

```bash
# Vulkan SDK 경로 설정 (버전 번호는 실제 설치된 버전에 맞게 수정)
export VULKAN_SDK="$HOME/1.3.296.0/x86_64"
export PATH="$VULKAN_SDK/bin:$PATH"

# 동적 라이브러리 경로 (이게 제일 중요!)
export LD_LIBRARY_PATH="$VULKAN_SDK/lib:$LD_LIBRARY_PATH"

# Validation Layer 경로
export VK_LAYER_PATH="$VULKAN_SDK/share/vulkan/explicit_layer.d"
```

설정 후 **반드시**:

```bash
source ~/.bashrc  # 또는 source ~/.zshrc
# 또는 터미널을 완전히 닫고 다시 열기
```

**검증**:

```bash
echo $VULKAN_SDK
# 출력: /home/사용자명/1.3.296.0/x86_64

vulkaninfo | head -20
# Vulkan 정보가 출력되어야 함
```

### 2.2. macOS 환경변수 설정

`~/.zshrc` (Mac은 기본적으로 zsh 사용) 파일에:

```bash
# Vulkan SDK 경로 (버전 번호 확인!)
export VULKAN_SDK="$HOME/VulkanSDK/1.3.296.0/macOS"
export PATH="$VULKAN_SDK/bin:$PATH"

# 동적 라이브러리 경로 (Mac은 DYLD_LIBRARY_PATH 사용)
export DYLD_LIBRARY_PATH="$VULKAN_SDK/lib:$DYLD_LIBRARY_PATH"

# MoltenVK 설정 (Mac 전용)
export VK_ICD_FILENAMES="$VULKAN_SDK/share/vulkan/icd.d/MoltenVK_icd.json"
export VK_LAYER_PATH="$VULKAN_SDK/share/vulkan/explicit_layer.d"

# Homebrew LLVM 설정 (나중에 clang++ 컴파일러로 사용)
export PATH="/opt/homebrew/opt/llvm/bin:$PATH"
export LDFLAGS="-L/opt/homebrew/opt/llvm/lib/c++"
export CPPFLAGS="-I/opt/homebrew/opt/llvm/include"
```

설정 후:

```bash
source ~/.zshrc
```

### 2.3. Windows 환경변수 설정

Windows는 SDK 설치 시 대부분 자동 설정되지만, 수동 확인이 필요한 경우:

1. `Win + R` → `sysdm.cpl` → "고급" 탭 → "환경 변수"
2. 시스템 변수에 다음이 있는지 확인:
   - `VULKAN_SDK`: `C:\VulkanSDK\1.3.296.0`
   - `Path`에 `%VULKAN_SDK%\Bin` 포함

**검증** (PowerShell):

```powershell
$env:VULKAN_SDK
# 출력: C:\VulkanSDK\1.3.296.0

vulkaninfo
```

### 2.4. 왜 이렇게 까다로운가?

**Linux의 `LD_LIBRARY_PATH`**:

- 프로그램이 실행될 때 동적 라이브러리(`.so` 파일)를 어디서 찾을지 알려주는 환경변수
- 이걸 설정 안 하면 `libvulkan.so`를 찾지 못해 "error while loading shared libraries" 발생

**Mac의 `DYLD_LIBRARY_PATH`**:

- Linux의 `LD_LIBRARY_PATH`와 같은 역할
- Mac은 보안상의 이유로 이 변수가 무시되는 경우가 많아 **CMake에서 `rpath` 추가 설정 필요**
- MoltenVK를 통해 Metal로 변환하기 때문에 `VK_ICD_FILENAMES` 필수

**Windows의 `Path`**:

- DLL 파일을 찾는 경로
- SDK 설치 시 자동으로 추가되지만, 터미널을 재시작해야 적용됨

---

## 3. 빌드 도구 설치

### 3.1. CMake 설치

**CMake**는 플랫폼 독립적인 빌드 시스템 생성 도구다.

#### Windows

- [CMake 공식 사이트](https://cmake.org/download/)에서 `.msi` 다운로드
- 설치 시 "Add CMake to PATH" 체크

#### Linux

```bash
sudo apt install cmake ninja-build
```

#### macOS

```bash
brew install cmake ninja
```

**검증**:

```bash
cmake --version
# 3.15 이상이어야 함
```

### 3.2. 컴파일러 설정

#### Windows

- **Visual Studio 2022 Community** 설치
- "C++를 사용한 데스크톱 개발" 워크로드 선택
- **LLVM Clang 도구** 추가 선택

#### Linux

```bash
# Clang 18 설치 (권장)
sudo apt install clang-18 clang++-18
```

#### macOS

```bash
# Xcode Command Line Tools
xcode-select --install

# LLVM (최신 Clang)
brew install llvm
```

### 3.3. vcpkg 설치 - 의존성 관리의 핵심

**vcpkg**는 C++ 라이브러리 패키지 매니저다. GLFW, GLM 등 외부 라이브러리를 자동으로 다운로드하고 빌드해준다.

#### Windows

```powershell
# C:\dev\ 폴더에 설치 (원하는 경로로 변경 가능)
cd C:\dev
git clone https://github.com/microsoft/vcpkg.git
cd vcpkg
.\bootstrap-vcpkg.bat
```

#### Linux/macOS

```bash
# 홈 디렉터리에 설치
cd ~
git clone https://github.com/microsoft/vcpkg.git
cd vcpkg
./bootstrap-vcpkg.sh
```

**검증**:

```bash
# Windows
C:\dev\vcpkg\vcpkg version

# Linux/Mac
~/vcpkg/vcpkg version
```

---

## 4. CMake Presets - 플랫폼별 설정 자동화

여러 플랫폼에서 개발하다 보면 CMake 옵션이 플랫폼마다 달라 매번 긴 명령어를 입력해야 한다. **CMake Presets**는 이를 파일로 저장해 간단한 이름으로 호출할 수 있게 해준다.

### 4.1. CMakePresets.json 생성

프로젝트 루트 폴더에 `CMakePresets.json` 생성:

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
            "name": "windows-default",
            "displayName": "Windows Default Config",
            "description": "Default build for Windows using vcpkg with Clang",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build-windows",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "CMAKE_TOOLCHAIN_FILE": "C:\\dev\\vcpkg\\scripts\\buildsystems\\vcpkg.cmake",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "TRUE",
                "CMAKE_C_COMPILER": "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/Llvm/bin/clang.exe",
                "CMAKE_CXX_COMPILER": "C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/Llvm/bin/clang++.exe"
            },
            "environment": {
                "VCPKG_TARGET_TRIPLET": "x64-windows"
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
            "name": "windows-default",
            "configurePreset": "windows-default"
        },
        {
            "name": "linux-default",
            "configurePreset": "linux-default"
        }
    ]
}
```

**주의**:

- `CMAKE_TOOLCHAIN_FILE`의 vcpkg 경로를 실제 설치 경로로 수정
- `VULKAN_SDK` 환경변수 경로도 실제 설치 경로로 수정

### 4.2. CMakePresets의 핵심 개념

**configurePresets**:

- 빌드 설정을 미리 정의
- 컴파일러, 빌드 디렉터리, CMake 변수 등을 저장
- 플랫폼별로 별도 설정 가능

**주요 필드**:

- `generator`: 빌드 시스템 (Ninja, Visual Studio 등)
- `binaryDir`: 빌드 결과물이 저장될 폴더
- `cacheVariables`: CMake 캐시 변수 (컴파일러, 플래그 등)
- `environment`: 환경변수 설정

**사용 방법**:

```bash
# 기존 방식 (복잡함)
cmake -G Ninja -DCMAKE_BUILD_TYPE=Debug -DCMAKE_TOOLCHAIN_FILE=~/vcpkg/... ..

# Preset 사용 (간단함)
cmake --preset linux-default
```

---

## 5. Makefile - 빌드 자동화

CMake Presets도 좋지만, 매번 `cmake --preset xxx` 입력하는 것도 귀찮다. **Makefile**로 빌드 과정을 더욱 간편하게 만들 수 있다.

프로젝트 루트에 제공된 `Makefile`은 다음을 자동으로 처리한다:

- OS 자동 감지 (Linux, macOS, Windows)
- 플랫폼별 환경변수 설정 (`LD_LIBRARY_PATH`, `DYLD_LIBRARY_PATH`, `VULKAN_SDK` 등)
- 적절한 CMake Preset 선택

**사용법**:

```bash
# 빌드 및 실행
make         # 설정 + 빌드
make run     # 빌드 + 실행
make clean   # 정리
make re      # 처음부터 다시

# 정보 확인
make info    # 현재 빌드 설정 출력
make help    # 사용 가능한 명령어
```

Makefile 내부에서 플랫폼별로 필요한 환경변수(`VULKAN_SDK`, `LD_LIBRARY_PATH` 등)를 자동으로 설정해주기 때문에, 간단한 `make` 명령어 하나로 모든 작업을 처리할 수 있다.

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

# Windows 전용 설정
if(WIN32)
    # Windows는 대부분 자동 처리됨
    # 필요시 여기에 추가 설정
endif()

# 컴파일 정의 (디버그 정보)
target_compile_definitions(vulkanGLFW PRIVATE
    $<$<CONFIG:Debug>:DEBUG>
)

# 컴파일 옵션
if(MSVC)
    target_compile_options(vulkanGLFW PRIVATE /W4)
else()
    target_compile_options(vulkanGLFW PRIVATE -Wall -Wextra -pedantic)
endif()
```

### 6.4. CMake 핵심 개념 정리

**find_package**:

- 필요한 라이브러리를 시스템에서 찾는다
- `CONFIG`: vcpkg가 제공하는 CMake 설정 파일 사용
- `REQUIRED`: 못 찾으면 에러 발생

**target_link_libraries**:

- 실행 파일에 라이브러리를 연결
- `PRIVATE`: 이 프로젝트 내부에서만 사용

**rpath**:

- 실행 파일이 동적 라이브러리를 찾을 경로를 저장
- Mac/Linux에서 필수 (안 하면 실행 시 라이브러리를 못 찾음)

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
# 간단하게 Makefile 사용
make

# 실행
make run

# 또는 수동으로
cmake --preset linux-default  # 또는 mac-default, windows-default
cmake --build build
./build/vulkanGLFW
```

**성공하면**: 빈 윈도우가 800x600 크기로 나타난다.

---

## 8. 자주 겪은 문제들과 해결법

### 8.1. "vulkaninfo: command not found"

**원인**: PATH에 Vulkan SDK의 bin 경로가 없음

**해결**:

```bash
# Linux/Mac: ~/.bashrc 또는 ~/.zshrc에 추가
export PATH="$VULKAN_SDK/bin:$PATH"
source ~/.bashrc

# Windows: 터미널 재시작
```

### 8.2. "error while loading shared libraries: libvulkan.so.1"

**원인**: 동적 라이브러리 경로가 설정 안 됨

**해결**:

```bash
# Linux
export LD_LIBRARY_PATH="$VULKAN_SDK/lib:$LD_LIBRARY_PATH"

# Mac
export DYLD_LIBRARY_PATH="$VULKAN_SDK/lib:$DYLD_LIBRARY_PATH"
```

또는 CMakeLists.txt에 `rpath` 설정이 제대로 되어 있는지 확인.

### 8.3. Mac에서 "dyld: Library not loaded"

**원인**: rpath가 설정 안 되거나 MoltenVK를 못 찾음

**해결**:

1. CMakeLists.txt에 rpath 설정 확인
2. 환경변수 확인:

   ```bash
   echo $VK_ICD_FILENAMES
   # 출력: /Users/사용자명/VulkanSDK/.../MoltenVK_icd.json
   ```

### 8.4. CMake가 Vulkan을 못 찾을 때

**원인**: `VULKAN_SDK` 환경변수가 없거나 잘못됨

**해결**:

```bash
# 확인
echo $VULKAN_SDK

# 올바른 출력 예시:
# Linux: /home/사용자명/1.3.296.0/x86_64
# Mac: /Users/사용자명/VulkanSDK/1.3.296.0/macOS
# Windows: C:\VulkanSDK\1.3.296.0
```

### 8.5. vcpkg가 라이브러리를 못 찾을 때

**원인**: `CMAKE_TOOLCHAIN_FILE`이 잘못 설정됨

**해결**:

1. CMakePresets.json에서 vcpkg 경로 확인
2. vcpkg 설치 확인:

   ```bash
   ~/vcpkg/vcpkg version  # Linux/Mac
   C:\dev\vcpkg\vcpkg version  # Windows
   ```

### 8.6. "No CMAKE_CXX_COMPILER could be found"

**원인**: C++ 컴파일러가 설치 안 됨 또는 경로가 틀림

**해결**:

```bash
# Linux
sudo apt install clang-18

# Mac
brew install llvm

# Windows: Visual Studio 재설치 (C++ 워크로드 포함)
```

---

## 9. 플랫폼별 차이점 총정리

### Windows

**장점**:

- SDK가 대부분 자동 설정
- Visual Studio 통합 지원
- 동적 라이브러리 경로 걱정 적음

**단점**:

- 환경변수가 터미널 재시작 후 적용
- 경로에 공백 있으면 CMake에서 문제 발생 가능

**핵심 체크리스트**:

- ✓ VULKAN_SDK 환경변수 설정됨
- ✓ Path에 %VULKAN_SDK%\Bin 포함
- ✓ Visual Studio에 LLVM 도구 설치
- ✓ vcpkg 경로가 `C:\dev\vcpkg`

### Linux

**장점**:

- Vulkan 네이티브 지원
- 패키지 관리자로 쉬운 설치

**단점**:

- 배포판마다 패키지 이름 다름
- 환경변수 수동 설정 필수

**핵심 체크리스트**:

- ✓ LD_LIBRARY_PATH 설정됨
- ✓ VULKAN_SDK 환경변수 설정
- ✓ VK_LAYER_PATH 설정
- ✓ clang-18 설치

### macOS

**장점**:

- Homebrew로 통합 관리
- Xcode 개발 도구 우수

**단점**:

- Vulkan 미지원 (MoltenVK 필요)
- DYLD_LIBRARY_PATH 제한적
- rpath 설정 필수
- 추가 링커 플래그 필요

**핵심 체크리스트**:

- ✓ VK_ICD_FILENAMES 설정 (MoltenVK)
- ✓ VK_LAYER_PATH 설정
- ✓ CMake에서 rpath 설정
- ✓ Homebrew LLVM 설치

---

## 10. 환경 구축 검증 체크리스트

모든 설정이 완료되었다면 다음을 확인:

### 기본 확인

```bash
# 1. Vulkan SDK 설치 확인
vulkaninfo | head -20
vkcube  # 3D 큐브 데모 실행

# 2. CMake 버전 확인
cmake --version  # 3.15 이상

# 3. 컴파일러 확인
clang++ --version  # 또는 cl.exe (Windows)

# 4. vcpkg 확인
~/vcpkg/vcpkg version  # 또는 C:\dev\vcpkg\vcpkg version
```

### 환경변수 확인

```bash
# Linux/Mac
echo $VULKAN_SDK
echo $LD_LIBRARY_PATH  # 또는 $DYLD_LIBRARY_PATH
echo $VK_LAYER_PATH

# Windows (PowerShell)
$env:VULKAN_SDK
$env:Path
```

### 프로젝트 빌드 확인

```bash
# 1. 정보 출력
make info

# 2. 빌드
make

# 3. 실행
make run
```

**성공 조건**:

- ✓ 빌드 에러 없음
- ✓ 800x600 윈도우가 나타남
- ✓ 윈도우가 정상 종료됨

---

## 마치며

Mac, Linux, Windows에서 Vulkan 환경을 구축하는 것은 생각보다 훨씬 복잡했다. 특히 **동적 라이브러리 경로 설정**, **플랫폼별 컴파일러 차이**, **의존성 관리**가 가장 까다로웠다.

하지만 **vcpkg + CMakePresets + Makefile** 조합을 찾아낸 후, 세 플랫폼 모두에서 일관된 개발 환경을 구축할 수 있었다:

1. **vcpkg**: 외부 라이브러리 자동 관리
2. **CMakePresets.json**: 플랫폼별 설정을 파일로 저장
3. **Makefile**: 한 줄 명령어로 모든 작업 실행

이제 환경은 완성되었다. 다음 편에서는 드디어 **실제 Vulkan 코드**를 작성해본다. Instance 생성부터 시작해 첫 삼각형을 화면에 그려보자.

**마지막 팁**:

- 환경변수 설정 후 **터미널을 완전히 닫고 다시 열기**
- 문제 발생 시 `make info`로 현재 설정 확인
- `make clean && make`로 처음부터 다시 빌드
- 각 플랫폼의 **핵심 체크리스트** 반드시 확인

---

**다음 편 예고**: [Vulkan] Ep06. Instance와 Device - Vulkan의 첫걸음
