+++
date = '2025-09-18T19:22:11+09:00'
draft = false
title = '[Vulkan] EP08. Surface와 Swapchain'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Instance", "Physical Device", "Extension", "Validation Layer"]
categories = ["그래픽스 프로그래밍"]
+++

## 시작하며

[EP07]에서 Logical Device를 생성하고 Queue를 획득했다. 이제 GPU에 명령을 보낼 준비가 되었다. 하지만 렌더링 결과를 화면에 표시하려면 두 가지가 더 필요하다.

**Surface**는 Vulkan과 윈도우 시스템을 연결하는 다리다. **Swapchain**은 화면에 표시될 이미지들을 관리하는 큐다.

이 글에서는 Surface와 Swapchain을 생성하여 화면 출력을 준비하는 과정을 정리한다.

---

## 1. Surface - 화면 연결

### 1.1. Surface란?

지금까지 Instance, Physical Device, Logical Device, Queue를 생성했다. 하지만 이것만으로는 화면에 아무것도 표시할 수 없다.

**Surface는 Vulkan과 운영체제의 윈도우 시스템을 연결하는 다리 역할**을 한다.

**Physical Device (GPU)**
- 렌더링 수행

↓

**Surface (VkSurfaceKHR)**
- 플랫폼 윈도우 시스템과 연결

↓

**화면 (모니터)**
- 최종 이미지 표시

### 1.2. WSI (Window System Integration)

Vulkan은 플랫폼 독립적인 API다. 따라서 각 플랫폼의 윈도우 시스템과 연동하려면 **WSI 확장**이 필요하다.

주요 플랫폼별 확장:
- Windows: `VK_KHR_win32_surface`
- Linux (X11): `VK_KHR_xlib_surface`
- Linux (Wayland): `VK_KHR_wayland_surface`
- macOS: `VK_EXT_metal_surface`

모든 플랫폼에서 공통으로 사용하는 기본 확장:
- `VK_KHR_surface`

### 1.3. Surface 생성 (GLFW 사용)

GLFW는 플랫폼별 차이를 추상화하여 간단하게 Surface를 생성할 수 있게 해준다.

```cpp
VkSurfaceKHR surface;

void createSurface() {
    if (glfwCreateWindowSurface(instance, window, nullptr, &surface) != VK_SUCCESS) {
        throw std::runtime_error("failed to create window surface!");
    }
}
```

GLFW가 내부적으로 처리하는 과정:
1. 현재 플랫폼 감지 (Windows, Linux, macOS)
2. 네이티브 윈도우 핸들 획득
3. 플랫폼별 Surface 생성 함수 호출
   - Windows: `vkCreateWin32SurfaceKHR`
   - Linux X11: `vkCreateXlibSurfaceKHR`
   - macOS: `vkCreateMetalSurfaceKHR`
4. `VkSurfaceKHR` 객체 반환

**중요**: Surface는 Instance 생성 직후에 만들어야 한다. Physical Device 선택 시 Surface 지원 여부를 확인해야 하기 때문이다.

### 1.4. Present Queue 찾기

Surface가 생성되면, 이 Surface에 이미지를 표시할 수 있는 Queue를 찾아야 한다.

#### Graphics Queue vs Present Queue

- **Graphics Queue**: 렌더링 명령 실행
- **Present Queue**: 렌더링 결과를 Surface에 표시

대부분의 GPU는 두 기능을 하나의 Queue에서 지원하지만, 일부는 분리되어 있을 수 있다.

```cpp
struct QueueFamilyIndices {
    std::optional<uint32_t> graphicsFamily;
    std::optional<uint32_t> presentFamily;

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
        // Graphics 지원 확인
        if (queueFamily.queueFlags & VK_QUEUE_GRAPHICS_BIT) {
            indices.graphicsFamily = i;
        }

        // Present 지원 확인
        VkBool32 presentSupport = false;
        vkGetPhysicalDeviceSurfaceSupportKHR(device, i, surface, &presentSupport);
        if (presentSupport) {
            indices.presentFamily = i;
        }

        if (indices.isComplete()) {
            break;
        }

        i++;
    }

    return indices;
}
```

**핵심**: `vkGetPhysicalDeviceSurfaceSupportKHR` 함수로 Queue Family가 특정 Surface를 지원하는지 확인한다.

### 1.5. Logical Device 생성 시 Present Queue 추가

Graphics Queue와 Present Queue가 다를 수 있으므로 두 Queue를 모두 생성해야 한다.

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
```

Queue Handle 획득:

```cpp
VkQueue graphicsQueue;
VkQueue presentQueue;

