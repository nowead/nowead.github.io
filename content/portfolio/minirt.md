---
title: "miniRT - Ray Tracing Renderer"
date: 2024-09-01
weight: 2
tags: ["C", "Ray Tracing", "Graphics", "42Seoul", "Phong", "Texture Mapping"]
github: "https://github.com/nowead/miniRT"
summary: "CPU 기반 Ray Tracing 렌더러 - Phong Reflection 및 Texture Mapping 지원"
cover_image: "minirt-image/minRT1.png"
---

## 프로젝트 개요

miniRT는 42Seoul의 그래픽스 프로젝트로, CPU 기반의 Ray Tracing 렌더러를 처음부터 구현한 프로젝트입니다. MiniLibX 그래픽 라이브러리를 사용하여 Sphere, Plane, Cylinder, Cone 등의 기본 3D 오브젝트를 렌더링하고, Phong Reflection Model을 통한 사실적인 조명 계산과 Texture Mapping, Bump Mapping을 지원합니다.

## 핵심 기술 스택

- **언어:** C (C99)
- **그래픽 라이브러리:** MiniLibX (macOS 및 Linux 지원)
- **렌더링 기법:** Ray Tracing, Phong Reflection Model
- **텍스처:** XPM 포맷, Bump Mapping
- **빌드 시스템:** Makefile

## 주요 기능

### 1. Ray Tracing 구현

**기본 Ray Tracing 알고리즘:**
```c
t_color trace_ray(t_scene *scene, t_vec3 ray_dir) {
    t_closest_hit closest_hit;
    
    // 1. 광선-오브젝트 교차 검사
    closest_hit = closest_intersection(
        (t_ray){scene->camera.pos, ray_dir}, 
        (t_float_range){0, FLT_MAX}, 
        scene
    );
    
    if (!closest_hit.obj)
        return BACKGROUND_COLOR;
        
    // 2. 표면 색상 계산
    t_point3 p = ray_origin + t * ray_dir;
    t_color surface_color = get_surface_color(p, &closest_hit);
    
    // 3. 조명 계산
    t_color lighting = compute_lighting(p, -ray_dir, &closest_hit, scene);
    
    return surface_color * lighting;
}
```

### 2. 지원 오브젝트 및 교차 검사

**Sphere**(구)
```c
void intersect_ray_sphere(t_inter_vars vars) {
    // 이차 방정식 계수 계산
    compute_sphere_quadratic_coefficients(
        vars.ray, &vars.obj->data.sphere, coeff
    );
    
    // 교차점 t 값 계산
    if (solve_quadratic_equation(coeff, t)) {
        update_closest_hit(t[0], 0, &vars);
        if (t[0] != t[1])
            update_closest_hit(t[1], 0, &vars);
    }
}
```

**Plane**(평면)
- 무한 평면 ray-plane 교차 검사
- 법선 벡터 기반 조명 계산

**Cylinder**(원기둥)
- 원기둥 측면 (side) 및 양쪽 캡 (top/bottom cap) 교차 검사
- 높이 제한 조건 검사

**Cone (원뿔)**
- 원뿔 측면 및 바닥 캡 교차 검사
- 이차 방정식 기반 교차점 계산

### 3. Phong Reflection Model

**조명 계산:**
```c
t_color compute_lighting(t_point3 p, t_vec3 v, 
                        t_closest_hit *hit, t_scene *scene) {
    t_color intens = {0, 0, 0};
    
    // Ambient Light (환경광)
    add_light_intensity(&intens, ambient_factor, &ambient_color);
    
    // Diffuse + Specular for each light
    for (each light in scene) {
        t_vec3 L = light_pos - p;  // Light direction
        float n_dot_l = dot(N, L);
        
        // Diffuse (확산 반사)
        if (n_dot_l > 0) {
            factor = light->intens * n_dot_l / length(L);
            add_light_intensity(&intens, factor, &light->color);
        }
        
        // Specular (정반사)
        if (obj->specular > 0) {
            t_vec3 R = reflect(L, N);
            float r_dot_v = dot(R, V);
            if (r_dot_v > 0) {
                factor = light->intens * pow(r_dot_v / (length(R) * length(V)), 
                                           obj->specular);
                add_light_intensity(&intens, factor, &light->color);
            }
        }
    }
    
    return clamp_light_intens(intens);
}
```

### 4. Texture Mapping 지원

**체커보드 패턴:**
```c
typedef struct s_checkerboard {
    t_color color1;
    t_color color2;
    int     columns;
    int     rows;
} t_checkerboard;

t_color get_checkerboard_color(t_checkerboard *checkerboard, 
                               t_point2 texture_point) {
    int col = (int)(texture_point.x * checkerboard->columns);
    int row = (int)(texture_point.y * checkerboard->rows);
    
    if ((col + row) % 2 == 0)
        return checkerboard->color1;
    else
        return checkerboard->color2;
}
```

