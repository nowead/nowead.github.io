---
title: "[Vulkan] EP07. Logical Device와 Queue"
date: 2025-12-01
series: ["Vulkan 학습"]
tags: ["Vulkan", "Graphics", "Device", "Queue"]
---

# EP07. Logical Device와 Queue

## 1. Logical Device란?

Physical Device는 GPU 하드웨어 자체를 나타내는 읽기 전용 객체다. 실제로 GPU와 상호작용하려면 **Logical Device**가 필요하다.

**Logical Device는 특정 Physical Device와의 활성화된 연결(session)을 나타내는 객체 핸들**이다. 애플리케이션과 GPU 드라이버 간의 주된 상호작용이 이 객체를 통해 이루어진다.

### Physical Device vs Logical Device

**Physical Device (VkPhysicalDevice)**
- GPU 하드웨어 정보 조회
- 읽기 전용, 상태 없음
- Instance가 관리

↓

**Logical Device (VkDevice)**
- GPU와 실제 상호작용
- 인터페이스 및 컨텍스트 역할
- 애플리케이션이 생성/파괴

### Logical Device의 역할: 인터페이스 및 컨텍스트

Logical Device는 Vulkan의 대부분 작업을 위한 기본 인터페이스다:

1. **객체 생성**: Buffer, Image, Pipeline, Semaphore 등 거의 모든 Vulkan 객체 생성 함수는 `VkDevice`를 첫 번째 파라미터로 받는다
2. **Queue 핸들 획득**: `vkGetDeviceQueue`로 명령 제출용 Queue 핸들을 가져온다
3. **상태 관리**: 활성화된 Extension, Feature 등 Physical Device를 사용하는 방식에 대한 모든 상태를 캡슐화한다
4. **메모리 관리**: GPU 메모리 할당 및 해제
5. **동기화**: Fence, Semaphore를 통한 GPU-CPU 동기화

Logical Device는 Physical Device의 모든 잠재적 기능 중 **애플리케이션이 사용하기로 요청하고 드라이버가 허가한 기능들의 집합**을 논리적으로 표현한다.

## 2. Logical Device 생성

### 2.1. Device Queue 지정

Logical Device 생성 시 사용할 Queue를 지정해야 한다.

```cpp
VkDeviceQueueCreateInfo queueCreateInfo{};
queueCreateInfo.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
queueCreateInfo.queueFamilyIndex = indices.graphicsFamily.value();
queueCreateInfo.queueCount = 1;

float queuePriority = 1.0f;
queueCreateInfo.pQueuePriorities = &queuePriority;
```

**주요 필드**:
- `queueFamilyIndex`: 사용할 Queue Family의 인덱스
- `queueCount`: 생성할 Queue 개수
- `pQueuePriorities`: Queue 우선순위 배열 (0.0 ~ 1.0)

### 2.2. Device Features 지정

GPU에서 사용할 기능을 명시적으로 활성화해야 한다.

```cpp
VkPhysicalDeviceFeatures deviceFeatures{};
deviceFeatures.samplerAnisotropy = VK_TRUE;  // 비등방성 필터링
deviceFeatures.fillModeNonSolid = VK_TRUE;   // Wireframe 렌더링
```

사용하지 않는 기능은 `VK_FALSE`로 두어야 한다. Vulkan은 기본적으로 모든 기능이 비활성화되어 있다.

### 2.3. VkDeviceCreateInfo

```cpp
VkDeviceCreateInfo createInfo{};
createInfo.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
createInfo.pQueueCreateInfos = &queueCreateInfo;
createInfo.queueCreateInfoCount = 1;
createInfo.pEnabledFeatures = &deviceFeatures;
createInfo.enabledExtensionCount = 0;
createInfo.ppEnabledExtensionNames = nullptr;
```

### 2.4. Device 생성

```cpp
VkDevice device;
if (vkCreateDevice(physicalDevice, &createInfo, nullptr, &device) != VK_SUCCESS) {
    throw std::runtime_error("Failed to create logical device!");
}
```

## 3. Device Extension

### 3.1. Instance Extension vs Device Extension

Vulkan의 Extension은 두 가지로 나뉜다.