vkGetDeviceQueue(device, indices.graphicsFamily.value(), 0, &graphicsQueue);
vkGetDeviceQueue(device, indices.presentFamily.value(), 0, &presentQueue);
```

같은 Queue Family면 같은 Handle을 받게 된다.

## 2. Swapchain - 이미지 큐

### 2.1. Swapchain이란?

**Swapchain은 화면에 표시될 이미지들의 큐(Queue) 또는 배열**이다.

렌더링 과정:

```
1. Swapchain에서 이미지 획득 (vkAcquireNextImageKHR)
    ↓
2. 해당 이미지에 렌더링
    ↓
3. 완성된 이미지를 Swapchain에 반환 (vkQueuePresentKHR)
    ↓
4. Surface를 통해 화면에 표시
```

**목적**: 사용자가 렌더링 중간 과정을 보지 않고 완성된 프레임만 보도록 한다.

### 2.2. Swapchain 지원 확인

모든 GPU가 Swapchain을 지원하는 것은 아니다. `VK_KHR_swapchain` Device Extension이 필요하다.

```cpp
const std::vector<const char*> deviceExtensions = {
    VK_KHR_SWAPCHAIN_EXTENSION_NAME
};

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

### 2.3. Swapchain 세부 정보 쿼리

Swapchain 생성 전에 세 가지 속성을 확인해야 한다:

#### 1. Surface Capabilities (기본 속성)

```cpp
VkSurfaceCapabilitiesKHR capabilities;
vkGetPhysicalDeviceSurfaceCapabilitiesKHR(device, surface, &capabilities);
```

포함 정보:
- `minImageCount`, `maxImageCount`: 최소/최대 이미지 개수
- `minImageExtent`, `maxImageExtent`: 최소/최대 이미지 해상도
- `currentExtent`: 현재 Surface 해상도
- `supportedTransforms`: 지원되는 변환
- `supportedCompositeAlpha`: 알파 블렌딩 모드

#### 2. Surface Formats (픽셀 형식)

```cpp
uint32_t formatCount;
vkGetPhysicalDeviceSurfaceFormatsKHR(device, surface, &formatCount, nullptr);

std::vector<VkSurfaceFormatKHR> formats(formatCount);
vkGetPhysicalDeviceSurfaceFormatsKHR(device, surface, &formatCount, formats.data());
```

`VkSurfaceFormatKHR` 구조체:
- `format`: 픽셀 형식 (예: `VK_FORMAT_B8G8R8A8_SRGB`)
- `colorSpace`: 색 공간 (예: `VK_COLOR_SPACE_SRGB_NONLINEAR_KHR`)

#### 3. Present Modes (표시 모드)

```cpp
uint32_t presentModeCount;
vkGetPhysicalDeviceSurfacePresentModesKHR(device, surface, &presentModeCount, nullptr);

std::vector<VkPresentModeKHR> presentModes(presentModeCount);
vkGetPhysicalDeviceSurfacePresentModesKHR(device, surface, &presentModeCount,
                                           presentModes.data());
```

### 2.4. Swapchain 설정 선택

#### 1. Surface Format 선택

```cpp
VkSurfaceFormatKHR chooseSwapSurfaceFormat(
    const std::vector<VkSurfaceFormatKHR>& availableFormats) {

    // SRGB 형식 우선 선택
    for (const auto& availableFormat : availableFormats) {
        if (availableFormat.format == VK_FORMAT_B8G8R8A8_SRGB &&
            availableFormat.colorSpace == VK_COLOR_SPACE_SRGB_NONLINEAR_KHR) {
            return availableFormat;
        }
    }

    // 없으면 첫 번째 형식 사용
    return availableFormats[0];
}
```

**권장**: `VK_FORMAT_B8G8R8A8_SRGB` + `VK_COLOR_SPACE_SRGB_NONLINEAR_KHR`

#### 2. Present Mode 선택

Present Mode는 이미지를 화면에 표시하는 방식을 결정한다.

| Present Mode | 설명 | 특징 |
|-------------|------|------|
| `VK_PRESENT_MODE_IMMEDIATE_KHR` | 즉시 전송 | 테어링 발생 가능, 낮은 지연 |
| `VK_PRESENT_MODE_FIFO_KHR` | 수직 동기화 (V-Sync) | 테어링 없음, 항상 지원됨 |
| `VK_PRESENT_MODE_FIFO_RELAXED_KHR` | 완화된 FIFO | 늦은 이미지는 즉시 전송 |
| `VK_PRESENT_MODE_MAILBOX_KHR` | 트리플 버퍼링 | 테어링 없고 낮은 지연 |

```cpp
VkPresentModeKHR chooseSwapPresentMode(
    const std::vector<VkPresentModeKHR>& availablePresentModes) {

    // Mailbox 모드 우선 (트리플 버퍼링)
    for (const auto& availablePresentMode : availablePresentModes) {
        if (availablePresentMode == VK_PRESENT_MODE_MAILBOX_KHR) {
            return availablePresentMode;
        }
    }

    // 없으면 FIFO (항상 지원됨)
    return VK_PRESENT_MODE_FIFO_KHR;
}
```

