+++
title = "FDE Portfolio"
aliases = ["/FDE/"]
description = "현장의 요청을 요구사항으로 정의하고, 운영되는 서비스로 만들고, 테스트로 검증하는 개발자 민대원의 포트폴리오."
name = "민대원"
role = "Forward Deployed Engineer"
profile_image = "profile.jpg"
email = "dwm951017@gmail.com"
github = "nowead"
eyebrow = "PORTFOLIO"
hero_intro = "현장의 요청을 검증 가능한 요구사항으로 정의하고, 실제로 쓰이는 서비스로 만들어 배포합니다. 완료 여부는 테스트와 운영 환경에서 확인합니다."
hero_stack = false
hero_cta = "subtle"
profile_intro = "사용자와 가까운 곳에서 문제를 듣고, 모호한 요청을 검증 가능한 요구사항으로 바꾸는 일부터 시작합니다. HTTP 서버와 렌더링 엔진을 직접 구현하며 익힌 원리를 바탕으로, 요청이 화면과 운영 환경에 닿을 때까지 책임집니다."
working_practice = "AI 코딩 에이전트를 개발 파트너로 활용하되, 완료 기준은 사람이 정한 요구사항과 테스트 하네스로 고정합니다. 빠르게 만들고, 통과한 것만 배포합니다."

[[loop]]
step = "01"
label = "DEFINE"
title = "문제 정의"
text = "한 줄짜리 요청을 확인 질문으로 좁히고, 번호가 붙은 요구사항과 결정 기록으로 남깁니다."
evidence = "onegoal · 요구사항 129개 · 결정 기록 42건"

[[loop]]
step = "02"
label = "BUILD"
title = "해결"
text = "화면부터 서버, 배포 구성까지 직접 만들어 실제 사용자가 쓰는 환경에 올립니다."
evidence = "onegoal 운영 중 · OmniMed3D 공개 데모 운영"

[[loop]]
step = "03"
label = "VERIFY"
title = "검증"
text = "완료 기준을 테스트로 고정하고, 통과한 변경만 운영 환경에 반영합니다."
evidence = "onegoal · 테스트 1,439개 · 커버리지 96.98%"

[[tracks]]
label = "TRACK 01 · MEDICAL 3D"
title = "직접 만든 렌더링 엔진이, 브라우저 의료 영상 뷰어로"
outcome = "omnimed3d"

[[tracks]]
label = "TRACK 02 · WEB SERVICE"
title = "서버와 인증을 직접 만든 경험이, 운영 중인 서비스로"
outcome = "onegoal"

[[practices]]
title = "요청을 그대로 구현하지 않습니다"
text = "한 줄짜리 요청은 확인 질문으로 범위를 좁힌 뒤 요구사항 ID를 붙입니다. 무엇을 만들고 무엇을 만들지 않을지 먼저 정합니다."

[[practices]]
title = "결정은 기록으로 남깁니다"
text = "선택한 방법과 버린 대안, 그 근거를 결정 기록(ADR)으로 남깁니다. 다음 판단은 이 기록에서 출발합니다."

[[practices]]
title = "통과한 것만 배포합니다"
text = "테스트·화면 회귀·운영 구성 점검을 하나의 명령으로 묶고, 통과한 변경만 승인을 거쳐 운영에 반영합니다."

[[stack]]
eyebrow = "DELIVERY STACK"
label = "서비스 개발·운영 기술"
title = "서비스를 만들고 운영한 기술"
items = [
  "Python · Django · JavaScript / TypeScript",
  "PostgreSQL · Redis · Docker Compose",
  "AWS Lightsail · S3 · Cloudflare · Caddy",
  "pytest · Playwright · Sentry · Better Stack"
]

[[stack]]
eyebrow = "ENGINEERING BASE"
label = "원리부터 구현한 기술"
title = "원리부터 직접 구현한 기술"
items = [
  "C / C++20 · WebAssembly (Emscripten)",
  "Vulkan · WebGPU · Slang / WGSL",
  "HTTP/1.1 · kqueue · CGI · WebSocket",
  "DICOM · NIfTI · 볼륨 렌더링"
]

[[education]]
degree = "강원대학교"
school = "컴퓨터정보통신공학과"
period = "2015.03 ~ 2021.08"
gpa = "평점평균: 4.11 / 4.5"

[[education]]
degree = "42 Seoul"
school = "소프트웨어 개발 교육"
period = "2023.10 입과 · 2025.08 공통과정 완료"
+++