| 구분 | Instance Extension | Device Extension |
|------|-------------------|------------------|
| **범위** | Vulkan 라이브러리 전체 | 특정 GPU |
| **목적** | 플랫폼 연동, 디버깅 | GPU 기능 확장 |
| **예시** | `VK_KHR_surface`<br>`VK_EXT_debug_utils` | `VK_KHR_swapchain`<br>`VK_KHR_ray_tracing_pipeline` |
| **활성화** | Instance 생성 시 | Device 생성 시 |

### 3.2. Swapchain Extension

화면에 렌더링하려면 **Swapchain**이 필요하다. Swapchain은 Device Extension으로 제공된다.

```cpp
const std::vector<const char*> deviceExtensions = {
    VK_KHR_SWAPCHAIN_EXTENSION_NAME  // "VK_KHR_swapchain"
};

createInfo.enabledExtensionCount = static_cast<uint32_t>(deviceExtensions.size());
createInfo.ppEnabledExtensionNames = deviceExtensions.data();
```

### 3.3. Extension 지원 확인

Physical Device가 Extension을 지원하는지 확인해야 한다.

```cpp
bool checkDeviceExtensionSupport(VkPhysicalDevice device) {
    uint32_t extensionCount;
    vkEnumerateDeviceExtensionProperties(device, nullptr, &extensionCount, nullptr);

    std::vector<VkExtensionProperties> availableExtensions(extensionCount);
    vkEnumerateDeviceExtensionProperties(device, nullptr, &extensionCount,
                                          availableExtensions.data());

    std::set<std::string> requiredExtensions(deviceExtensions.begin(),
                                              deviceExtensions.end());

    for (const auto& extension : availableExtensions) {
        requiredExtensions.erase(extension.extensionName);
    }

    return requiredExtensions.empty();
}
```

Physical Device 선택 시 Extension 지원 여부를 확인해야 한다:

```cpp
bool isDeviceSuitable(VkPhysicalDevice device) {
    QueueFamilyIndices indices = findQueueFamilies(device);
    bool extensionsSupported = checkDeviceExtensionSupport(device);

    return indices.isComplete() && extensionsSupported;
}
```

## 4. Structure Chain (고급)

### 4.1. pNext의 역할

Vulkan 구조체는 `pNext` 포인터를 가지고 있다. 이를 통해 **추가 구조체를 연결**할 수 있다.

```cpp
struct VkDeviceCreateInfo {
    VkStructureType             sType;
    const void*                 pNext;  // 확장 구조체 연결
    // ...
};
```

### 4.2. Extension 활성화 vs Feature 활성화

Device 생성 시 두 단계가 필요하다:

1. **Extension 선언 (`ppEnabledExtensionNames`)**: Extension의 이름(문자열)을 전달하여 사용을 선언
2. **Feature 활성화 (`pNext` Structure Chain)**: Extension이 제공하는 구체적인 기능을 켜거나 특정 버전의 코어 기능을 활성화

**예시**:

```cpp
// 1단계: Extension 선언
const std::vector<const char*> deviceExtensions = {
    VK_EXT_EXTENDED_DYNAMIC_STATE_EXTENSION_NAME  // "VK_EXT_extended_dynamic_state"
};

createInfo.enabledExtensionCount = static_cast<uint32_t>(deviceExtensions.size());
createInfo.ppEnabledExtensionNames = deviceExtensions.data();

// 2단계: Feature 활성화 (Structure Chain)
VkPhysicalDeviceExtendedDynamicStateFeaturesEXT dynamicStateFeatures{};
dynamicStateFeatures.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_EXTENDED_DYNAMIC_STATE_FEATURES_EXT;
dynamicStateFeatures.extendedDynamicState = VK_TRUE;  // 실제 기능 활성화

createInfo.pNext = &dynamicStateFeatures;  // 세부 설정 연결
```

**Structure Chain은 활성화한 Extension의 세부 설정이나 특정 버전의 핵심 기능을 켜는 '추가 요청 및 세부 설정서' 역할**을 한다.

### 4.3. Vulkan 1.3 Features

Vulkan 1.3의 새로운 기능은 `VkPhysicalDeviceVulkan13Features` 구조체로 활성화한다.

```cpp
VkPhysicalDeviceVulkan13Features features13{};
features13.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES;
features13.dynamicRendering = VK_TRUE;
features13.synchronization2 = VK_TRUE;

VkDeviceCreateInfo createInfo{};
createInfo.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
createInfo.pNext = &features13;  // Structure Chain 연결
// ...
```

### 4.4. 여러 구조체 연결

