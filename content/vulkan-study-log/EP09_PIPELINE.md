+++
date = '2025-09-20T12:41:23+09:00'
draft = false
title = '[Vulkan] EP09. Graphics Pipeline'
series = ["Vulkan 학습"]
tags = ["Vulkan", "Graphics Pipeline", "Shader", "Render Pass"]
categories = ["그래픽스 프로그래밍"]
summary = "Graphics Pipeline을 구성합니다. Shader Module, Render Pass, Fixed Function 단계를 설정하고 Pipeline을 생성합니다."
+++

## 시작하며

[EP08]에서 Swapchain과 Image View를 생성했다. 이제 실제로 화면에 무언가를 그리기 위한 핵심 구성 요소인 **Graphics Pipeline**을 만들 차례다.

Graphics Pipeline은 3D 지오메트리와 텍스처 데이터를 최종 픽셀로 변환하는 일련의 과정이다. Vulkan은 이 파이프라인의 거의 모든 단계를 명시적으로 구성해야 한다.

이 글에서는 Graphics Pipeline의 개념, Shader Module, Render Pass, 그리고 고정 함수 단계를 다룬다.

---

## 1. Graphics Pipeline 개요

### 1.1. Pipeline이란?

Graphics Pipeline은 정점 데이터가 화면의 픽셀로 변환되는 과정을 정의한다.

파이프라인의 주요 단계:

1. **Input Assembler**: 정점 데이터 수집
2. **Vertex Shader**: 정점 변환 (3D → 2D)
3. **Rasterization**: 삼각형을 픽셀로 변환
4. **Fragment Shader**: 픽셀 색상 계산
5. **Color Blending**: 최종 색상 결정

### 1.2. Vulkan Pipeline의 특징

**명시적 제어**:
- 파이프라인의 각 단계를 직접 구성
- 기본값이 거의 없음
- 설정해야 할 항목이 많지만 최적화 가능

**불변성 (Immutable)**:
- 파이프라인 생성 후 대부분의 상태 변경 불가
- 다른 설정이 필요하면 새 파이프라인 생성
- 드라이버 최적화에 유리

**프로그래밍 가능 vs 고정 함수**:
- **프로그래밍 가능**: Shader로 제어 (Vertex Shader, Fragment Shader)
- **고정 함수**: 설정으로 제어 (Rasterizer, Blending 등)

---

## 2. Shader Module

### 2.1. Shader란?

Shader는 GPU에서 실행되는 작은 프로그램이다. 정점이나 프래그먼트 데이터를 처리한다.

**주요 Shader 종류**:
- **Vertex Shader**: 정점 위치 변환, 속성 계산
- **Fragment Shader**: 픽셀 색상 결정

### 2.2. GLSL과 SPIR-V

**GLSL (OpenGL Shading Language)**:
- C/C++ 유사 문법
- 사람이 읽고 쓰기 쉬운 언어

**SPIR-V**:
- GPU 벤더 독립적인 중간 표현
- Vulkan은 SPIR-V만 직접 사용
- GLSL → SPIR-V 컴파일 필요

**컴파일**:
```bash
# glslangValidator 사용 (Vulkan SDK 포함)
glslangValidator -V shader.vert -o vert.spv
glslangValidator -V shader.frag -o frag.spv
```

### 2.3. Shader 코드 예제

**Vertex Shader (shader.vert)**:
```glsl
#version 450

layout(location = 0) out vec3 fragColor;

vec2 positions[3] = vec2[](
    vec2(0.0, -0.5),
    vec2(0.5, 0.5),
    vec2(-0.5, 0.5)
);

vec3 colors[3] = vec3[](
    vec3(1.0, 0.0, 0.0),
    vec3(0.0, 1.0, 0.0),
    vec3(0.0, 0.0, 1.0)
);

void main() {
    gl_Position = vec4(positions[gl_VertexIndex], 0.0, 1.0);
    fragColor = colors[gl_VertexIndex];
}
```

