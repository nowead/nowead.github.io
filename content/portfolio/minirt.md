---
title: "miniRT"
date: 2024-08-30
weight: 3
category: "graphics"
category_label: "CPU ray tracer"
period: "2024.08 — 2024.10"
role: "2인 프로젝트"
image_alt: "구, 평면, 원기둥의 재질과 조명을 계산한 miniRT 렌더링 화면"
tags: ["C", "Ray Tracing", "Graphics", "42Seoul", "Phong", "Texture Mapping"]
github: "https://github.com/nowead/miniRT"
summary: "CPU 기반 Ray Tracing 렌더러 - Phong Reflection 및 Texture Mapping 지원"
cover_image: "minirt-image/minRT1.png"
math: true
---

> CPU 기반 Ray Tracing 렌더러 — 벡터 연산부터 교차 검사와 조명 계산까지 직접 구현

**C (C99) | Ray Tracing | Phong Reflection | Texture Mapping**

2024.08 ~ 2024.10 (2개월) | 2인 개발 | macOS

---

## 프로젝트 소개

C로 벡터 연산, 광선과 표면의 교차 검사, 조명 모델을 구현한 CPU 기반 Ray Tracer입니다.

| 항목 | 내용 |
|------|------|
| **언어** | C (C99), 벡터 연산 직접 구현 |
| **렌더링** | Ray Tracing, Phong Reflection Model |
| **오브젝트** | Sphere, Plane, Cylinder, Cone |
| **기능** | Texture Mapping, Bump Mapping, 멀티 라이트 |

**개발 목적**: 그래픽스 수식을 직접 코드로 옮기며 벡터 연산과 좌표계, 빛과 표면의 관계를 이해하고자 했습니다.

![miniRT Rendering 1](/portfolio/minirt-image/minRT1.png)

*Phong Reflection Model: Ambient + Diffuse + Specular 조명 계산 결과*

![miniRT Rendering 2](/portfolio/minirt-image/miniRT2.png)

*멀티 라이트 소스: 각 광원의 그림자 및 반사광 독립 계산 후 합산*

---

## 광선과 표면의 교차 계산

### 구현 과제
구, 원기둥, 원뿔의 곡면과 광선이 만나는 지점을 구하려면 이차방정식을 풀어야 합니다. 수식의 기하학적 의미를 이해하고, 부동소수점 오차로 잘못된 교차점이 선택되지 않도록 처리했습니다.

아래 코드 예시는 핵심 계산 흐름을 간략화한 의사 코드입니다.

### Sphere: 기본 이차방정식
광선 {{< math label="P(t) = O + tD" >}}<mi mathvariant="bold">P</mi><mo>(</mo><mi>t</mi><mo>)</mo><mo>=</mo><mi mathvariant="bold">O</mi><mo>+</mo><mi>t</mi><mi mathvariant="bold">D</mi>{{< /math >}}를 구의 방정식 {{< math label="P에서 C를 뺀 벡터의 길이의 제곱 = r의 제곱" >}}<msup><mrow><mo>‖</mo><mi mathvariant="bold">P</mi><mo>−</mo><mi mathvariant="bold">C</mi><mo>‖</mo></mrow><mn>2</mn></msup><mo>=</mo><msup><mi>r</mi><mn>2</mn></msup>{{< /math >}}에 대입하면 다음 이차방정식을 얻습니다. O는 광선의 시작점, D는 방향, C는 구의 중심, r은 반지름입니다.

{{< math display="block" label="a t의 제곱 + b t + c = 0" >}}
<mi>a</mi><msup><mi>t</mi><mn>2</mn></msup><mo>+</mo><mi>b</mi><mi>t</mi><mo>+</mo><mi>c</mi><mo>=</mo><mn>0</mn>
{{< /math >}}

각 계수는 다음과 같이 계산합니다.

