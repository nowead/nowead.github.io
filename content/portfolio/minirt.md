---
title: "miniRT - Ray Tracing Renderer"
date: 2024-09-01
weight: 2
tags: ["C", "Ray Tracing", "Graphics", "42Seoul", "Phong", "Texture Mapping"]
github: "https://github.com/nowead/miniRT"
summary: "CPU 기반 Ray Tracing 렌더러 - Phong Reflection 및 Texture Mapping 지원"
cover_image: "minirt-image/minRT1.png"
---

# miniRT

> CPU 기반 Ray Tracing 렌더러 — 수학, 벡터 연산, 광선 추적 알고리즘 구현

**C (C99) | Ray Tracing | Phong Reflection | Texture Mapping**

2024.09 ~ 2024.10 (2개월) | 2인 개발 | macOS

---

## Overview

MiniLibX를 사용하여 CPU 기반 Ray Tracing 렌더러를 처음부터 구현한 그래픽스 프로젝트.

| 항목 | 내용 |
|------|------|
| **언어** | C (C99), 외부 수학 라이브러리 없음 |
| **렌더링** | Ray Tracing, Phong Reflection Model |
| **오브젝트** | Sphere, Plane, Cylinder, Cone |
| **기능** | Texture Mapping, Bump Mapping, 멀티 라이트 |

**Motivation**: 그래픽스 수학의 기초부터 구현하며 벡터 연산, 광선-표면 교차 검사, 조명 모델을 코드로 실현.

---

## Challenge 1: 광선-오브젝트 교차 검사 수학

### Problem
Sphere, Cylinder, Cone은 모두 이차 방정식 기반 교차 검사 필요. 수학 공식을 코드로 정확히 변환해야 함.

### Sphere 교차 검사
광선: $\mathbf{P}(t) = \mathbf{O} + t\mathbf{D}$, 구: $||\mathbf{P} - \mathbf{C}||^2 = r^2$

이차 방정식 유도:
```c
// (O + tD - C) · (O + tD - C) = r²
// at² + bt + c = 0
t_vec3 oc = ray.origin - sphere.center;
float a = dot(ray.dir, ray.dir);
float b = 2 * dot(oc, ray.dir);
float c = dot(oc, oc) - sphere.radius * sphere.radius;

float discriminant = b*b - 4*a*c;
if (discriminant < 0) return NO_HIT;  // 교차 없음

float t1 = (-b - sqrt(discriminant)) / (2*a);
float t2 = (-b + sqrt(discriminant)) / (2*a);
```

### Cylinder 교차 검사
원기둥은 **측면 (infinite cylinder) + 양쪽 캡 (두 원)**으로 구성:

**측면 교차**:
```c
// 광선을 원기둥 로컬 좌표계로 변환
t_vec3 X = ray.origin - cylinder.center;
t_vec3 Y = cylinder.axis;  // 원기둥 축

// (X + tD) - [(X + tD)·Y]Y의 노름이 r인 점 찾기
float a = dot(D, D) - pow(dot(D, Y), 2);
float b = 2 * (dot(X, D) - dot(X, Y) * dot(D, Y));
float c = dot(X, X) - pow(dot(X, Y), 2) - r*r;

// 이차 방정식 풀이 후 높이 제약 검사
if (abs(dot(hit_point - base, axis)) > height) return NO_HIT;
```

**캡 교차**: 평면-광선 교차 후 반지름 체크
```c
float denom = dot(ray.dir, cap_normal);
if (abs(denom) < EPSILON) return NO_HIT;

float t = dot(cap_center - ray.origin, cap_normal) / denom;
t_point3 p = ray.origin + t * ray.dir;

if (distance(p, cap_center) > radius) return NO_HIT;
```

### Impact
- 모든 벡터 연산 함수를 직접 구현 (dot, cross, normalize, reflect)
- 부동소수점 정밀도 이슈 경험 (EPSILON 처리)
- **교훈**: 그래픽스는 수학을 코드로 번역하는 과정. 공식의 기하학적 의미 이해가 디버깅의 핵심.

---

## Challenge 2: Phong Reflection 최적화

### Problem
각 픽셀마다 모든 광원에 대해 Phong 계산 → 800x600 해상도에서 10초 렌더링 시간.

### Phong Model 구현
$I = I_a + \sum_{lights} [I_d (\mathbf{N} \cdot \mathbf{L}) + I_s (\mathbf{R} \cdot \mathbf{V})^{shininess}]$

```c
t_color compute_lighting(t_point3 p, t_vec3 N, t_vec3 V, 
                         t_object *obj, t_scene *scene) {
    t_color result = obj->ambient * scene->ambient_light;
    
    for (int i = 0; i < scene->num_lights; i++) {
        t_vec3 L = normalize(scene->lights[i].pos - p);
        
        // Shadow ray 체크
        if (is_in_shadow(p, L, scene)) continue;
        
        // Diffuse
        float n_dot_l = max(dot(N, L), 0);
        result += obj->diffuse * scene->lights[i].color * n_dot_l;
        
        // Specular
        if (obj->shininess > 0) {
            t_vec3 R = reflect(-L, N);  // 반사 벡터
            float r_dot_v = max(dot(R, V), 0);
            float spec = pow(r_dot_v, obj->shininess);
            result += scene->lights[i].color * spec;
        }
    }
    return clamp(result, 0, 1);
}
```

