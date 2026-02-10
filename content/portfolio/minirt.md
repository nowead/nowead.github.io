---
title: "miniRT - Ray Tracing Renderer"
date: 2024-08-30
weight: 2
tags: ["C", "Ray Tracing", "Graphics", "42Seoul", "Phong", "Texture Mapping"]
github: "https://github.com/nowead/miniRT"
summary: "CPU 기반 Ray Tracing 렌더러 - Phong Reflection 및 Texture Mapping 지원"
cover_image: "minirt-image/minRT1.png"
---

# miniRT

> CPU 기반 Ray Tracing 렌더러 — 외부 라이브러리 없이 수학 구현

**C (C99) | Ray Tracing | Phong Reflection | Texture Mapping**

2024.08 ~ 2024.10 (2개월) | 2인 개발 | macOS

---

## Overview

외부 수학 라이브러리 없이 CPU 기반 Ray Tracer를 처음부터 구현한 그래픽스 프로젝트.

| 항목 | 내용 |
|------|------|
| **언어** | C (C99), 외부 수학 라이브러리 없음 |
| **렌더링** | Ray Tracing, Phong Reflection Model |
| **오브젝트** | Sphere, Plane, Cylinder, Cone |
| **기능** | Texture Mapping, Bump Mapping, 멀티 라이트 |

**Motivation**: 그래픽스 수학의 기초부터 구현하며 벡터 연산, 광선-표면 교차 검사, 조명 모델을 코드로 실현.

![miniRT Rendering 1](/portfolio/minirt-image/minRT1.png)

*Phong Reflection Model: Ambient + Diffuse + Specular 조명 계산 결과*

![miniRT Rendering 2](/portfolio/minirt-image/miniRT2.png)

*멀티 라이트 소스: 각 광원의 그림자 및 반사광 독립 계산 후 합산*

---

## Challenge 1: Ray-Surface Intersection의 수학적 정확성

### Problem
Sphere, Cylinder, Cone의 광선 교차 검사는 모두 이차 방정식 풀이 필요. 수학 공식의 기하학적 의미를 이해하고 부동소수점 정밀도 문제를 해결해야 함.

### Sphere: 기본 이차방정식
광선 $\mathbf{P}(t) = \mathbf{O} + t\mathbf{D}$를 구 방정식 $||\mathbf{P} - \mathbf{C}||^2 = r^2$에 대입:

$$at^2 + bt + c = 0$$
$$a = \mathbf{D} \cdot \mathbf{D}, \quad b = 2(\mathbf{O} - \mathbf{C}) \cdot \mathbf{D}, \quad c = ||\mathbf{O} - \mathbf{C}||^2 - r^2$$

```c
t_vec3 oc = ray.origin - sphere.center;
float a = dot(ray.dir, ray.dir);
float b = 2 * dot(oc, ray.dir);
float c = dot(oc, oc) - sphere.radius * sphere.radius;

float discriminant = b*b - 4*a*c;
if (discriminant < 0) return NO_HIT;  // 교차 없음

float t1 = (-b - sqrt(discriminant)) / (2*a);
float t2 = (-b + sqrt(discriminant)) / (2*a);
```

### Cylinder: 축에 수직인 성분 분해
무한 원기둥 방정식에서 높이 제약을 추가:
- 광선 방향을 축 방향과 수직 성분으로 분해: $\mathbf{D}_\perp = \mathbf{D} - (\mathbf{D} \cdot \mathbf{A})\mathbf{A}$
- 이차방정식 풀이 후 높이 제약 검사: $0 \leq m \leq h$

```c
// 측면 교차
t_vec3 X = ray.origin - cylinder.center;
t_vec3 Y = cylinder.axis;
float a = dot(D, D) - pow(dot(D, Y), 2);
float b = 2 * (dot(X, D) - dot(X, Y) * dot(D, Y));
float c = dot(X, X) - pow(dot(X, Y), 2) - r*r;

// 캡: 평면-광선 교차 + 반지름 체크
if (distance(hit_point, cap_center) > radius) return NO_HIT;
```

### 부동소수점 정밀도 문제
**Shadow Acne**: 표면 위의 점에서 광선을 쏠 때 자기 자신과 교차

**해결**:
```c
t_closest_hit shadow = closest_intersection(
    (t_ray){p, L},
    (t_float_range){0.001, 1},  // t_min = 0.001로 극소 교차 무시
    scene
);
```

### Impact
- Sphere, Plane, Cylinder, Cone 교차 검사 구현 완료
- 모든 벡터 연산(dot, cross, normalize, scale) 직접 구현
- **교훈**: 수학 공식의 기하학적 의미 이해가 디버깅의 핵심. `discriminant < 0`은 "교차 없음"의 물리적 의미.

---

## Challenge 2: 좌표계 변환과 법선 벡터 계산

### Problem
Cylinder와 Cone은 World Space에서 임의 방향을 가지므로, 교차점의 법선 벡터와 텍스처 좌표를 계산하려면 Local Space로 변환 필요. 좌표계 변환 과정에서 정밀도 손실 발생.

### World → Local 좌표 변환
임의 방향의 원기둥을 Y-up 좌표계로 변환. 회전 행렬 대신 벡터 투영 사용:

$$\mathbf{P}_{local} = \mathbf{R}^{-1}(\mathbf{P}_{world} - \mathbf{C})$$

```c
t_vec3 world_to_local(t_vec3 p, t_vec3 axis, t_point3 center) {
    t_vec3 cp = subtract_3dpoints(p, center);
    // axis를 Y축으로 매핑 (투영 기반 변환)
    return (t_vec3){...};
}
```

