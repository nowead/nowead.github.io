+++
date = '2025-09-16T14:00:00+09:00'
draft = false
title = '[Vulkan] Ep06. Instance와 Device - Vulkan의 첫걸음'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Instance", "Device", "Queue", "Extension", "Layer"]
categories = ["그래픽스 프로그래밍"]
+++

## 시작하며

[Ep05]에서 개발 환경을 구축했다. 이제 Vulkan 코드를 작성한다.

OpenGL은 Context가 자동으로 만들어진다. Vulkan은 Instance, Physical Device, Logical Device를 직접 생성해야 한다.

이 글에서는 **Instance 생성**부터 **Device 선택**, **Queue 획득**까지 정리한다.

---

## 1. Vulkan 초기화 과정 전체 흐름

Vulkan에서 삼각형 하나를 그리려면 다음 단계를 거쳐야 한다:

```
1. Instance 생성        → Vulkan 라이브러리와 연결
2. Physical Device 선택 → GPU 선택
3. Logical Device 생성  → GPU와 통신할 인터페이스 생성
4. Queue 획득          → GPU에 명령을 제출할 큐 얻기
5. Surface 생성        → 윈도우와 연결 (다음 편)
6. Swapchain 생성      → 화면 출력 준비 (다음 편)
7. Pipeline 생성       → 셰이더 설정 (다음 편)
8. Command Buffer      → 실제 그리기 명령 (다음 편)
```

이번 글에서는 **1~4번**까지 다룬다.

---

## 2. Instance - Vulkan의 진입점

### 2.1. Instance란?

**Instance**는 Vulkan 애플리케이션과 Vulkan 라이브러리(`libvulkan.so`, `vulkan-1.dll` 등) 사이의 연결 통로다.

**Instance의 역할**:
- Vulkan 런타임 초기화
- Extension과 Validation Layer 설정
- Physical Device(GPU) 목록 조회

### 2.2. VkApplicationInfo 설정

먼저 애플리케이션 정보를 설정한다:

```cpp
VkApplicationInfo appInfo{};
appInfo.sType = VK_STRUCTURE_TYPE_APPLICATION_INFO;
appInfo.pApplicationName = "Hello Triangle";
appInfo.applicationVersion = VK_MAKE_VERSION(1, 0, 0);
appInfo.pEngineName = "No Engine";
appInfo.engineVersion = VK_MAKE_VERSION(1, 0, 0);
appInfo.apiVersion = VK_API_VERSION_1_3;  // Vulkan 1.3 사용
```

**주요 필드**:
- `sType`: 구조체 타입 (Vulkan의 모든 구조체는 이걸 가짐)
- `pApplicationName`: 앱 이름 (디버깅 시 유용)
- `apiVersion`: 사용할 Vulkan 버전

**왜 이런 정보를 요구하나?**
- GPU 드라이버가 애플리케이션에 맞게 최적화할 수 있음
- 디버깅 도구(RenderDoc 등)에서 식별 가능

### 2.3. Extension 설정

Extension은 Vulkan의 추가 기능이다. 기본 API는 최소 기능만 제공한다.

#### 필수 Extension: GLFW가 요구하는 Extension

GLFW로 윈도우를 만들려면 다음 Extension들이 필요하다:

```cpp
uint32_t glfwExtensionCount = 0;
const char** glfwExtensions;

// GLFW가 필요로 하는 Extension 목록 가져오기
glfwExtensions = glfwGetRequiredInstanceExtensions(&glfwExtensionCount);
```

**Windows**: `VK_KHR_surface`, `VK_KHR_win32_surface`
**Linux**: `VK_KHR_surface`, `VK_KHR_xlib_surface`
**macOS**: `VK_KHR_surface`, `VK_EXT_metal_surface` (MoltenVK)

#### 추가 Extension: 디버깅용

개발 중에는 디버그 메시지를 받기 위해 추가 Extension을 활성화한다:

```cpp
std::vector<const char*> extensions(glfwExtensions, glfwExtensions + glfwExtensionCount);

#ifdef DEBUG
    extensions.push_back(VK_EXT_DEBUG_UTILS_EXTENSION_NAME);
#endif
```

### 2.4. Validation Layer 설정

Validation Layer는 개발 중 에러를 검출하는 디버깅 도구다.

