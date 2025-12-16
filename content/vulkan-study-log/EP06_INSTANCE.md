+++
date = '2025-09-13T14:00:00+09:00'
draft = false
title = '[Vulkan] Ep06. Instance와 Physical Device'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Instance", "Physical Device", "Extension", "Validation Layer"]
categories = ["그래픽스 프로그래밍"]
summary = "Vulkan Instance를 생성하고 설정합니다. Application Info, Extension, Validation Layer 등 Instance의 핵심 요소를 다룹니다."
+++

## 시작하며

[Ep05]에서 개발 환경을 구축했다. 이제 Vulkan 코드를 작성한다.

OpenGL은 상당히 많은 기능들이 내포된 Context가 자동으로 만들어진다. 하지만 Vulkan에는 OpenGL과 같은 Context가 존재하지 않고 그저 운영체제, 하드웨어와의 연결고리 역할만 하는 Context가 존재한다. Vulkan은 이 Context 객체를 선언한 후 Instance, Physical Device, Logical Device를 직접 생성해야 한다.

이 글에서는 C++ RAII 방식으로 **Context 생성**, **Instance 생성**, **Physical Device 선택**, **Queue Family 찾기**까지 정리한다.

---

## 1. Vulkan 초기화 과정

Vulkan에서 삼각형 하나를 그리려면 다음 단계를 거쳐야 한다:

1. **Instance 생성** - Vulkan 라이브러리와 연결
2. **Physical Device 선택** - GPU 선택
3. **Logical Device 생성** - GPU와 통신할 인터페이스 생성 (다음 편)
4. **Queue 획득** - GPU에 명령을 제출할 큐 얻기 (다음 편)
5. **Surface 생성** - 윈도우와 연결
6. **Swapchain 생성** - 화면 출력 준비
7. **Pipeline 생성** - 셰이더 설정
8. **Command Buffer** - 실제 그리기 명령

이번 글에서는 1~2번까지 다룬다.

---

## 2. Instance - Vulkan의 진입점

### 2.0. Context란?

#### C API vs C++ RAII

Vulkan은 본래 C API로 설계되었다. 순수 C API를 사용하면 Context 객체 없이 직접 함수 포인터를 로드하고 관리해야 한다.

하지만 **Vulkan C++ RAII 버전**(vulkan.hpp)을 사용하면 `vk::Context` 객체가 이 과정을 자동화해준다.

#### Context의 역할

`vk::Context`는 Vulkan 사용의 가장 첫 단계로, 다음 역할을 수행한다:

1. **동적 라이브러리 함수 로딩**
   - Vulkan은 동적 라이브러리(`libvulkan.so`, `vulkan-1.dll`)로 제공됨
   - Context가 이 라이브러리에서 사용 가능한 함수들의 주소를 찾아 메모리에 로드
   - 애플리케이션이 Vulkan API를 호출할 수 있게 준비

2. **시스템 정보 조회**
   - 사용 가능한 Instance Extension 목록
   - 사용 가능한 Validation Layer 목록
   - Vulkan API 버전 정보

3. **수명 관리 (RAII)**
   - Context가 소멸될 때 Vulkan 라이브러리를 안전하게 언로드
   - 메모리 누수 방지

#### Context 생성

```cpp
#include <vulkan/vulkan_raii.hpp>

// Context 생성 (Vulkan 라이브러리 초기화)
vk::raii::Context context;

// 이제 context를 통해 Vulkan 기능 사용 가능
```

Context를 생성하면 이후 Instance, Physical Device, Logical Device 등을 순차적으로 생성할 수 있다.

#### C API와의 비교

**C API 방식:**
```cpp
VkInstance instance;
VkInstanceCreateInfo createInfo{};
// ... createInfo 설정
vkCreateInstance(&createInfo, nullptr, &instance);
// 사용 후 명시적으로 파괴 필요
vkDestroyInstance(instance, nullptr);
```

**C++ RAII 방식:**
```cpp
vk::raii::Context context;
vk::raii::Instance instance = context.createInstance(createInfo);
// instance가 스코프를 벗어나면 자동으로 파괴됨
```

RAII 방식은 자동 리소스 관리, 예외 안전성, 더 간결한 코드를 제공한다.

### 2.1. Instance란?

Instance는 Context 이후에 생성하는 객체로, Vulkan 애플리케이션과 Vulkan 라이브러리 사이의 **실질적인 연결 통로**다.