**Present Mode 비교**:

- **IMMEDIATE**: 큐 대기 없이 즉시 표시 → 테어링 가능
- **FIFO (이중 버퍼링)**: V-Sync에 맞춰 표시 → 테어링 없음, 프레임 제한
- **MAILBOX (삼중 버퍼링)**: 큐가 차면 최신 이미지로 교체 → 테어링 없고 지연 낮음

#### 3. Swap Extent (해상도) 선택

```cpp
VkExtent2D chooseSwapExtent(const VkSurfaceCapabilitiesKHR& capabilities) {
    if (capabilities.currentExtent.width != std::numeric_limits<uint32_t>::max()) {
        return capabilities.currentExtent;
    } else {
        int width, height;
        glfwGetFramebufferSize(window, &width, &height);

        VkExtent2D actualExtent = {
            static_cast<uint32_t>(width),
            static_cast<uint32_t>(height)
        };

        actualExtent.width = std::clamp(actualExtent.width,
            capabilities.minImageExtent.width,
            capabilities.maxImageExtent.width);
        actualExtent.height = std::clamp(actualExtent.height,
            capabilities.minImageExtent.height,
            capabilities.maxImageExtent.height);

        return actualExtent;
    }
}
```

**참고**: 고해상도 디스플레이에서는 창 크기와 픽셀 크기가 다를 수 있다.

### 2.5. Swapchain 생성

```cpp
void createSwapChain() {
    SwapChainSupportDetails swapChainSupport = querySwapChainSupport(physicalDevice);

    VkSurfaceFormatKHR surfaceFormat = chooseSwapSurfaceFormat(swapChainSupport.formats);
    VkPresentModeKHR presentMode = chooseSwapPresentMode(swapChainSupport.presentModes);
    VkExtent2D extent = chooseSwapExtent(swapChainSupport.capabilities);

    // 이미지 개수 결정
    uint32_t imageCount = swapChainSupport.capabilities.minImageCount + 1;
    if (swapChainSupport.capabilities.maxImageCount > 0 &&
        imageCount > swapChainSupport.capabilities.maxImageCount) {
        imageCount = swapChainSupport.capabilities.maxImageCount;
    }

    VkSwapchainCreateInfoKHR createInfo{};
    createInfo.sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR;
    createInfo.surface = surface;
    createInfo.minImageCount = imageCount;
    createInfo.imageFormat = surfaceFormat.format;
    createInfo.imageColorSpace = surfaceFormat.colorSpace;
    createInfo.imageExtent = extent;
    createInfo.imageArrayLayers = 1;  // VR이 아니면 항상 1
    createInfo.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;

    QueueFamilyIndices indices = findQueueFamilies(physicalDevice);
    uint32_t queueFamilyIndices[] = {
        indices.graphicsFamily.value(),
        indices.presentFamily.value()
    };

    if (indices.graphicsFamily != indices.presentFamily) {
        // Queue가 다르면 Concurrent 모드
        createInfo.imageSharingMode = VK_SHARING_MODE_CONCURRENT;
        createInfo.queueFamilyIndexCount = 2;
        createInfo.pQueueFamilyIndices = queueFamilyIndices;
    } else {
        // Queue가 같으면 Exclusive 모드 (더 빠름)
        createInfo.imageSharingMode = VK_SHARING_MODE_EXCLUSIVE;
        createInfo.queueFamilyIndexCount = 0;
        createInfo.pQueueFamilyIndices = nullptr;
    }

    createInfo.preTransform = swapChainSupport.capabilities.currentTransform;
    createInfo.compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
    createInfo.presentMode = presentMode;
    createInfo.clipped = VK_TRUE;
    createInfo.oldSwapchain = VK_NULL_HANDLE;

    if (vkCreateSwapchainKHR(device, &createInfo, nullptr, &swapChain) != VK_SUCCESS) {
        throw std::runtime_error("failed to create swap chain!");
    }
}
```

**주요 파라미터 설명**:

- `minImageCount`: Swapchain 이미지 개수 (최소값 + 1 권장)
- `imageArrayLayers`: VR/3D가 아니면 1
- `imageUsage`: 렌더링 대상이므로 `COLOR_ATTACHMENT`
- `imageSharingMode`:
  - `EXCLUSIVE`: 단일 Queue, 성능 최고
  - `CONCURRENT`: 여러 Queue, 소유권 이전 불필요