{{< math display="block" label="a = D 내적 D. b = 2 곱하기 (O − C) 내적 D. c = O − C의 길이의 제곱 − r의 제곱." >}}
<mtable columnalign="right left" rowspacing="0.6em">
<mtr><mtd><mi>a</mi></mtd><mtd><mo>=</mo><mi mathvariant="bold">D</mi><mo>·</mo><mi mathvariant="bold">D</mi></mtd></mtr>
<mtr><mtd><mi>b</mi></mtd><mtd><mo>=</mo><mn>2</mn><mo>(</mo><mi mathvariant="bold">O</mi><mo>−</mo><mi mathvariant="bold">C</mi><mo>)</mo><mo>·</mo><mi mathvariant="bold">D</mi></mtd></mtr>
<mtr><mtd><mi>c</mi></mtd><mtd><mo>=</mo><msup><mrow><mo>‖</mo><mi mathvariant="bold">O</mi><mo>−</mo><mi mathvariant="bold">C</mi><mo>‖</mo></mrow><mn>2</mn></msup><mo>−</mo><msup><mi>r</mi><mn>2</mn></msup></mtd></mtr>
</mtable>
{{< /math >}}

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
광선 방향에서 원기둥의 축 방향 성분을 빼면 축에 수직인 성분을 얻습니다. A는 원기둥의 축을 나타내는 단위 벡터입니다.

{{< math display="block" label="D의 수직 성분 = D − (D 내적 A) 곱하기 A" >}}
<msub><mi mathvariant="bold">D</mi><mo>⊥</mo></msub><mo>=</mo><mi mathvariant="bold">D</mi><mo>−</mo><mo>(</mo><mi mathvariant="bold">D</mi><mo>·</mo><mi mathvariant="bold">A</mi><mo>)</mo><mi mathvariant="bold">A</mi>
{{< /math >}}

무한 원기둥과의 교차점을 구한 뒤, 축 방향 위치 m이 높이 h 안에 있는지 {{< math label="0 ≤ m ≤ h" >}}<mn>0</mn><mo>≤</mo><mi>m</mi><mo>≤</mo><mi>h</mi>{{< /math >}} 조건으로 검사합니다.

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
**Shadow Acne**: 표면 위에서 출발한 광선이 부동소수점 오차로 같은 표면과 다시 교차하는 현상입니다.

**해결**:
```c
t_closest_hit shadow = closest_intersection(
    (t_ray){p, L},
    (t_float_range){0.001, 1},  // t_min = 0.001로 극소 교차 무시
    scene
);
```

### 구현 결과
- Sphere, Plane, Cylinder, Cone 교차 검사 구현
- 모든 벡터 연산(dot, cross, normalize, scale) 직접 구현
- **배운 점**: 수식의 기하학적 의미를 이해하면 디버깅의 기준이 명확해집니다. 예를 들어 `discriminant < 0`은 광선이 표면과 만나지 않는다는 뜻입니다.

---

## 좌표계 변환과 법선 벡터 계산

### 구현 과제
원기둥과 원뿔은 월드 좌표계에서 임의의 방향을 가질 수 있습니다. 물체를 기준으로 법선 벡터와 텍스처 좌표를 계산할 수 있도록 로컬 좌표계를 구성했습니다.

### World → Local 좌표 변환
원기둥의 축을 로컬 Y축으로 삼고, 중심에서 교차점까지의 벡터를 로컬 기저에 투영합니다. 이를 기저 행렬 R로 표현하면 다음과 같습니다.

{{< math display="block" label="Q = P world − C. P local = R의 역행렬 곱하기 Q." >}}
<mtable columnalign="right left" rowspacing="0.6em">
<mtr><mtd><mi mathvariant="bold">Q</mi></mtd><mtd><mo>=</mo><msub><mi mathvariant="bold">P</mi><mtext>world</mtext></msub><mo>−</mo><mi mathvariant="bold">C</mi></mtd></mtr>
<mtr><mtd><msub><mi mathvariant="bold">P</mi><mtext>local</mtext></msub></mtd><mtd><mo>=</mo><msup><mi mathvariant="bold">R</mi><mrow><mo>−</mo><mn>1</mn></mrow></msup><mi mathvariant="bold">Q</mi></mtd></mtr>
</mtable>
{{< /math >}}

```c
t_vec3 world_to_local(t_vec3 p, t_vec3 axis, t_point3 center) {
    t_vec3 cp = subtract_3dpoints(p, center);
    // axis를 Y축으로 매핑 (투영 기반 변환)
    return (t_vec3){...};
}
```