#### Context와 Instance의 관계

- **Context**: Vulkan 라이브러리를 로드하고 기본 환경을 준비
- **Instance**: 실제 Vulkan 기능을 사용하기 위한 연결점

Instance의 역할:

- Vulkan 런타임 초기화
- Extension과 Validation Layer 활성화
- Physical Device(GPU) 목록 조회
- 애플리케이션 전역 설정 관리

### 2.2. ApplicationInfo 설정

애플리케이션 정보를 설정한다:

```cpp
vk::ApplicationInfo appInfo{
    .pApplicationName = "Hello Triangle",
    .applicationVersion = VK_MAKE_VERSION(1, 0, 0),
    .pEngineName = "No Engine",
    .engineVersion = VK_MAKE_VERSION(1, 0, 0),
    .apiVersion = VK_API_VERSION_1_3
};
```

주요 필드:

- `pApplicationName`: 앱 이름 (디버깅 시 유용)
- `applicationVersion`: 애플리케이션 버전
- `pEngineName`: 엔진 이름 (사용하는 경우)
- `engineVersion`: 엔진 버전
- `apiVersion`: 사용할 Vulkan API 버전 (1.3 권장)

GPU 드라이버는 이 정보로 애플리케이션에 맞게 최적화할 수 있다.

C API에서는 모든 구조체에 `sType` 필드를 수동으로 설정해야 했지만, C++ RAII에서는 구조체 타입이 자동으로 설정되므로 실수를 방지한다.

### 2.3. Extension 설정

Extension은 Vulkan의 추가 기능이다. 기본 API는 최소 기능만 제공하므로, 윈도우 시스템 연결이나 디버깅 같은 기능은 Extension으로 활성화해야 한다.

#### GLFW가 요구하는 Extension

GLFW로 윈도우를 만들려면 플랫폼별 Extension이 필요하다:

```cpp
uint32_t glfwExtensionCount = 0;
const char** glfwExtensions = glfwGetRequiredInstanceExtensions(&glfwExtensionCount);
```

플랫폼별 필수 Extension:

- **Windows**: `VK_KHR_surface`, `VK_KHR_win32_surface`
- **Linux**: `VK_KHR_surface`, `VK_KHR_xlib_surface` 또는 `VK_KHR_wayland_surface`
- **macOS**: `VK_KHR_surface`, `VK_EXT_metal_surface`, `VK_KHR_portability_enumeration`

macOS는 MoltenVK를 사용하므로 `VK_KHR_portability_enumeration`이 추가로 필요하다.

#### Extension 지원 확인

GLFW가 요구하는 Extension을 시스템이 지원하는지 확인한다:

```cpp
// 시스템이 지원하는 Extension 목록 조회
auto availableExtensions = context.enumerateInstanceExtensionProperties();

// GLFW 요구 Extension이 지원되는지 확인
for (uint32_t i = 0; i < glfwExtensionCount; i++) {
    bool found = false;
    for (const auto& extension : availableExtensions) {
        if (strcmp(glfwExtensions[i], extension.extensionName) == 0) {
            found = true;
            break;
        }
    }
    if (!found) {
        throw std::runtime_error(std::string("Required extension not supported: ") + glfwExtensions[i]);
    }
}
```

C API에서는 먼저 개수를 조회하고, 벡터를 할당한 후 다시 호출하는 2단계 과정이 필요했다. C++ RAII에서는 `context.enumerateInstanceExtensionProperties()`가 자동으로 벡터를 반환하므로 더 간결하다.

#### 추가 Extension

개발 중에는 디버그 메시지를 받기 위해 추가 Extension을 활성화한다:

```cpp
std::vector<const char*> extensions(glfwExtensions, glfwExtensions + glfwExtensionCount);

#ifdef DEBUG
    extensions.push_back(VK_EXT_DEBUG_UTILS_EXTENSION_NAME);
#endif

#ifdef __APPLE__
    extensions.push_back(VK_KHR_PORTABILITY_ENUMERATION_EXTENSION_NAME);
#endif
```

### 2.4. Validation Layer 설정

Validation Layer는 개발 중 에러를 검출하는 디버깅 도구다.

Vulkan은 성능을 위해 런타임 에러 체크를 최소화한다. 잘못된 API 호출을 해도 크래시만 나거나 이상한 결과를 낸다.

