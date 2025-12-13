+++
date = '2025-09-13T14:00:00+09:00'
draft = false
title = '[Vulkan] Ep06. Instance와 Physical Device'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Instance", "Physical Device", "Extension", "Validation Layer"]
categories = ["그래픽스 프로그래밍"]
+++

## 시작하며

[Ep05]에서 개발 환경을 구축했다. 이제 Vulkan 코드를 작성한다.

OpenGL은 Context가 자동으로 만들어진다. Vulkan은 Instance, Physical Device, Logical Device를 직접 생성해야 한다.

이 글에서는 **Instance 생성**과 **Physical Device 선택**까지 정리한다.

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

### 2.1. Instance란?

Instance는 Vulkan 애플리케이션과 Vulkan 라이브러리(`libvulkan.so`, `vulkan-1.dll` 등) 사이의 연결 통로다.

Instance의 역할:

- Vulkan 런타임 초기화
- Extension과 Validation Layer 설정
- Physical Device(GPU) 목록 조회

### 2.2. VkApplicationInfo 설정

애플리케이션 정보를 설정한다:

```cpp
VkApplicationInfo appInfo{};
appInfo.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
appInfo.pApplicationName = "Hello Triangle";
appInfo.applicationVersion = VK_MAKE_VERSION(1, 0, 0);
appInfo.pEngineName = "No Engine";
appInfo.engineVersion = VK_MAKE_VERSION(1, 0, 0);
appInfo.apiVersion = VK_API_VERSION_1_3;
```

주요 필드:

- `sType`: 구조체 타입 (Vulkan의 모든 구조체에 필수)
- `pApplicationName`: 앱 이름 (디버깅 시 유용)
- `apiVersion`: 사용할 Vulkan 버전

GPU 드라이버는 이 정보로 애플리케이션에 맞게 최적화할 수 있다.

### 2.3. Extension 설정

Extension은 Vulkan의 추가 기능이다. 기본 API는 최소 기능만 제공한다.

#### GLFW가 요구하는 Extension

GLFW로 윈도우를 만들려면 Extension이 필요하다:

```cpp
uint32_t glfwExtensionCount = 0;
const char** glfwExtensions;
glfwExtensions = glfwGetRequiredInstanceExtensions(&glfwExtensionCount);
```

플랫폼별 필수 Extension:

- **Windows**: `VK_KHR_surface`, `VK_KHR_win32_surface`
- **Linux**: `VK_KHR_surface`, `VK_KHR_xlib_surface`
- **macOS**: `VK_KHR_surface`, `VK_EXT_metal_surface`, `VK_KHR_portability_enumeration`

macOS는 MoltenVK를 사용하므로 `VK_KHR_portability_enumeration`이 추가로 필요하다.

#### Extension 지원 확인

GLFW가 요구하는 Extension을 시스템이 지원하는지 확인한다:

```cpp
// 시스템이 지원하는 Extension 목록 조회
std::vector<VkExtensionProperties> availableExtensions;
uint32_t extensionCount;
vkEnumerateInstanceExtensionProperties(nullptr, &extensionCount, nullptr);
availableExtensions.resize(extensionCount);
vkEnumerateInstanceExtensionProperties(nullptr, &extensionCount, availableExtensions.data());

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
        throw std::runtime_error("Required extension not supported");
    }
}
```

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

Vulkan은 성능을 위해 에러 체크를 하지 않는다. 잘못된 API 호출을 해도 크래시만 나거나 이상한 결과를 낸다.

Validation Layer 기능:

- API 사용 오류 감지 (파라미터 검증, 호출 순서 위반)
- 객체 생성/파괴 추적으로 리소스 누수 감지
- 스레드 안전성 검사
- Vulkan 호출 로깅 및 프로파일링
- 성능 경고

```cpp
const std::vector<const char*> validationLayers = {
    "VK_LAYER_KHRONOS_validation"
};

#ifdef DEBUG
    const bool enableValidationLayers = true;
#else
    const bool enableValidationLayers = false;
#endif
```

개발 중에만 사용한다. 릴리즈 빌드에서는 성능 저하가 크다.

#### Validation Layer 지원 확인