여러 Feature 구조체를 연결할 수 있다:

```cpp
VkPhysicalDeviceVulkan13Features features13{};
features13.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES;
features13.dynamicRendering = VK_TRUE;

VkPhysicalDeviceVulkan12Features features12{};
features12.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES;
features12.bufferDeviceAddress = VK_TRUE;
features12.pNext = &features13;  // 다음 구조체 연결

VkDeviceCreateInfo createInfo{};
createInfo.pNext = &features12;  // Chain의 시작점
```

체인 구조:

```text
VkDeviceCreateInfo
    ↓ pNext
VkPhysicalDeviceVulkan12Features
    ↓ pNext
VkPhysicalDeviceVulkan13Features
    ↓ pNext
nullptr
```

## 5. Queue 획득

Logical Device를 생성한 후 Queue Handle을 가져와야 한다.

### 5.1. vkGetDeviceQueue

```cpp
VkQueue graphicsQueue;
vkGetDeviceQueue(device, indices.graphicsFamily.value(), 0, &graphicsQueue);
```

**파라미터**:
- `device`: Logical Device
- `queueFamilyIndex`: Queue Family 인덱스
- `queueIndex`: Queue Family 내 Queue 인덱스 (0부터 시작)
- `pQueue`: Queue Handle을 받을 포인터

### 5.2. 여러 Queue 사용

Graphics와 Present Queue가 다를 수 있다:

```cpp
VkQueue graphicsQueue;
VkQueue presentQueue;

vkGetDeviceQueue(device, indices.graphicsFamily.value(), 0, &graphicsQueue);
vkGetDeviceQueue(device, indices.presentFamily.value(), 0, &presentQueue);
```

같은 Queue Family라면 같은 Queue Handle을 받게 된다.

### 5.3. Queue Family가 다른 경우

```cpp
std::vector<VkDeviceQueueCreateInfo> queueCreateInfos;
std::set<uint32_t> uniqueQueueFamilies = {
    indices.graphicsFamily.value(),
    indices.presentFamily.value()
};

float queuePriority = 1.0f;
for (uint32_t queueFamily : uniqueQueueFamilies) {
    VkDeviceQueueCreateInfo queueCreateInfo{};
    queueCreateInfo.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queueCreateInfo.queueFamilyIndex = queueFamily;
    queueCreateInfo.queueCount = 1;
    queueCreateInfo.pQueuePriorities = &queuePriority;
    queueCreateInfos.push_back(queueCreateInfo);
}

createInfo.queueCreateInfoCount = static_cast<uint32_t>(queueCreateInfos.size());
createInfo.pQueueCreateInfos = queueCreateInfos.data();
```

중복을 제거하고 각 Queue Family마다 `VkDeviceQueueCreateInfo`를 생성한다.

## 6. 완전한 코드 예시

### 6.1. Logical Device 생성 전체 코드

```cpp
void createLogicalDevice() {
    QueueFamilyIndices indices = findQueueFamilies(physicalDevice);

    // 1. Queue Create Infos
    std::vector<VkDeviceQueueCreateInfo> queueCreateInfos;
    std::set<uint32_t> uniqueQueueFamilies = {
        indices.graphicsFamily.value(),
        indices.presentFamily.value()
    };

    float queuePriority = 1.0f;
    for (uint32_t queueFamily : uniqueQueueFamilies) {
        VkDeviceQueueCreateInfo queueCreateInfo{};
        queueCreateInfo.sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
        queueCreateInfo.queueFamilyIndex = queueFamily;
        queueCreateInfo.queueCount = 1;
        queueCreateInfo.pQueuePriorities = &queuePriority;
        queueCreateInfos.push_back(queueCreateInfo);
    }

    // 2. Device Features
    VkPhysicalDeviceFeatures deviceFeatures{};
    deviceFeatures.samplerAnisotropy = VK_TRUE;

    // 3. Device Create Info
    VkDeviceCreateInfo createInfo{};
    createInfo.sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    createInfo.queueCreateInfoCount = static_cast<uint32_t>(queueCreateInfos.size());
    createInfo.pQueueCreateInfos = queueCreateInfos.data();
    createInfo.pEnabledFeatures = &deviceFeatures;

    // Device Extensions
    createInfo.enabledExtensionCount = static_cast<uint32_t>(deviceExtensions.size());
    createInfo.ppEnabledExtensionNames = deviceExtensions.data();

    // Validation Layers (backward compatibility)
    if (enableValidationLayers) {
        createInfo.enabledLayerCount = static_cast<uint32_t>(validationLayers.size());
        createInfo.ppEnabledLayerNames = validationLayers.data();
    } else {
        createInfo.enabledLayerCount = 0;
    }

    // 4. Create Device
    if (vkCreateDevice(physicalDevice, &createInfo, nullptr, &device) != VK_SUCCESS) {
        throw std::runtime_error("Failed to create logical device!");
    }

    // 5. Get Queue Handles
    vkGetDeviceQueue(device, indices.graphicsFamily.value(), 0, &graphicsQueue);
    vkGetDeviceQueue(device, indices.presentFamily.value(), 0, &presentQueue);
}
```