### Cylinder 법선 벡터
**측면**의 법선은 중심에서 교차점까지의 벡터 Q에서 축 방향 성분을 제거한 뒤 정규화합니다.

{{< math display="block" label="Q = P − C. Q의 수직 성분 = Q − (Q 내적 A) 곱하기 A. N = Q의 수직 성분을 정규화한 벡터." >}}
<mtable columnalign="right left" rowspacing="0.6em">
<mtr><mtd><mi mathvariant="bold">Q</mi></mtd><mtd><mo>=</mo><mi mathvariant="bold">P</mi><mo>−</mo><mi mathvariant="bold">C</mi></mtd></mtr>
<mtr><mtd><msub><mi mathvariant="bold">Q</mi><mo>⊥</mo></msub></mtd><mtd><mo>=</mo><mi mathvariant="bold">Q</mi><mo>−</mo><mo>(</mo><mi mathvariant="bold">Q</mi><mo>·</mo><mi mathvariant="bold">A</mi><mo>)</mo><mi mathvariant="bold">A</mi></mtd></mtr>
<mtr><mtd><mi mathvariant="bold">N</mi></mtd><mtd><mo>=</mo><mi mathvariant="normal">normalize</mi><mo>(</mo><msub><mi mathvariant="bold">Q</mi><mo>⊥</mo></msub><mo>)</mo></mtd></mtr>
</mtable>
{{< /math >}}

**캡**의 법선은 위·아래 면에 따라 축 방향 또는 그 반대 방향입니다: {{< math label="N = 양 또는 음의 A" >}}<mi mathvariant="bold">N</mi><mo>=</mo><mo>±</mo><mi mathvariant="bold">A</mi>{{< /math >}}.

### Sphere UV Mapping
교차점의 방향 벡터를 방위각과 고도각으로 변환한 뒤, 0부터 1 사이의 UV 좌표로 옮깁니다.
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

극 근처에서는 UV 좌표의 불연속을 고려해 텍스처를 처리했습니다.

### Bump Mapping
```c
// 인접 픽셀 gradient로 법선 섭동
float dh_du = h - get_texture_color(bump_map, (t_point2){uv.x + 0.01, uv.y}).r;
float dh_dv = h - get_texture_color(bump_map, (t_point2){uv.x, uv.y + 0.01}).r;

t_vec3 perturbed = N + dh_du * tangent + dh_dv * bitangent;
return normalize(perturbed);
```

### 구현 결과
- World ↔ Local 좌표 변환 구현
- Sphere/Cylinder/Cone 법선 벡터 계산
- UV 매핑: 구면 좌표, 원통 좌표 변환
- **배운 점**: 좌표계마다 기준점과 축의 의미를 명확히 해야 계산 오류를 줄일 수 있습니다. 특히 Tangent space를 구성할 때는 기저 벡터의 직교성이 중요했습니다.

---

## Phong 조명과 그림자 계산

### 구현 과제
각 픽셀에서 광원별 확산 반사와 정반사를 계산하고, 표면과 광원 사이에 다른 물체가 있는지 검사해 그림자를 표현했습니다.

### Phong Model 구현
환경광에 각 광원의 확산 반사와 정반사 성분을 더합니다. 식을 짧게 나타내기 위해 두 반사 성분의 방향 계수를 각각 {{< math label="k d" >}}<msub><mi>k</mi><mi>d</mi></msub>{{< /math >}}, {{< math label="k s" >}}<msub><mi>k</mi><mi>s</mi></msub>{{< /math >}}로 두었습니다. N은 법선, L은 광원 방향, R은 반사 방향, V는 시선 방향이며 n은 `shininess` 지수입니다.