**Fragment Shader (shader.frag)**:
```glsl
#version 450

layout(location = 0) in vec3 fragColor;
layout(location = 0) out vec4 outColor;

void main() {
    outColor = vec4(fragColor, 1.0);
}
```

### 2.4. Shader Module 생성

SPIR-V 바이트코드를 로드하여 `VkShaderModule` 생성:

```cpp
std::vector<char> readFile(const std::string& filename) {
    std::ifstream file(filename, std::ios::ate | std::ios::binary);

    if (!file.is_open()) {
        throw std::runtime_error("failed to open file!");
    }

    size_t fileSize = (size_t)file.tellg();
    std::vector<char> buffer(fileSize);

    file.seekg(0);
    file.read(buffer.data(), fileSize);
    file.close();

    return buffer;
}

VkShaderModule createShaderModule(const std::vector<char>& code) {
    VkShaderModuleCreateInfo createInfo{};
    createInfo.sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    createInfo.codeSize = code.size();
    createInfo.pCode = reinterpret_cast<const uint32_t*>(code.data());

    VkShaderModule shaderModule;
    if (vkCreateShaderModule(device, &createInfo, nullptr, &shaderModule) != VK_SUCCESS) {
        throw std::runtime_error("failed to create shader module!");
    }

    return shaderModule;
}
```

**사용**:
```cpp
auto vertShaderCode = readFile("shaders/vert.spv");
auto fragShaderCode = readFile("shaders/frag.spv");

VkShaderModule vertShaderModule = createShaderModule(vertShaderCode);
VkShaderModule fragShaderModule = createShaderModule(fragShaderCode);
```

**생명 주기**:
- Shader Module은 Pipeline 생성에만 필요
- Pipeline 생성 후 안전하게 파괴 가능

```cpp
vkDestroyShaderModule(device, vertShaderModule, nullptr);
vkDestroyShaderModule(device, fragShaderModule, nullptr);
```

---

## 3. Render Pass

### 3.1. Render Pass란?

Render Pass는 렌더링 작업에 사용되는 프레임버퍼 어태치먼트의 구조와 동작을 정의한다.

**주요 역할**:
- 어태치먼트 포맷 및 샘플 수 정의
- Load/Store 동작 지정
- 서브패스 구성
- 의존성 관리

### 3.2. Render Pass 구성 요소

**Attachment Description**:
```cpp
VkAttachmentDescription colorAttachment{};
colorAttachment.format = swapChainImageFormat;
colorAttachment.samples = VK_SAMPLE_COUNT_1_BIT;

// Load/Store 동작
colorAttachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;  // 시작 시 클리어
colorAttachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;  // 종료 시 저장

// 스텐실 (사용 안 함)
colorAttachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
colorAttachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;

// 레이아웃
colorAttachment.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
colorAttachment.finalLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
```

**Load/Store 동작**:

| 동작 | 설명 |
|------|------|
| `LOAD` | 기존 데이터 유지 |
| `CLEAR` | 지정된 값으로 초기화 |
| `DONT_CARE` | 기존 데이터 무시 (최적화 가능) |
| `STORE` | 결과 저장 |

**Subpass**:
```cpp
VkAttachmentReference colorAttachmentRef{};
colorAttachmentRef.attachment = 0;  // attachment 배열의 인덱스
colorAttachmentRef.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;

VkSubpassDescription subpass{};
subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
subpass.colorAttachmentCount = 1;
subpass.pColorAttachments = &colorAttachmentRef;
```

**Subpass Dependency**:
```cpp
VkSubpassDependency dependency{};
dependency.srcSubpass = VK_SUBPASS_EXTERNAL;
dependency.dstSubpass = 0;

dependency.srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
dependency.srcAccessMask = 0;

dependency.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
dependency.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
```

### 3.3. Render Pass 생성