Vulkan은 성능을 위해 에러 체크를 하지 않는다. 잘못된 API 호출을 해도 크래시만 나거나 이상한 결과를 낸다.

Validation Layer 활성화 시:
- API 사용 오류 감지 (잘못된 파라미터, 순서 위반)
- 메모리 누수 감지
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

    // Instance 생성
    if (vkCreateInstance(&createInfo, nullptr, &instance) != VK_SUCCESS) {
        throw std::runtime_error("failed to create instance!");
    }
}
```

성공 시 `VkInstance instance`에 유효한 핸들이 저장된다.

---

## 3. Physical Device - GPU 선택하기

### 3.1. Physical Device란?

Physical Device는 시스템에 설치된 실제 GPU(또는 소프트웨어 렌더러)다.

NVIDIA GPU와 Intel GPU가 모두 있다면 둘 다 Physical Device로 나타난다.

Physical Device의 역할:

- GPU 정보 조회 (이름, 메모리, 지원 기능)
- Queue Family 조회

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
std::cout << "Type: " << deviceProperties.deviceType << std::endl;  // 0=통합, 1=독립
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

    // 최대 텍스처 크기가 클수록 좋음
    score += deviceProperties.limits.maxImageDimension2D;

    // Geometry Shader 필수
    if (!deviceFeatures.geometryShader) {
        return 0;
    }

    return score;
}
```

---

## 4. Queue Family - GPU와의 통신 채널

### 4.1. Queue Family란?

Queue는 GPU에 명령을 제출하는 대기열이다.

GPU는 여러 종류의 작업을 처리한다. 각 작업 타입마다 별도의 Queue가 있고, 이를 Queue Family로 분류한다.

주요 Queue Family 타입:

- **Graphics Queue**: 그리기 명령
- **Compute Queue**: 계산 명령 (GPGPU)
- **Transfer Queue**: 데이터 전송
- **Present Queue**: 화면 출력

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

## 5. Logical Device - GPU와의 인터페이스

### 5.1. Logical Device란?

Logical Device는 Physical Device(GPU)와 상호작용하기 위한 소프트웨어 인터페이스다.

Physical Device vs Logical Device:

- **Physical Device**: 하드웨어 (읽기 전용)
- **Logical Device**: GPU와 통신하는 통로 (명령 제출, 메모리 할당)

하나의 Physical Device에서 여러 Logical Device 생성 가능:

- 각 Logical Device는 독립된 설정
- 멀티스레드 환경에서 유용

### 5.2. Logical Device 생성

```cpp
void createLogicalDevice() {
    QueueFamilyIndices indices = findQueueFamilies(physicalDevice);

    // Queue 생성 정보
    VkDeviceQueueCreateInfo queueCreateInfo{};
    queueCreateInfo.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queueCreateInfo.queueFamilyIndex = indices.graphicsFamily.value();
    queueCreateInfo.queueCount = 1;

    float queuePriority = 1.0f;  // 0.0 ~ 1.0 (높을수록 우선순위 높음)
    queueCreateInfo.pQueuePriorities = &queuePriority;

    // Device 기능 설정
    VkPhysicalDeviceFeatures deviceFeatures{};

    // Device 생성 정보
    VkDeviceCreateInfo createInfo{};
    createInfo.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    createInfo.pQueueCreateInfos = &queueCreateInfo;
    createInfo.queueCreateInfoCount = 1;
    createInfo.pEnabledFeatures = &deviceFeatures;

    // Device Extension (Swapchain 등)
    createInfo.enabledExtensionCount = 0;  // 일단 없음

    // Validation Layer (구버전 호환용)
    if (enableValidationLayers) {
        createInfo.enabledLayerCount = static_cast<uint32_t>(validationLayers.size());
        createInfo.ppEnabledLayerNames = validationLayers.data();
    } else {
        createInfo.enabledLayerCount = 0;
    }

    // Logical Device 생성
    if (vkCreateDevice(physicalDevice, &createInfo, nullptr, &device) != VK_SUCCESS) {
        throw std::runtime_error("failed to create logical device!");
    }

    // Graphics Queue 핸들 획득
    vkGetDeviceQueue(device, indices.graphicsFamily.value(), 0, &graphicsQueue);
}
```

### 5.3. 코드 분석

#### Queue 우선순위

```cpp
float queuePriority = 1.0f;
```