### 6.2. 정리 순서

Vulkan 객체는 생성의 역순으로 정리해야 한다.

```cpp
void cleanup() {
    vkDestroyDevice(device, nullptr);          // Logical Device 파괴
    // Physical Device는 파괴하지 않음 (Instance가 관리)
    vkDestroyInstance(instance, nullptr);      // Instance 파괴
}
```

**주의**:
- Queue는 Device와 함께 자동으로 파괴되므로 별도로 정리하지 않는다
- Physical Device는 Instance가 관리하므로 직접 파괴하지 않는다

## 7. 자주 발생하는 문제

### 7.1. Extension 미지원

**증상**: `vkCreateDevice`가 `VK_ERROR_EXTENSION_NOT_PRESENT` 반환

**원인**: Physical Device가 요청한 Extension을 지원하지 않음

**해결**:
```cpp
// Physical Device 선택 시 Extension 지원 확인
if (!checkDeviceExtensionSupport(device)) {
    return false;
}
```

### 7.2. Feature 미지원

**증상**: Device 생성은 성공하지만 특정 기능 사용 시 Validation Layer 경고

**원인**: 활성화하지 않은 Feature를 사용

**해결**:
```cpp
// 사용할 Feature를 명시적으로 활성화
VkPhysicalDeviceFeatures supportedFeatures;
vkGetPhysicalDeviceFeatures(physicalDevice, &supportedFeatures);

VkPhysicalDeviceFeatures deviceFeatures{};
if (supportedFeatures.samplerAnisotropy) {
    deviceFeatures.samplerAnisotropy = VK_TRUE;
}
```

### 7.3. Queue Priority 미지정

**증상**: `VK_ERROR_VALIDATION_FAILED_EXT` 또는 크래시

**원인**: `pQueuePriorities`가 nullptr이거나 유효하지 않은 메모리

**해결**:
```cpp
float queuePriority = 1.0f;
queueCreateInfo.pQueuePriorities = &queuePriority;  // 반드시 설정
```

### 7.4. Device 생성 전 Physical Device 미선택

**증상**: `physicalDevice`가 `VK_NULL_HANDLE`

**원인**: `pickPhysicalDevice()`를 호출하지 않음

**해결**:
```cpp
void initVulkan() {
    createInstance();
    pickPhysicalDevice();     // 반드시 Device 생성 전에 호출
    createLogicalDevice();
}
```

## 8. 핵심 개념 정리

### 8.1. Logical Device

- Physical Device에 대한 소프트웨어 인터페이스
- 모든 Vulkan 명령은 Logical Device를 통해 실행
- 여러 개의 Logical Device를 생성할 수 있음 (멀티 GPU)

### 8.2. Device Extension

- GPU별로 제공되는 확장 기능
- Instance Extension과 별도로 관리
- Swapchain 같은 핵심 기능도 Extension으로 제공

### 8.3. Structure Chain

- `pNext` 포인터를 통해 구조체를 연결
- Vulkan 1.1, 1.2, 1.3 기능 활성화 시 사용
- Extension별 Feature 구조체 연결 가능

### 8.4. Queue 획득

- Logical Device 생성 시 Queue Family 지정
- `vkGetDeviceQueue`로 Queue Handle 획득
- Queue는 Device와 함께 자동 파괴

## 9. 다음 단계

이제 Vulkan 초기화의 핵심 단계를 완료했다:

1. Instance 생성
2. Physical Device 선택
3. Logical Device 생성
4. Queue 획득

다음 편에서는 **Surface**와 **Swapchain**을 생성하여 화면에 렌더링할 준비를 한다.