Validation Layer 기능:

- API 사용 오류 감지 (파라미터 검증, 호출 순서 위반)
- 객체 생성/파괴 추적으로 리소스 누수 감지
- 스레드 안전성 검사
- Vulkan 호출 로깅 및 프로파일링
- 성능 경고 (비효율적인 사용 패턴 감지)

```cpp
const std::vector<const char*> validationLayers = {
    "VK_LAYER_KHRONOS_validation"
};

#ifdef DEBUG
    constexpr bool enableValidationLayers = true;
#else
    constexpr bool enableValidationLayers = false;
#endif
```

개발 중에만 사용한다. 릴리즈 빌드에서는 성능 저하가 크므로 비활성화해야 한다.

#### Validation Layer 지원 확인

```cpp
bool checkValidationLayerSupport(const vk::raii::Context& context) {
    auto availableLayers = context.enumerateInstanceLayerProperties();

    for (const char* layerName : validationLayers) {
        bool layerFound = false;

        for (const auto& layerProperties : availableLayers) {
            if (strcmp(layerName, layerProperties.layerName) == 0) {
                layerFound = true;
                break;
            }
        }

        if (!layerFound) {
            return false;
        }
    }

    return true;
}
```

### 2.5. Instance 생성

모든 정보를 모아 Instance를 생성한다:

```cpp
vk::raii::Instance createInstance(const vk::raii::Context& context) {
    // Validation Layer 지원 확인
    if (enableValidationLayers && !checkValidationLayerSupport(context)) {
        throw std::runtime_error("validation layers requested, but not available!");
    }

    // 애플리케이션 정보
    vk::ApplicationInfo appInfo{
        .pApplicationName = "Hello Triangle",
        .applicationVersion = VK_MAKE_VERSION(1, 0, 0),
        .pEngineName = "No Engine",
        .engineVersion = VK_MAKE_VERSION(1, 0, 0),
        .apiVersion = VK_API_VERSION_1_3
    };

    // Extension 목록 준비
    auto extensions = getRequiredExtensions();

    // Instance 생성 정보
    vk::InstanceCreateFlags flags{};
#ifdef __APPLE__
    // macOS는 portability enumeration flag 필요
    flags |= vk::InstanceCreateFlagBits::eEnumeratePortabilityKHR;
#endif

    vk::InstanceCreateInfo createInfo{
        .flags = flags,
        .pApplicationInfo = &appInfo,
        .enabledLayerCount = enableValidationLayers ?
            static_cast<uint32_t>(validationLayers.size()) : 0,
        .ppEnabledLayerNames = enableValidationLayers ?
            validationLayers.data() : nullptr,
        .enabledExtensionCount = static_cast<uint32_t>(extensions.size()),
        .ppEnabledExtensionNames = extensions.data()
    };

    // Instance 생성 (예외가 자동으로 발생)
    return vk::raii::Instance(context, createInfo);
}
```

#### C API와의 주요 차이점

1. **자동 에러 처리**: C API에서는 `vkCreateInstance`의 반환값이 `VK_SUCCESS`인지 확인해야 했지만, C++ RAII에서는 실패 시 자동으로 예외가 발생한다.
2. **자동 리소스 관리**: C API에서는 사용 후 `vkDestroyInstance`를 명시적으로 호출해야 했지만, `vk::raii::Instance`는 소멸될 때 자동으로 정리된다.
3. **타입 안전성**: Flags가 타입 안전한 `vk::InstanceCreateFlagBits` enum class로 제공된다.

사용 예:

```cpp
int main() {
    vk::raii::Context context;
    vk::raii::Instance instance = createInstance(context);

    // instance 사용
    // ...

    // 스코프를 벗어나면 자동으로 정리됨
}
```

---

## 3. Physical Device - GPU 선택

### 3.1. Physical Device란?

Physical Device는 시스템에 설치된 실제 GPU(또는 소프트웨어 렌더러)를 나타내는 핸들이다.

NVIDIA GPU와 Intel GPU가 모두 있다면 둘 다 Physical Device로 나타난다.

#### 핵심 특징: 조회 전용 (Querying)

Physical Device는 직접적인 명령 실행에 사용되지 않는다. 대신 GPU의 **속성, 기능, 한계**를 조회하는 데 사용된다.

조회 가능한 정보:

- **`vk::PhysicalDeviceProperties`**: 장치 이름, 공급업체 ID, API 버전, 한계값 (최대 텍스처 크기 등)
- **`vk::PhysicalDeviceFeatures`**: 지오메트리 셰이더, 테셀레이션 등 지원 기능
- **큐 패밀리 속성**: 장치가 제공하는 큐 패밀리 종류와 개수
- **메모리 속성**: 사용 가능한 메모리 타입과 힙 정보
- **지원 확장 목록**: 장치 레벨 확장 기능

Physical Device는 상태를 가지지 않으며, Logical Device를 생성하기 위한 전제 조건이다.

### 3.2. Physical Device 나열

Instance를 통해 사용 가능한 Physical Device 목록을 얻고, 적합한 GPU를 선택한다:

```cpp
vk::raii::PhysicalDevice pickPhysicalDevice(const vk::raii::Instance& instance) {
    // 모든 Physical Device 나열
    vk::raii::PhysicalDevices devices(instance);

    if (devices.empty()) {
        throw std::runtime_error("failed to find GPUs with Vulkan support!");
    }

    // 적합한 GPU 찾기
    for (const auto& device : devices) {
        if (isDeviceSuitable(device)) {
            return std::move(device);
        }
    }

    throw std::runtime_error("failed to find a suitable GPU!");
}
```

C API에서는 장치 개수를 먼저 조회하고, 벡터를 할당한 후 다시 호출하는 2단계 과정이 필요했다. 또한 `VK_NULL_HANDLE`을 확인해야 했다. C++ RAII에서는 `vk::raii::PhysicalDevices`가 자동으로 모든 장치를 벡터로 반환하므로 더 안전하고 간결하다.

### 3.3. GPU 선택 기준

모든 GPU가 같지 않다. 적합한 GPU를 선택해야 한다.

#### 기본 정보 조회

```cpp
auto deviceProperties = device.getProperties();

std::cout << "Device: " << deviceProperties.deviceName << std::endl;
std::cout << "Type: " << vk::to_string(deviceProperties.deviceType) << std::endl;
std::cout << "API Version: " << deviceProperties.apiVersion << std::endl;
```

deviceType:

- `vk::PhysicalDeviceType::eDiscreteGpu`: 독립 GPU (NVIDIA, AMD)
- `vk::PhysicalDeviceType::eIntegratedGpu`: 통합 GPU (Intel)
- `vk::PhysicalDeviceType::eVirtualGpu`: 가상 GPU
- `vk::PhysicalDeviceType::eCpu`: 소프트웨어 렌더러

#### 지원 기능 확인

```cpp
auto supportedFeatures = device.getFeatures();

if (!supportedFeatures.geometryShader) {
    return false;  // Geometry Shader 필수
}
```

#### GPU 점수 매기기

여러 GPU 중 최적의 GPU를 선택하는 방법:

```cpp
int rateDeviceSuitability(const vk::raii::PhysicalDevice& device) {
    auto deviceProperties = device.getProperties();
    auto deviceFeatures = device.getFeatures();

    int score = 0;

    // 독립 GPU 우대
    if (deviceProperties.deviceType == vk::PhysicalDeviceType::eDiscreteGpu) {
        score += 1000;
    }

    // 최대 텍스처 크기
    score += deviceProperties.limits.maxImageDimension2D;

    // Geometry Shader 필수
    if (!deviceFeatures.geometryShader) {
        return 0;
    }

    return score;
}
```

점수 기반으로 최적의 GPU를 선택할 수도 있다:

```cpp
vk::raii::PhysicalDevice pickBestPhysicalDevice(const vk::raii::Instance& instance) {
    vk::raii::PhysicalDevices devices(instance);

    if (devices.empty()) {
        throw std::runtime_error("failed to find GPUs with Vulkan support!");
    }

    int bestScore = 0;
    vk::raii::PhysicalDevice* bestDevice = nullptr;

    for (auto& device : devices) {
        int score = rateDeviceSuitability(device);
        if (score > bestScore) {
            bestScore = score;
            bestDevice = &device;
        }
    }

    if (bestScore == 0) {
        throw std::runtime_error("failed to find a suitable GPU!");
    }

    return std::move(*bestDevice);
}
```

---

## 4. Queue Family - GPU 작업 타입

### 4.1. Queue Family란?

Queue는 GPU에 명령을 제출하는 대기열이다.