```cpp
void createRenderPass() {
    VkAttachmentDescription colorAttachment{};
    colorAttachment.format = swapChainImageFormat;
    colorAttachment.samples = VK_SAMPLE_COUNT_1_BIT;
    colorAttachment.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    colorAttachment.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    colorAttachment.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    colorAttachment.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    colorAttachment.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    colorAttachment.finalLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;

    VkAttachmentReference colorAttachmentRef{};
    colorAttachmentRef.attachment = 0;
    colorAttachmentRef.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;

    VkSubpassDescription subpass{};
    subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    subpass.colorAttachmentCount = 1;
    subpass.pColorAttachments = &colorAttachmentRef;

    VkSubpassDependency dependency{};
    dependency.srcSubpass = VK_SUBPASS_EXTERNAL;
    dependency.dstSubpass = 0;
    dependency.srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dependency.srcAccessMask = 0;
    dependency.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dependency.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;

    VkRenderPassCreateInfo renderPassInfo{};
    renderPassInfo.sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
    renderPassInfo.attachmentCount = 1;
    renderPassInfo.pAttachments = &colorAttachment;
    renderPassInfo.subpassCount = 1;
    renderPassInfo.pSubpasses = &subpass;
    renderPassInfo.dependencyCount = 1;
    renderPassInfo.pDependencies = &dependency;

    if (vkCreateRenderPass(device, &renderPassInfo, nullptr, &renderPass) != VK_SUCCESS) {
        throw std::runtime_error("failed to create render pass!");
    }
}
```

---

## 4. 고정 함수 단계

### 4.1. Vertex Input

정점 데이터 형식 정의 (현재는 하드코딩된 데이터 사용):

```cpp
VkPipelineVertexInputStateCreateInfo vertexInputInfo{};
vertexInputInfo.sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
vertexInputInfo.vertexBindingDescriptionCount = 0;
vertexInputInfo.pVertexBindingDescriptions = nullptr;
vertexInputInfo.vertexAttributeDescriptionCount = 0;
vertexInputInfo.pVertexAttributeDescriptions = nullptr;
```

### 4.2. Input Assembly

정점을 어떤 도형으로 조립할지 정의:

```cpp
VkPipelineInputAssemblyStateCreateInfo inputAssembly{};
inputAssembly.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
inputAssembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
inputAssembly.primitiveRestartEnable = VK_FALSE;
```

**Topology 옵션**:
- `TRIANGLE_LIST`: 3개 정점마다 독립 삼각형
- `TRIANGLE_STRIP`: 정점 공유하는 삼각형 띠
- `LINE_LIST`: 2개 정점마다 독립 선
- `POINT_LIST`: 각 정점이 점

### 4.3. Viewport와 Scissor

렌더링 영역 정의:

```cpp
VkViewport viewport{};
viewport.x = 0.0f;
viewport.y = 0.0f;
viewport.width = (float)swapChainExtent.width;
viewport.height = (float)swapChainExtent.height;
viewport.minDepth = 0.0f;
viewport.maxDepth = 1.0f;

VkRect2D scissor{};
scissor.offset = {0, 0};
scissor.extent = swapChainExtent;

VkPipelineViewportStateCreateInfo viewportState{};
viewportState.sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
viewportState.viewportCount = 1;
viewportState.pViewports = &viewport;
viewportState.scissorCount = 1;
viewportState.pScissors = &scissor;
```

**동적 상태로 설정** (런타임 변경 가능):
```cpp
std::vector<VkDynamicState> dynamicStates = {
    VK_DYNAMIC_STATE_VIEWPORT,
    VK_DYNAMIC_STATE_SCISSOR
};

VkPipelineDynamicStateCreateInfo dynamicState{};
dynamicState.sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO;
dynamicState.dynamicStateCount = static_cast<uint32_t>(dynamicStates.size());
dynamicState.pDynamicStates = dynamicStates.data();
```

### 4.4. Rasterizer

프리미티브를 프래그먼트로 변환:

```cpp
VkPipelineRasterizationStateCreateInfo rasterizer{};
rasterizer.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
rasterizer.depthClampEnable = VK_FALSE;
rasterizer.rasterizerDiscardEnable = VK_FALSE;
rasterizer.polygonMode = VK_POLYGON_MODE_FILL;
rasterizer.lineWidth = 1.0f;
rasterizer.cullMode = VK_CULL_MODE_BACK_BIT;
rasterizer.frontFace = VK_FRONT_FACE_CLOCKWISE;
rasterizer.depthBiasEnable = VK_FALSE;
```

**Polygon Mode**:
- `FILL`: 채우기
- `LINE`: 와이어프레임
- `POINT`: 정점만 표시

### 4.5. Multisampling

안티앨리어싱 설정 (현재는 비활성화):

```cpp
VkPipelineMultisampleStateCreateInfo multisampling{};
multisampling.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
multisampling.sampleShadingEnable = VK_FALSE;
multisampling.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;
```

### 4.6. Color Blending

색상 혼합 방식 정의:

```cpp
VkPipelineColorBlendAttachmentState colorBlendAttachment{};
colorBlendAttachment.colorWriteMask = VK_COLOR_COMPONENT_R_BIT |
                                       VK_COLOR_COMPONENT_G_BIT |
                                       VK_COLOR_COMPONENT_B_BIT |
                                       VK_COLOR_COMPONENT_A_BIT;
colorBlendAttachment.blendEnable = VK_FALSE;

VkPipelineColorBlendStateCreateInfo colorBlending{};
colorBlending.sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
colorBlending.logicOpEnable = VK_FALSE;
colorBlending.attachmentCount = 1;
colorBlending.pAttachments = &colorBlendAttachment;
```

**알파 블렌딩 예제**:
```cpp
colorBlendAttachment.blendEnable = VK_TRUE;
colorBlendAttachment.srcColorBlendFactor = VK_BLEND_FACTOR_SRC_ALPHA;
colorBlendAttachment.dstColorBlendFactor = VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
colorBlendAttachment.colorBlendOp = VK_BLEND_OP_ADD;
colorBlendAttachment.srcAlphaBlendFactor = VK_BLEND_FACTOR_ONE;
colorBlendAttachment.dstAlphaBlendFactor = VK_BLEND_FACTOR_ZERO;
colorBlendAttachment.alphaBlendOp = VK_BLEND_OP_ADD;
```

### 4.7. Pipeline Layout

Shader가 사용할 리소스 정의 (현재는 빈 레이아웃):

```cpp
VkPipelineLayoutCreateInfo pipelineLayoutInfo{};
pipelineLayoutInfo.sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
pipelineLayoutInfo.setLayoutCount = 0;
pipelineLayoutInfo.pushConstantRangeCount = 0;

if (vkCreatePipelineLayout(device, &pipelineLayoutInfo, nullptr, &pipelineLayout) != VK_SUCCESS) {
    throw std::runtime_error("failed to create pipeline layout!");
}
```

---

## 5. Graphics Pipeline 생성

모든 구성 요소를 조합하여 Pipeline 생성:

```cpp
void createGraphicsPipeline() {
    // Shader Module 생성
    auto vertShaderCode = readFile("shaders/vert.spv");
    auto fragShaderCode = readFile("shaders/frag.spv");

    VkShaderModule vertShaderModule = createShaderModule(vertShaderCode);
    VkShaderModule fragShaderModule = createShaderModule(fragShaderCode);

    // Shader Stage
    VkPipelineShaderStageCreateInfo vertShaderStageInfo{};
    vertShaderStageInfo.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    vertShaderStageInfo.stage = VK_SHADER_STAGE_VERTEX_BIT;
    vertShaderStageInfo.module = vertShaderModule;
    vertShaderStageInfo.pName = "main";

    VkPipelineShaderStageCreateInfo fragShaderStageInfo{};
    fragShaderStageInfo.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
    fragShaderStageInfo.stage = VK_SHADER_STAGE_FRAGMENT_BIT;
    fragShaderStageInfo.module = fragShaderModule;
    fragShaderStageInfo.pName = "main";

    VkPipelineShaderStageCreateInfo shaderStages[] = {vertShaderStageInfo, fragShaderStageInfo};

    // 고정 함수 설정 (위의 코드들)

    // Pipeline 생성
    VkGraphicsPipelineCreateInfo pipelineInfo{};
    pipelineInfo.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
    pipelineInfo.stageCount = 2;
    pipelineInfo.pStages = shaderStages;
    pipelineInfo.pVertexInputState = &vertexInputInfo;
    pipelineInfo.pInputAssemblyState = &inputAssembly;
    pipelineInfo.pViewportState = &viewportState;
    pipelineInfo.pRasterizationState = &rasterizer;
    pipelineInfo.pMultisampleState = &multisampling;
    pipelineInfo.pColorBlendState = &colorBlending;
    pipelineInfo.pDynamicState = &dynamicState;
    pipelineInfo.layout = pipelineLayout;
    pipelineInfo.renderPass = renderPass;
    pipelineInfo.subpass = 0;

    if (vkCreateGraphicsPipelines(device, VK_NULL_HANDLE, 1, &pipelineInfo,
                                   nullptr, &graphicsPipeline) != VK_SUCCESS) {
        throw std::runtime_error("failed to create graphics pipeline!");
    }

    // Shader Module 정리
    vkDestroyShaderModule(device, fragShaderModule, nullptr);
    vkDestroyShaderModule(device, vertShaderModule, nullptr);
}
```

---

## 6. Graphics Pipeline 생성

지금까지 설명한 모든 구성 요소(Shader Module, Render Pass, Fixed Function 단계들, Pipeline Layout)를 하나로 모아 `VkPipeline` 객체를 생성한다.

### 6.1. VkGraphicsPipelineCreateInfo 구조체

모든 정보를 `VkGraphicsPipelineCreateInfo` 구조체에 모은다:

```cpp
VkGraphicsPipelineCreateInfo pipelineInfo{};
pipelineInfo.sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;

// 셰이더 단계
pipelineInfo.stageCount = 2;
pipelineInfo.pStages = shaderStages;  // Vertex + Fragment

// 고정 함수 단계
pipelineInfo.pVertexInputState = &vertexInputInfo;
pipelineInfo.pInputAssemblyState = &inputAssembly;
pipelineInfo.pViewportState = &viewportState;
pipelineInfo.pRasterizationState = &rasterizer;
pipelineInfo.pMultisampleState = &multisampling;
pipelineInfo.pDepthStencilState = nullptr;  // 현재 미사용
pipelineInfo.pColorBlendState = &colorBlending;
pipelineInfo.pDynamicState = &dynamicState;

// Pipeline Layout과 Render Pass
pipelineInfo.layout = pipelineLayout;
pipelineInfo.renderPass = renderPass;
pipelineInfo.subpass = 0;  // 사용할 서브패스 인덱스

// 파이프라인 파생 (선택사항)
pipelineInfo.basePipelineHandle = VK_NULL_HANDLE;
pipelineInfo.basePipelineIndex = -1;
```

**주요 필드:**
- `pStages`: 프로그래밍 가능한 셰이더 단계 배열
- `pVertexInputState` ~ `pDynamicState`: 고정 함수 단계 설정
- `layout`: Uniform 및 Push Constants 레이아웃
- `renderPass`, `subpass`: 어떤 Render Pass의 어느 서브패스에서 사용될지 지정

### 6.2. vkCreateGraphicsPipelines 호출

```cpp
VkPipeline graphicsPipeline;

if (vkCreateGraphicsPipelines(device, VK_NULL_HANDLE, 1, &pipelineInfo,
                               nullptr, &graphicsPipeline) != VK_SUCCESS) {
    throw std::runtime_error("failed to create graphics pipeline!");
}
```

**파라미터:**
- **`device`**: Logical Device
- **`pipelineCache`**: 파이프라인 캐시 객체 (`VK_NULL_HANDLE`로 비활성화 가능)
  - 실제 애플리케이션에서는 `VkPipelineCache`를 사용하여 생성 속도 향상
  - 캐시를 파일로 저장하여 재실행 시 재사용 가능