### Optimization: 조기 종료 & 벡터 캐싱
```c
// 1. Bounding box early rejection
if (!ray_intersects_bbox(ray, scene->bbox)) return BACKGROUND;

// 2. 가장 가까운 교차점만 계산 (closest-hit 방식)
t_closest_hit closest = {.t = FLT_MAX, .obj = NULL};
for (each object) {
    float t = intersect(ray, object);
    if (t > 0 && t < closest.t) {
        closest.t = t;
        closest.obj = object;
    }
}

// 3. 반사 벡터 재사용 (specular 계산 시)
```

### Multi-threading (pthread)
```c
typedef struct s_thread_data {
    t_scene *scene;
    int start_y;
    int end_y;
} t_thread_data;

void *render_rows(void *arg) {
    t_thread_data *data = (t_thread_data *)arg;
    for (int y = data->start_y; y < data->end_y; y++) {
        for (int x = 0; x < WIDTH; x++) {
            t_color pixel = trace_ray(x, y, data->scene);
            put_pixel(data->scene->img, x, y, pixel);
        }
    }
    return NULL;
}

// 4개 스레드로 화면을 수평 분할
pthread_t threads[4];
for (int i = 0; i < 4; i++) {
    data[i].start_y = i * (HEIGHT / 4);
    data[i].end_y = (i + 1) * (HEIGHT / 4);
    pthread_create(&threads[i], NULL, render_rows, &data[i]);
}
```

### Impact
- 렌더링 시간: 10초 → **2.5초** (4배 향상)
- **교훈**: 그래픽스 최적화는 수학적 최적화 (조기 종료)와 병렬화의 조합. 프레임 단위 병렬화가 가장 효과적.

---

## Challenge 3: Texture Mapping 좌표 변환

### Problem
3D 표면 위치를 2D 텍스처 좌표 (UV)로 변환. Sphere, Cylinder, Cone마다 다른 매핑 필요.

### Sphere UV Mapping (구면 좌표)
```c
t_point2 sphere_uv(t_point3 hit_point, t_sphere *sphere) {
    t_vec3 d = normalize(hit_point - sphere->center);
    
    // 구면 좌표: θ (azimuth), φ (elevation)
    float theta = atan2(d.z, d.x);        // [-π, π]
    float phi = asin(d.y);                 // [-π/2, π/2]
    
    float u = (theta + M_PI) / (2 * M_PI); // [0, 1]
    float v = (phi + M_PI/2) / M_PI;       // [0, 1]
    
    return (t_point2){u, v};
}
```

### Cylinder UV Mapping
```c
t_point2 cylinder_uv(t_point3 hit_point, t_cylinder *cy) {
    t_vec3 d = hit_point - cy->base;
    
    // U: 원주 방향 (각도)
    float theta = atan2(d.z, d.x);
    float u = (theta + M_PI) / (2 * M_PI);
    
    // V: 높이 방향
    float v = dot(d, cy->axis) / cy->height;
    
    return (t_point2){u, v};
}
```

### XPM Texture Lookup
```c
t_color get_texture_color(t_texture *tex, t_point2 uv) {
    int x = (int)(uv.x * tex->width) % tex->width;
    int y = (int)(uv.y * tex->height) % tex->height;
    
    // XPM data는 int 배열
    int color = tex->data[y * tex->width + x];
    return int_to_color(color);
}
```

### Bump Mapping (Normal Perturbation)
```c
t_vec3 apply_bump_map(t_vec3 N, t_point2 uv, t_texture *bump_map) {
    // Bump map에서 높이 정보 추출
    float h = get_texture_color(bump_map, uv).r;  // grayscale
    
    // 인접 픽셀과의 차이로 gradient 계산
    float dh_du = h - get_texture_color(bump_map, 
                      (t_point2){uv.x + 0.01, uv.y}).r;
    float dh_dv = h - get_texture_color(bump_map, 
                      (t_point2){uv.x, uv.y + 0.01}).r;
    
    // Tangent space에서 normal 섭동
    t_vec3 tangent = get_tangent(N);
    t_vec3 bitangent = cross(N, tangent);
    
    t_vec3 perturbed = N + dh_du * tangent + dh_dv * bitangent;
    return normalize(perturbed);
}
```

### Impact
- Sphere, Cylinder, Cone에 텍스처 매핑 성공
- Bump mapping으로 표면 디테일 향상
- **교훈**: 좌표계 변환 (World → Local → Texture)의 연쇄. 각 단계의 수학적 의미를 시각화하며 디버깅.

---

## Key Takeaways

### Mathematics
- **벡터 수학이 그래픽스의 언어**: Dot product (투영, 거리), Cross product (법선), Normalize (방향)
- **이차 방정식 everywhere**: Ray-sphere, ray-cylinder, ray-cone 모두 $at^2 + bt + c = 0$
- **좌표계 변환의 연쇄**: World space → Object local space → Texture space

### Low-Level Optimization
- **Memory layout matters**: 구조체 패딩, 캐시 친화적 배열 순회
- **Floating-point precision**: EPSILON 처리, `fabs(x) < EPSILON` vs `x == 0`
- **병렬화**: pthread로 픽셀 단위 독립 계산 병렬화

### Graphics Concepts
- **Ray tracing은 역방향 렌더링**: 픽셀 → 광선 → 표면 → 광원 (물리와 반대)
- **Phong model의 물리적 의미**: Ambient (환경광) + Diffuse (확산 반사) + Specular (정반사)
- **Texture mapping**: 3D → 2D 투영, UV 좌표의 연속성 및 seam 처리

---

*개발 기간: 2024.09 ~ 2024.10 | 팀: 2인 (민대원, 서성진)*