GPU는 여러 종류의 작업을 처리한다. 각 작업 타입마다 별도의 Queue가 있고, 이를 Queue Family로 분류한다.

**Queue Family는 공통된 기능을 가진 하나 이상의 Queue들의 집합**이다.

#### 핵심 속성

각 Queue Family는 `vk::QueueFamilyProperties` 구조체로 정보를 제공한다:

- **`queueFlags`**: 어떤 작업을 처리할 수 있는지 나타내는 비트마스크
  - `vk::QueueFlagBits::eGraphics`: 렌더링 파이프라인 관련 그래픽스 작업
  - `vk::QueueFlagBits::eCompute`: 컴퓨트 셰이더 실행 같은 계산 작업
  - `vk::QueueFlagBits::eTransfer`: 버퍼/이미지 복사 같은 전송 작업
  - `vk::QueueFlagBits::eSparseBinding`: 희소 메모리 관리 작업
- **`queueCount`**: 해당 Queue Family에서 생성할 수 있는 최대 Queue 개수

주요 Queue Family 타입:

- **Graphics Queue**: 그리기 명령 (`eGraphics`)
- **Compute Queue**: 계산 명령 (`eCompute`)
- **Transfer Queue**: 데이터 전송 (`eTransfer`)
- **Present Queue**: 화면 출력 (별도 비트 없음, Surface 지원 확인 필요)

### 4.2. Queue Family 찾기

GPU가 지원하는 Queue Family 목록을 조회한다:

```cpp
struct QueueFamilyIndices {
    std::optional<uint32_t> graphicsFamily;
    std::optional<uint32_t> presentFamily;  // 다음 편에서 사용

    bool isComplete() const {
        return graphicsFamily.has_value() && presentFamily.has_value();
    }
};

QueueFamilyIndices findQueueFamilies(const vk::raii::PhysicalDevice& device) {
    QueueFamilyIndices indices;

    // Queue Family 속성 조회
    auto queueFamilies = device.getQueueFamilyProperties();

    // Graphics Queue 지원하는 Queue Family 찾기
    for (uint32_t i = 0; i < queueFamilies.size(); i++) {
        if (queueFamilies[i].queueFlags & vk::QueueFlagBits::eGraphics) {
            indices.graphicsFamily = i;
        }

        if (indices.isComplete()) {
            break;
        }
    }

    return indices;
}
```

#### 달라진 점

C API에서는 Queue Family 개수를 먼저 조회하고, 벡터를 할당한 후 다시 호출해야 했다. C++ RAII에서는 `device.getQueueFamilyProperties()`가 자동으로 벡터를 반환한다. 또한 `VK_QUEUE_GRAPHICS_BIT` 같은 매크로 대신 타입 안전한 `vk::QueueFlagBits::eGraphics`를 사용한다.

#### Queue Flags 타입

queueFlags (비트 플래그):

- `vk::QueueFlagBits::eGraphics`: 그리기 지원
- `vk::QueueFlagBits::eCompute`: 계산 지원
- `vk::QueueFlagBits::eTransfer`: 전송 지원

대부분의 GPU는 Graphics Queue가 모든 기능을 지원한다. 일부 GPU는 전송 전용 Queue를 따로 제공한다.

#### 디버깅: Queue Family 정보 출력

```cpp
void printQueueFamilies(const vk::raii::PhysicalDevice& device) {
    auto queueFamilies = device.getQueueFamilyProperties();

    std::cout << "Available Queue Families:" << std::endl;
    for (uint32_t i = 0; i < queueFamilies.size(); i++) {
        std::cout << "  Queue Family " << i << ":" << std::endl;
        std::cout << "    Queue Count: " << queueFamilies[i].queueCount << std::endl;
        std::cout << "    Graphics: "
                  << ((queueFamilies[i].queueFlags & vk::QueueFlagBits::eGraphics) ? "Yes" : "No")
                  << std::endl;
        std::cout << "    Compute: "
                  << ((queueFamilies[i].queueFlags & vk::QueueFlagBits::eCompute) ? "Yes" : "No")
                  << std::endl;
        std::cout << "    Transfer: "
                  << ((queueFamilies[i].queueFlags & vk::QueueFlagBits::eTransfer) ? "Yes" : "No")
                  << std::endl;
    }
}
```

---

## 5. 자주 겪는 문제와 해결법