- 여러 Queue를 사용할 때 스케줄링 우선순위
- 0.0(낮음) ~ 1.0(높음)
- 단일 Queue 사용 시 의미 없음

#### Queue 핸들 획득

```cpp
vkGetDeviceQueue(device, indices.graphicsFamily.value(), 0, &graphicsQueue);
```

- `device`: 방금 만든 Logical Device
- `indices.graphicsFamily.value()`: Queue Family 인덱스
- `0`: Queue 인덱스 (같은 Family 내에서 여러 Queue 가능)
- `&graphicsQueue`: 획득한 Queue 핸들을 저장할 변수

이제 `graphicsQueue`를 통해 GPU에 명령을 제출할 수 있다.

---

## 6. 정리 - 전체 코드 구조

### 6.1. 클래스 멤버 변수

```cpp
class HelloTriangleApplication {
private:
    GLFWwindow* window;

    VkInstance instance;
    VkPhysicalDevice physicalDevice = VK_NULL_HANDLE;
    VkDevice device;

    VkQueue graphicsQueue;
};
```

### 6.2. 초기화 순서

```cpp
void initVulkan() {
    createInstance();
    pickPhysicalDevice();
    createLogicalDevice();
}
```

### 6.3. 정리 (Cleanup)

Vulkan은 수동 메모리 관리다. 만든 순서의 역순으로 정리한다:

```cpp
void cleanup() {
    vkDestroyDevice(device, nullptr);
    vkDestroyInstance(instance, nullptr);

    glfwDestroyWindow(window);
    glfwTerminate();
}
```

주의사항:

- Physical Device는 정리 안 함 (정보 조회만 함)
- Queue도 정리 안 함 (Device 정리 시 자동)

---

## 7. 실행 및 검증

### 7.1. 빌드 및 실행

```bash
make
make run
```

### 7.2. 출력 예시

```
Device: NVIDIA GeForce RTX 3080
Type: Discrete GPU
Graphics Queue Family: 0
```

### 7.3. 디버그 메시지 확인

Validation Layer를 활성화했다면, 콘솔에 다음과 같은 메시지가 나올 수 있다:

```
Validation Layer: Debug utils messenger created
Validation Layer: Device created successfully
```

---

## 8. 자주 겪는 문제와 해결법

### 8.1. "failed to create instance!"

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

### 8.2. "failed to find GPUs with Vulkan support!"

**원인**: Vulkan 드라이버가 없거나 오래됨

**해결**:

- **Windows**: GPU 드라이버 업데이트
- **Linux**: `sudo apt install mesa-vulkan-drivers` (Intel GPU)
- **macOS**: Vulkan SDK 재설치 (MoltenVK 확인)

### 8.3. "validation layers requested, but not available!"

**원인**: Vulkan SDK의 Validation Layer가 설치 안 됨

**해결**:

```bash
# 확인
ls $VULKAN_SDK/share/vulkan/explicit_layer.d/

# 있어야 하는 파일: VkLayer_khronos_validation.json
```

없으면 Vulkan SDK 재설치.

### 8.4. Queue Family를 못 찾을 때

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

## 9. 핵심 개념 정리

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

### Logical Device

- GPU와 통신하는 인터페이스
- Queue 생성 및 명령 제출
- 대부분의 Vulkan 함수는 Logical Device를 첫 번째 인자로 받음

### Queue

- GPU에 명령을 제출하는 대기열
- Logical Device 생성 시 함께 생성
- 멀티스레드에서는 각 스레드가 별도의 Queue 사용 권장

---

## 10. 다음 단계

지금까지 Vulkan과 GPU를 연결했다. 아직 화면에는 아무것도 나타나지 않는다.

다음 편:

1. **Window Surface** 생성 - GLFW 윈도우와 Vulkan 연결
2. **Swapchain** 생성 - 화면 출력 준비
3. **Present Queue** 설정

---

## 마치며

Instance와 Device 생성 과정은 한 번 설정하면 거의 변경할 일이 없다.

핵심:

1. Instance → Physical Device → Logical Device 순서로 생성
2. Queue Family 인덱스 저장
3. Validation Layer는 개발 중에만 사용
4. 정리는 생성 순서의 역순

다음 편에서는 화면 출력을 준비한다.

---

**다음 편 예고**: [Vulkan] Ep07. Surface와 Swapchain - 화면 출력 준비