- `preTransform`: 이미지 회전/반전 (보통 변환 없음)
- `compositeAlpha`: 알파 블렌딩 (보통 불투명)
- `clipped`: 가려진 픽셀 무시 (성능 향상)
- `oldSwapchain`: 재생성 시 이전 Swapchain 참조

### 2.6. Swapchain 이미지 획득

```cpp
std::vector<VkImage> swapChainImages;
VkFormat swapChainImageFormat;
VkExtent2D swapChainExtent;

void retrieveSwapChainImages() {
    uint32_t imageCount;
    vkGetSwapchainImagesKHR(device, swapChain, &imageCount, nullptr);
    swapChainImages.resize(imageCount);
    vkGetSwapchainImagesKHR(device, swapChain, &imageCount, swapChainImages.data());

    swapChainImageFormat = surfaceFormat.format;
    swapChainExtent = extent;
}
```

**중요**: `VkImage`는 Swapchain이 소유하므로 직접 파괴하지 않는다.

## 3. 전체 초기화 흐름

```cpp
void initVulkan() {
    createInstance();
    createSurface();         // Surface 먼저 생성
    pickPhysicalDevice();    // Surface 지원 확인
    createLogicalDevice();   // Present Queue 포함
    createSwapChain();       // Swapchain 생성
}
```

**초기화 순서 중요**: Surface는 Physical Device 선택 전에 생성해야 한다.

## 4. 정리 순서

```cpp
void cleanup() {
    vkDestroySwapchainKHR(device, swapChain, nullptr);
    vkDestroyDevice(device, nullptr);
    vkDestroySurfaceKHR(instance, surface, nullptr);
    vkDestroyInstance(instance, nullptr);
}
```

**주의**:
- Swapchain → Device → Surface → Instance 순서
- Swapchain Images는 직접 파괴하지 않음

## 5. 자주 발생하는 문제

### 5.1. "No suitable present queue found"

**원인**: Surface를 지원하는 Queue Family가 없음

**해결**:
```cpp
// Physical Device 선택 시 Present 지원 확인
VkBool32 presentSupport = false;
vkGetPhysicalDeviceSurfaceSupportKHR(device, i, surface, &presentSupport);
if (!presentSupport) {
    // 이 GPU는 사용 불가
    return false;
}
```

### 5.2. Swapchain 생성 실패

**원인**: Surface 속성 확인 누락

**해결**:
```cpp
// 반드시 세 가지 모두 확인
SwapChainSupportDetails details;
vkGetPhysicalDeviceSurfaceCapabilitiesKHR(device, surface, &details.capabilities);
// formats 쿼리
// presentModes 쿼리

if (details.formats.empty() || details.presentModes.empty()) {
    return false;  // Swapchain 지원 안 함
}
```

### 5.3. 화면에 아무것도 안 보임

**원인**: Present Queue에 제출하지 않음

**해결**:
```cpp
VkPresentInfoKHR presentInfo{};
presentInfo.sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR;
presentInfo.swapchainCount = 1;
presentInfo.pSwapchains = &swapChain;
presentInfo.pImageIndices = &imageIndex;

vkQueuePresentKHR(presentQueue, &presentInfo);  // Present Queue 사용!
```

### 5.4. macOS에서 Swapchain 생성 실패

**원인**: MoltenVK는 `VK_KHR_portability_subset` 필요

**해결**:
```cpp
#ifdef __APPLE__
const std::vector<const char*> deviceExtensions = {
    VK_KHR_SWAPCHAIN_EXTENSION_NAME,
    "VK_KHR_portability_subset"  // macOS 필수
};
#endif
```

## 6. 핵심 개념 정리

### 6.1. Surface

- Vulkan과 플랫폼 윈도우 시스템의 연결 다리
- Instance 생성 직후, Physical Device 선택 전에 생성
- WSI 확장을 통해 플랫폼별 구현

### 6.2. Present Queue

- 렌더링 결과를 Surface에 표시하는 Queue
- Graphics Queue와 같을 수도, 다를 수도 있음
- `vkGetPhysicalDeviceSurfaceSupportKHR`로 지원 확인

### 6.3. Swapchain

- 화면에 표시될 이미지들의 큐/배열
- 렌더링 중간 과정을 숨기고 완성된 프레임만 표시
- Present Mode로 버퍼링 방식 결정

### 6.4. Present Mode

- **FIFO**: V-Sync, 이중 버퍼링
- **MAILBOX**: 트리플 버퍼링, 낮은 지연
- **IMMEDIATE**: 즉시 표시, 테어링 가능

## 7. 다음 단계

화면에 그릴 준비가 완료되었다:

1. Instance 생성
2. Physical Device 선택
3. Logical Device 생성
4. Queue 획득
5. Surface 생성
6. Swapchain 생성

다음 편에서는 **Render Pass**를 생성하여 실제 렌더링 파이프라인을 구성한다.