{{< math display="block" label="k d = N 내적 L. k s = R 내적 V를 R의 길이와 V의 길이의 곱으로 나눈 값의 n 제곱." >}}
<mtable columnalign="right left" rowspacing="0.8em">
<mtr><mtd><msub><mi>k</mi><mi>d</mi></msub></mtd><mtd><mo>=</mo><mi mathvariant="bold">N</mi><mo>·</mo><mi mathvariant="bold">L</mi></mtd></mtr>
<mtr><mtd><msub><mi>k</mi><mi>s</mi></msub></mtd><mtd><mo>=</mo><msup><mrow><mo>(</mo><mfrac><mrow><mi mathvariant="bold">R</mi><mo>·</mo><mi mathvariant="bold">V</mi></mrow><mrow><mo>‖</mo><mi mathvariant="bold">R</mi><mo>‖</mo><mo>·</mo><mo>‖</mo><mi mathvariant="bold">V</mi><mo>‖</mo></mrow></mfrac><mo>)</mo></mrow><mi>n</mi></msup></mtd></mtr>
</mtable>
{{< /math >}}

{{< math display="block" label="I = I a + 모든 광원에 대한 (I d 곱하기 k d + I s 곱하기 k s)의 합" >}}
<mi>I</mi><mo>=</mo><msub><mi>I</mi><mi>a</mi></msub><mo>+</mo><munder><mo>∑</mo><mtext>lights</mtext></munder><mo>(</mo><msub><mi>I</mi><mi>d</mi></msub><msub><mi>k</mi><mi>d</mi></msub><mo>+</mo><msub><mi>I</mi><mi>s</mi></msub><msub><mi>k</mi><mi>s</mi></msub><mo>)</mo>
{{< /math >}}

코드에서는 음수가 된 내적 값을 0으로 제한해 반대 방향의 빛이 색상에 더해지지 않도록 처리했습니다.

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
**문제**: `t_min=0`이면 부동소수점 오차로 같은 표면을 교차점으로 감지할 수 있습니다.

**해결**: `t_min=0.001`로 설정해 출발점에 너무 가까운 교차점을 제외했습니다.
```c
t_closest_hit shadow = closest_intersection(
    (t_ray){p, L},
    (t_float_range){0.001, 1},  // 핵심: t_min = 0.001
    scene
);
```

### 멀티 라이트 & 렌더링 최적화
- 연결 리스트로 광원을 관리하고, 각 광원의 조명 계산 결과를 합산
- 색상 제한: `fminf(intens.r, 1.0f)`로 채널별 최댓값을 1로 제한
- pthread 병렬화: 화면을 수평으로 나누어 4개 스레드에서 렌더링

### 구현 결과
- Phong Model: Ambient + Diffuse + Specular 구현
- Shadow ray: 각 광원 그림자 계산 (멀티 라이트 지원)
- Shadow acne 해결: `t_range = [0.001, 1]`
- **배운 점**: 작은 오차라도 교차점 선택에 영향을 주면 화면에 드러납니다. Epsilon은 단순한 상수가 아니라 어떤 교차점을 제외할지 정하는 기준으로 다뤘습니다.

---

## 배운 점

### 수학
- **교차 검사의 공통 구조**: 구, 원기둥, 원뿔의 곡면과 광선의 교차 계산은 이차방정식으로 정리할 수 있습니다.
- **벡터 수학이 그래픽스의 언어**: Dot product (투영, 거리), Cross product (법선), Normalize (방향)
- **좌표계 변환의 연결:** World space → Object local space → Texture space

### 그래픽스
- **Ray Tracing의 계산 흐름:** 픽셀 → 광선 → 표면 → 광원 순서로 빛의 경로를 추적합니다.
- **Phong Model의 물리적 의미**: Ambient (환경광) + Diffuse (확산 반사) + Specular (정반사)
- **Shadow Acne**: 부동소수점 정밀도 문제, `t_min=0.001`로 극소 교차 무시

### C 프로그래밍
- **벡터 연산 직접 구현**: 내적, 외적, 정규화, 스칼라 곱을 구현하고 제곱근·삼각함수 계산에는 C 표준 수학 함수를 사용했습니다.
- **메모리 최적화**: Union 기반 객체 저장, 구조체 패딩 고려
- **정밀도 처리**: `< EPSILON` vs `< 0` 구분, 물리적 의미 기반 임계값 설정

---

*개발 기간: 2024.08 ~ 2024.10 | 팀: 2인 (민대원, 서성진)*