### Cylinder 법선 벡터
- **측면**: 축에 수직한 방향 $\mathbf{N} = normalize(\mathbf{P} - \mathbf{C} - [(\mathbf{P} - \mathbf{C}) \cdot \mathbf{A}] \mathbf{A})$
- **캡**: 축 방향 $\mathbf{N} = \pm\mathbf{A}$

### Sphere UV Mapping
구면 좌표 변환:
```c
t_point2 sphere_uv(t_point3 hit_point, t_sphere *sphere) {
    t_vec3 d = normalize(hit_point - sphere->center);
    
    // θ (방위각), φ (고도각)
    float theta = atan2(d.z, d.x);    // [-π, π]
    float phi = asin(d.y);            // [-π/2, π/2]
    
    float u = (theta + M_PI) / (2 * M_PI);  // [0, 1]
    float v = (phi + M_PI/2) / M_PI;        // [0, 1]
    
    return (t_point2){u, v};
}
```

**Pole 특이점 처리**: 극 근처에서 UV 불연속 해결

### Bump Mapping
```c
// 인접 픽셀 gradient로 법선 섭동
float dh_du = h - get_texture_color(bump_map, (t_point2){uv.x + 0.01, uv.y}).r;
float dh_dv = h - get_texture_color(bump_map, (t_point2){uv.x, uv.y + 0.01}).r;

t_vec3 perturbed = N + dh_du * tangent + dh_dv * bitangent;
return normalize(perturbed);
```

### Impact
- World ↔ Local 좌표 변환 구현
- Sphere/Cylinder/Cone 법선 벡터 계산
- UV 매핑: 구면 좌표, 원통 좌표 변환
- **교훈**: 좌표계 변환은 기하학적 의미 이해 필수. Tangent space 계산 시 직교 기저 구성 중요.

---

## Challenge 3: Phong Lighting과 Shadow Acne

### Problem
Phong Reflection Model 구현 시 각 픽셀마다 모든 광원에 대해 조명 계산 필요. 그림자 계산 시 self-intersection으로 인한 shadow acne 발생.

### Phong Model 구현
$$I = I_a + \sum_{lights} \left[ I_d (\mathbf{N} \cdot \mathbf{L}) + I_s \left(\frac{\mathbf{R} \cdot \mathbf{V}}{||\mathbf{R}|| \cdot ||\mathbf{V}||}\right)^{shininess} \right]$$

```c
t_color compute_lighting(t_point3 p, t_vec3 N, t_vec3 V, 
                         t_object *obj, t_scene *scene) {
    t_color result = obj->ambient * scene->ambient_light;
    
    for (int i = 0; i < scene->num_lights; i++) {
        t_vec3 L = normalize(scene->lights[i].pos - p);
        
        // Shadow ray 체크
        if (is_in_shadow(p, L, scene)) continue;
        
        // Diffuse: Lambert 코사인 법칙
        float n_dot_l = max(dot(N, L), 0);
        result += obj->diffuse * scene->lights[i].color * n_dot_l;
        
        // Specular: 반사 벡터 R = 2(N·L)N - L
        if (obj->shininess > 0) {
            t_vec3 R = reflect(-L, N);
            float r_dot_v = max(dot(R, V), 0);
            float spec = pow(r_dot_v, obj->shininess);
            result += scene->lights[i].color * spec;
        }
    }
    return clamp(result, 0, 1);
}
```

### Shadow Acne 해결
**문제**: `t_min=0`일 때 표면이 자기 자신과 교차 감지 (부동소수점 오차)

**해결**: `t_min=0.001`로 설정하여 극소 교차 무시
```c
t_closest_hit shadow = closest_intersection(
    (t_ray){p, L},
    (t_float_range){0.001, 1},  // 핵심: t_min = 0.001
    scene
);
```

### 멀티 라이트 & 렌더링 최적화
- Linked list로 광원 관리, 각 광원 독립 계산 후 합산
- 색상 clamping: `fminf(intens.r, 1.0f)` (overflow 방지)
- pthread 병렬화: 4개 스레드로 화면 수평 분할 → **10초 → 2.5초** (4배 향상)

### Impact
- Phong Model: Ambient + Diffuse + Specular 구현
- Shadow ray: 각 광원 그림자 계산 (멀티 라이트 지원)
- Shadow acne 해결: `t_range = [0.001, 1]`
- **교훈**: Shadow acne는 부동소수점 정밀도 문제. Epsilon 사용 시 물리적 의미(극소 거리 무시) 이해 필요.

---

## Key Takeaways

### Mathematics
- **이차 방정식 everywhere**: Ray-sphere, ray-cylinder, ray-cone 모두 $at^2 + bt + c = 0$
- **벡터 수학이 그래픽스의 언어**: Dot product (투영, 거리), Cross product (법선), Normalize (방향)
- **좌표계 변환의 연쇄**: World space → Object local space → Texture space

### Graphics Concepts
- **Ray Tracing 역방향 렌더링**: 픽셀 → 광선 → 표면 → 광원 (물리와 반대)
- **Phong Model의 물리적 의미**: Ambient (환경광) + Diffuse (확산 반사) + Specular (정반사)
- **Shadow Acne**: 부동소수점 정밀도 문제, `t_min=0.001`로 극소 교차 무시

### Low-Level C
- **외부 라이브러리 없음**: 수학 함수 직접 구현 (sqrt, pow, atan2, acos)
- **메모리 최적화**: Union 기반 객체 저장, 구조체 패딩 고려
- **정밀도 처리**: `< EPSILON` vs `< 0` 구분, 물리적 의미 기반 임계값 설정

---

*개발 기간: 2024.08 ~ 2024.10 | 팀: 2인 (민대원, 서성진)*