### 5.1. "failed to create instance!"

**원인**: Extension이나 Layer를 찾지 못함

**해결**:

1. `vulkaninfo`로 지원 Extension 확인:

   ```bash
   vulkaninfo | grep -A 10 "Instance Extensions"
   ```

2. GLFW가 요구하는 Extension 출력:

   ```cpp
   uint32_t count = 0;
   const char** extensions = glfwGetRequiredInstanceExtensions(&count);
   for (uint32_t i = 0; i < count; i++) {
       std::cout << extensions[i] << std::endl;
   }
   ```

### 5.2. "failed to find GPUs with Vulkan support!"

**원인**: Vulkan 드라이버가 없거나 오래됨

**해결**:

- **Windows**: GPU 드라이버 업데이트
- **Linux**: `sudo apt install mesa-vulkan-drivers` (Intel GPU)
- **macOS**: Vulkan SDK 재설치 (MoltenVK 확인)

### 5.3. "validation layers requested, but not available!"

**원인**: Vulkan SDK의 Validation Layer가 설치 안 됨

**해결**:

```bash
# 확인
ls $VULKAN_SDK/share/vulkan/explicit_layer.d/

# 있어야 하는 파일: VkLayer_khronos_validation.json
```

없으면 Vulkan SDK 재설치.

#### macOS 추가 설정

macOS에서는 Validation Layer 파일이 설치되어 있어도 환경변수 설정이 필요하다:

```bash
# ~/.zshrc에 추가
export VK_LAYER_PATH=/opt/homebrew/share/vulkan/explicit_layer.d
export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH

# 적용
source ~/.zshrc
```

환경변수 역할:

- `VK_LAYER_PATH`: Validation Layer JSON 설정 파일 위치
- `DYLD_LIBRARY_PATH`: 동적 라이브러리 (`.dylib`) 검색 경로

### 5.4. Queue Family를 못 찾을 때

**원인**: 잘못된 GPU 선택 또는 구식 드라이버

**디버깅**:

```cpp
auto queueFamilies = device.getQueueFamilyProperties();

for (uint32_t i = 0; i < queueFamilies.size(); i++) {
    std::cout << "Queue Family " << i << ":" << std::endl;
    std::cout << "  Queue Count: " << queueFamilies[i].queueCount << std::endl;
    std::cout << "  Graphics: "
              << ((queueFamilies[i].queueFlags & vk::QueueFlagBits::eGraphics) ? "Yes" : "No")
              << std::endl;
}
```

---

## 6. 핵심 개념 정리

### Context (C++ RAII 전용)

- Vulkan 동적 라이브러리 로드 및 함수 포인터 관리
- 시스템 정보 조회 (사용 가능한 Extension, Layer 등)
- RAII를 통한 자동 리소스 관리
- 모든 Vulkan 객체 생성의 시작점

### Instance

- Vulkan 라이브러리와의 실질적인 연결 통로
- Extension과 Validation Layer 활성화
- Physical Device 목록 조회
- 애플리케이션당 하나

### Physical Device

- 실제 GPU 하드웨어
- 정보 조회만 가능 (읽기 전용)
- 최적의 GPU 선택 필요
- Logical Device 생성을 위한 전제 조건

### Queue Family

- GPU 작업 타입별 Queue 그룹
- Graphics, Compute, Transfer 등
- Queue Family 인덱스 저장 필요
- Logical Device 생성 시 사용

---

## 마치며

Instance와 Physical Device 선택은 Vulkan 초기화의 첫 단계다.

핵심:

1. **Context** (C++ RAII): Vulkan 라이브러리 로드 및 함수 포인터 관리
2. **Instance**: Vulkan 라이브러리와의 실질적인 연결
3. **Extension과 Validation Layer**: 명시적으로 활성화 필요
4. **Physical Device**: 읽기 전용, 정보 조회만 가능
5. **Queue Family**: 인덱스를 저장하여 Logical Device 생성 시 사용

**C++ RAII의 장점**:

- 자동 리소스 관리 (메모리 누수 방지)
- 자동 에러 처리 (예외 기반)
- 타입 안전성 (enum class 사용)
- 간결한 코드 (반복적인 크기 조회 불필요)

다음 편에서는 Logical Device를 생성하고 Queue를 획득한다.

---

**다음 편 예고**: [Vulkan] Ep07. Logical Device와 Queue 생성