```cpp
bool checkValidationLayerSupport() {
    uint32_t layerCount;
    vkEnumerateInstanceLayerProperties(&layerCount, nullptr);

    std::vector<VkLayerProperties> availableLayers(layerCount);
    vkEnumerateInstanceLayerProperties(&layerCount, availableLayers.data());

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
void createInstance() {
    if (enableValidationLayers && !checkValidationLayerSupport()) {
        throw std::runtime_error("validation layers requested, but not available!");
    }

    VkApplicationInfo appInfo{};
    // ... (위에서 설정한 내용)

    VkInstanceCreateInfo createInfo{};
    createInfo.sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    createInfo.pApplicationInfo = &appInfo;

    // Extension 설정
    auto extensions = getRequiredExtensions();
    createInfo.enabledExtensionCount = static_cast<uint32_t>(extensions.size());
    createInfo.ppEnabledExtensionNames = extensions.data();

    // Validation Layer 설정
    if (enableValidationLayers) {
        createInfo.enabledLayerCount = static_cast<uint32_t>(validationLayers.size());
        createInfo.ppEnabledLayerNames = validationLayers.data();
    } else {
        createInfo.enabledLayerCount = 0;
    }

#ifdef __APPLE__
    // macOS는 portability enumeration flag 필요
    createInfo.flags |= VK_INSTANCE_CREATE_ENUMERATE_PORTABILITY_BIT_KHR;
#endif

    // Instance 생성
    if (vkCreateInstance(&createInfo, nullptr, &instance) != VK_SUCCESS) {
        throw std::runtime_error("failed to create instance!");
    }
}
```

성공 시 `VkInstance instance`에 유효한 핸들이 저장된다.

---

## 3. Physical Device - GPU 선택

### 3.1. Physical Device란?

Physical Device는 시스템에 설치된 실제 GPU(또는 소프트웨어 렌더러)를 나타내는 핸들이다.

NVIDIA GPU와 Intel GPU가 모두 있다면 둘 다 Physical Device로 나타난다.

#### 핵심 특징: 조회 전용 (Querying)

Physical Device는 직접적인 명령 실행에 사용되지 않는다. 대신 GPU의 **속성, 기능, 한계**를 조회하는 데 사용된다.

조회 가능한 정보:

- **`VkPhysicalDeviceProperties`**: 장치 이름, 공급업체 ID, API 버전, 한계값 (최대 텍스처 크기 등)
- **`VkPhysicalDeviceFeatures`**: 지오메트리 셰이더, 테셀레이션 등 지원 기능
- **큐 패밀리 속성**: 장치가 제공하는 큐 패밀리 종류와 개수
- **메모리 속성**: 사용 가능한 메모리 타입과 힙 정보
- **지원 확장 목록**: 장치 레벨 확장 기능

Physical Device는 상태를 가지지 않으며, Logical Device를 생성하기 위한 전제 조건이다.

### 3.2. Physical Device 나열

```cpp
void pickPhysicalDevice() {
    uint32_t deviceCount = 0;
    vkEnumeratePhysicalDevices(instance, &deviceCount, nullptr);

    if (deviceCount == 0) {
        throw std::runtime_error("failed to find GPUs with Vulkan support!");
    }

    std::vector<VkPhysicalDevice> devices(deviceCount);
    vkEnumeratePhysicalDevices(instance, &deviceCount, devices.data());

    for (const auto& device : devices) {
        if (isDeviceSuitable(device)) {
            physicalDevice = device;
            break;
        }
    }

    if (physicalDevice == VK_NULL_HANDLE) {
        throw std::runtime_error("failed to find a suitable GPU!");
    }
}
```

### 3.3. GPU 선택 기준

모든 GPU가 같지 않다. 적합한 GPU를 선택해야 한다.

#### 기본 정보 조회

```cpp
VkPhysicalDeviceProperties deviceProperties;
vkGetPhysicalDeviceProperties(device, &deviceProperties);

std::cout << "Device: " << deviceProperties.deviceName << std::endl;
std::cout << "Type: " << deviceProperties.deviceType << std::endl;
std::cout << "API Version: " << deviceProperties.apiVersion << std::endl;
```

deviceType:

- `VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU`: 독립 GPU (NVIDIA, AMD)
- `VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU`: 통합 GPU (Intel)
- `VK_PHYSICAL_DEVICE_TYPE_VIRTUAL_GPU`: 가상 GPU
- `VK_PHYSICAL_DEVICE_TYPE_CPU`: 소프트웨어 렌더러

#### 지원 기능 확인

```cpp
VkPhysicalDeviceFeatures supportedFeatures;
vkGetPhysicalDeviceFeatures(device, &supportedFeatures);

if (!supportedFeatures.geometryShader) {
    return false;  // Geometry Shader 필수
}
```

#### GPU 점수 매기기

여러 GPU 중 최적의 GPU를 선택하는 방법:

```cpp
int rateDeviceSuitability(VkPhysicalDevice device) {
    VkPhysicalDeviceProperties deviceProperties;
    VkPhysicalDeviceFeatures deviceFeatures;
    vkGetPhysicalDeviceProperties(device, &deviceProperties);
    vkGetPhysicalDeviceFeatures(device, &deviceFeatures);

    int score = 0;

    // 독립 GPU 우대
    if (deviceProperties.deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU) {
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

---

## 4. Queue Family - GPU 작업 타입

### 4.1. Queue Family란?

Queue는 GPU에 명령을 제출하는 대기열이다.

GPU는 여러 종류의 작업을 처리한다. 각 작업 타입마다 별도의 Queue가 있고, 이를 Queue Family로 분류한다.

**Queue Family는 공통된 기능을 가진 하나 이상의 Queue들의 집합**이다.

#### 핵심 속성

각 Queue Family는 `VkQueueFamilyProperties` 구조체로 정보를 제공한다:

- **`queueFlags`**: 어떤 작업을 처리할 수 있는지 나타내는 비트마스크
  - `VK_QUEUE_GRAPHICS_BIT`: 렌더링 파이프라인 관련 그래픽스 작업
  - `VK_QUEUE_COMPUTE_BIT`: 컴퓨트 셰이더 실행 같은 계산 작업
  - `VK_QUEUE_TRANSFER_BIT`: 버퍼/이미지 복사 같은 전송 작업
  - `VK_QUEUE_SPARSE_BINDING_BIT`: 희소 메모리 관리 작업
- **`queueCount`**: 해당 Queue Family에서 생성할 수 있는 최대 Queue 개수

주요 Queue Family 타입:

- **Graphics Queue**: 그리기 명령 (VK_QUEUE_GRAPHICS_BIT)
- **Compute Queue**: 계산 명령 (VK_QUEUE_COMPUTE_BIT)
- **Transfer Queue**: 데이터 전송 (VK_QUEUE_TRANSFER_BIT)
- **Present Queue**: 화면 출력 (별도 비트 없음, Surface 지원 확인 필요)

### 4.2. Queue Family 찾기

GPU가 지원하는 Queue Family 목록을 조회한다:

```cpp
struct QueueFamilyIndices {
    std::optional<uint32_t> graphicsFamily;
    std::optional<uint32_t> presentFamily;  // 다음 편에서 사용

    bool isComplete() {
        return graphicsFamily.has_value() && presentFamily.has_value();
    }
};

QueueFamilyIndices findQueueFamilies(VkPhysicalDevice device) {
    QueueFamilyIndices indices;

    uint32_t queueFamilyCount = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(device, &queueFamilyCount, nullptr);

    std::vector<VkQueueFamilyProperties> queueFamilies(queueFamilyCount);
    vkGetPhysicalDeviceQueueFamilyProperties(device, &queueFamilyCount, queueFamilies.data());

    int i = 0;
    for (const auto& queueFamily : queueFamilies) {
        // Graphics Queue 지원 확인
        if (queueFamily.queueFlags & VK_QUEUE_GRAPHICS_BIT) {
            indices.graphicsFamily = i;
        }

        if (indices.isComplete()) {
            break;
        }

        i++;
    }

    return indices;
}
```

queueFlags (비트 플래그):

- `VK_QUEUE_GRAPHICS_BIT`: 그리기 지원
- `VK_QUEUE_COMPUTE_BIT`: 계산 지원
- `VK_QUEUE_TRANSFER_BIT`: 전송 지원

대부분의 GPU는 Graphics Queue가 모든 기능을 지원한다. 일부 GPU는 전송 전용 Queue를 따로 제공한다.

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
for (const auto& queueFamily : queueFamilies) {
    std::cout << "Queue Family " << i << ":" << std::endl;
    std::cout << "  Queue Count: " << queueFamily.queueCount << std::endl;
    std::cout << "  Graphics: " << (queueFamily.queueFlags & VK_QUEUE_GRAPHICS_BIT ? "Yes" : "No") << std::endl;
    i++;
}
```

---

## 6. 핵심 개념 정리

### Instance

- Vulkan 라이브러리와의 연결 통로
- Extension과 Validation Layer 설정
- 애플리케이션당 하나

### Physical Device

- 실제 GPU 하드웨어
- 정보 조회만 가능 (읽기 전용)
- 최적의 GPU 선택 필요

### Queue Family

- GPU 작업 타입별 Queue 그룹
- Graphics, Compute, Transfer 등
- Queue Family 인덱스 저장 필요

---

## 마치며

Instance와 Physical Device 선택은 Vulkan 초기화의 첫 단계다.

핵심:

1. Instance는 Vulkan 라이브러리와의 연결
2. Extension과 Validation Layer를 명시적으로 활성화
3. Physical Device는 읽기 전용, 정보 조회만 가능
4. Queue Family 인덱스를 저장해야 함

다음 편에서는 Logical Device를 생성하고 Queue를 획득한다.

---

**다음 편 예고**: [Vulkan] Ep07. Logical Device와 Queue 생성