- **`createInfoCount`**: 생성할 파이프라인 개수 (여러 개 동시 생성 가능)
- **`pCreateInfos`**: `VkGraphicsPipelineCreateInfo` 배열
- **`pAllocator`**: 커스텀 메모리 할당자
- **`pPipelines`**: 생성된 파이프라인 핸들 반환

### 6.3. 파이프라인 소멸

```cpp
void cleanup() {
    vkDestroyPipeline(device, graphicsPipeline, nullptr);
    vkDestroyPipelineLayout(device, pipelineLayout, nullptr);
    // ...
}
```

파이프라인은 더 이상 사용되지 않을 때 명시적으로 파괴해야 한다. 예를 들어:
- 애플리케이션 종료 시
- 윈도우 리사이즈로 인한 Swapchain 재생성 시 (Render Pass 호환성 때문)

### 6.4. 파이프라인 특성

**불변성 (Immutable):**
- 파이프라인 생성 후 대부분의 상태 변경 불가
- 다른 렌더링 상태가 필요하면 새 파이프라인 생성 필요
- 동적 상태(`VkDynamicState`)로 지정된 항목만 런타임 변경 가능

**성능 최적화:**
- 생성 비용이 높으므로 초기화 시점에 미리 생성
- 여러 파이프라인을 한 번에 생성하여 병렬 처리 활용
- `VkPipelineCache` 사용으로 재생성 시간 단축

**파이프라인 파생 (Pipeline Derivatives):**
- 기존 파이프라인을 기반으로 새 파이프라인 생성 가능
- 일부 상태만 다른 유사한 파이프라인의 경우 생성 속도 향상
- `basePipelineHandle` 또는 `basePipelineIndex` 사용

---

## 7. 정리 순서

```cpp
void cleanup() {
    vkDestroyPipeline(device, graphicsPipeline, nullptr);
    vkDestroyPipelineLayout(device, pipelineLayout, nullptr);
    vkDestroyRenderPass(device, renderPass, nullptr);

    for (auto imageView : swapChainImageViews) {
        vkDestroyImageView(device, imageView, nullptr);
    }

    vkDestroySwapchainKHR(device, swapChain, nullptr);
    vkDestroyDevice(device, nullptr);
    vkDestroySurfaceKHR(instance, surface, nullptr);
    vkDestroyInstance(instance, nullptr);
}
```

**정리 순서**: Pipeline → Pipeline Layout → Render Pass → Image Views → Swapchain → Device → Surface → Instance

---

## 8. 핵심 개념 정리

### 8.1. Graphics Pipeline

- 정점 데이터를 픽셀로 변환하는 일련의 과정
- Vulkan은 모든 단계를 명시적으로 구성
- 생성 후 대부분의 상태 변경 불가 (불변)

### 8.2. Shader Module

- GPU에서 실행되는 프로그램
- GLSL로 작성 → SPIR-V로 컴파일
- Pipeline 생성 후 파괴 가능

### 8.3. Render Pass

- 프레임버퍼 어태치먼트 구조 정의
- Load/Store 동작 지정
- 서브패스 및 의존성 관리

### 8.4. 고정 함수 단계

- Vertex Input, Input Assembly, Viewport, Rasterizer 등
- 프로그래밍 불가, 설정으로 제어
- 일부는 동적 상태로 설정 가능

---

## 9. 다음 단계

Graphics Pipeline을 생성했다. 이제 필요한 것:

1. **Framebuffer**: Render Pass와 Image View 연결
2. **Command Buffer**: GPU 명령 기록
3. **Synchronization**: 렌더링 동기화

다음 편에서는 **Framebuffer와 Command Buffer**를 생성하여 실제 렌더링 명령을 기록한다.

---

**다음 편**: [Vulkan] EP10. Framebuffer와 Command Buffer