**XPM 이미지 텍스처:**
- XPM 파일 로딩 및 텍스처 좌표 매핑
- UV 좌표 계산 (Sphere, Cylinder, Cone별로 다른 매핑)

**Bump Mapping:**
- 법선 맵을 사용한 표면 디테일 향상
- World space -> Local space 변환

### 5. 카메라 시스템

**카메라 변환 및 뷰포트:**
```c
void init_camera_and_viewport(t_camera *camera, t_img *img) {
    camera->fov_radian = camera->fov * M_PI / 180;
    camera->viewport_w = 2 * tan(camera->fov_radian / 2);
    camera->viewport_h = camera->viewport_w * (img->height / (float)img->width);
    
    // View coordinate system
    t_vec3 w = unit_vector(camera->dir);
    camera->u = unit_vector(cross((t_vec3){0, 1, 0}, w));
    camera->v = cross(w, camera->u);
}

t_vec3 canvas_to_viewport(int x, int y, t_img *img, t_camera *camera) {
    float x_offset = x * (camera->viewport_w / img->width);
    float y_offset = y * (camera->viewport_h / img->height);
    
    t_vec3 x_component = scale_vector(camera->u, x_offset);
    t_vec3 y_component = scale_vector(camera->v, y_offset);
    
    t_point3 p = viewport_center + x_component + y_component;
    return p - camera->pos;
}
```

## .rt 파일 포맷

**장면 파일 예시:**
```plaintext
A 0.2 255,255,255          # Ambient light
C -50,0,20 0,0,1 70        # Camera (position, direction, FOV)
L -40,0,30 0.7 255,255,255 # Point light

sp 0,0,20 20 255,0,0       # Sphere (center, diameter, color)
pl 0,0,0 0,1,0 0,255,0     # Plane (position, normal, color)
cy 50,0,20 0,0,1 14 30 0,0,255  # Cylinder (pos, axis, dia, height, color)
co 0,-10,0 0,1,0 20 30 255,255,0 # Cone (vertex, axis, dia, height, color)
```

## 조작 방법

```plaintext
W / A / S / D : 카메라 전/후/좌/우 이동
Q / E         : 카메라 하강 / 상승
방향키        : 카메라 시점 회전 (상/하/좌/우)
ESC           : 프로그램 종료
```

## 프로젝트 구조

```plaintext
miniRT/
├── includes/          # 헤더 파일
│   └── minirt.h
├── libft/             # 기본 함수 라이브러리
├── mlx_macbook/       # macOS용 MiniLibX
├── mlx_intel/         # Intel 기반 MiniLibX
├── textures/          # 텍스처 이미지 파일
├── scenes/            # 테스트용 .rt 장면 파일
└── sources/           # 소스 코드
    ├── minirt.c
    ├── parse/         # 장면 파일 파싱
    └── render/        # 렌더링 로직
        ├── render_scene.c
        ├── closest_intersection.c
        ├── intersect_ray_*.c
        ├── compute_lighting.c
        ├── get_surface_color.c
        └── vector_operations*.c
```

## 빌드 및 실행

```bash
# Clone repository
git clone https://github.com/nowead/miniRT.git
cd miniRT

# Build project
make

# Run with sample scene
./miniRT scenes/test.rt
```

## 주요 성과

- **Ray Tracing 알고리즘 완전 구현:** CPU 기반 광선 추적 렌더러
- **다양한 오브젝트 지원:** Sphere, Plane, Cylinder, Cone
- **사실적인 조명:** Phong Reflection Model (Ambient + Diffuse + Specular)
- **Texture Mapping:** 체커보드, XPM 이미지, Bump Mapping
- **실시간 카메라 제어:** 키보드 입력을 통한 카메라 이동 및 회전
- **파싱 시스템:** .rt 파일 형식 정의 및 파싱 구현

## 기술적 도전 과제

1. **이차 방정식 해결:** Sphere, Cylinder, Cone 교차 검사
2. **벡터 수학 구현:** Dot product, Cross product, Normalization
3. **좌표계 변환:** World space <-> Local space <-> Texture space
4. **조명 계산 최적화**: Shadow ray, Reflection ray 구현
5. **메모리 관리**: MiniLibX와 C 표준 라이브러리 조합

---

**개발 기간:** 2024.09 ~ 2024.10  
**팀 구성:** 2인 (민대원, 서성진)  
**주요 기술:** C, Ray Tracing, Phong Reflection, Texture Mapping, MiniLibX
