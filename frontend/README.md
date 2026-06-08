# frontend/

Vue 3 기반 SPA + **PWA**. 빌드 결과물(`dist/`)을 S3(`inhatc-team2-3-frontend`)에 업로드해 정적 호스팅합니다.

> ⚠️ 빌드 도구는 **Vue CLI(webpack)** 입니다. (Vite 아님) 상태관리는 Pinia 없이 `src/stores/`의 경량 `ref` 모듈을 씁니다.

---

## 기술 스택

| 기술 | 버전 | 용도 |
|------|------|------|
| Vue.js | 3.x | SPA 프레임워크 |
| Vue CLI (`@vue/cli-service`) | 5.x | 빌드/개발 서버 (webpack) |
| vue-router | 4.x | 라우팅 (`/`, `/search`) |
| Vitest | 2.x | 단위 테스트 |
| Geolocation API | – | 현재 위치 수집 |
| Kakao Map API | – | 지역 검색·지도 시각화 |
| Service Worker / manifest | – | PWA(홈 화면 설치·오프라인 캐시) |

---

## 로컬 실행

```bash
npm ci
npm run serve     # 개발 서버 (기본 http://localhost:8080)
```

카카오맵을 쓰려면 빌드/서버 실행 시 `VUE_APP_KAKAO_API_KEY`가 필요합니다.
로컬에선 `frontend/.env` 파일에 넣어 둡니다(이 파일은 `.gitignore` 처리됨):

```
VUE_APP_KAKAO_API_KEY=카카오_JavaScript_키
```

> 배포(CI)에서는 GitHub Secret `KAKAO_API_KEY`가 빌드 시 주입됩니다.
> 미설정 시 지도가 빈 화면이 됩니다. 카카오 개발자 콘솔에서 **도메인 제한**도 등록하세요(localhost + 배포 도메인).

---

## 주요 스크립트

```bash
npm run serve       # 개발 서버
npm run build       # 프로덕션 빌드 (dist/)
npm run lint        # ESLint
npm run test:unit   # Vitest 단위 테스트
```

---

## 폴더 구조 (실제)

```
frontend/
├── public/
│   ├── index.html               # 메타/PWA 링크/카카오 SDK 스크립트
│   ├── manifest.webmanifest     # PWA 매니페스트
│   ├── service-worker.js        # 직접 작성한 SW (캐싱 전략)
│   ├── icons/                   # PWA 아이콘 (192/512/maskable/apple-touch)
│   └── *.json                   # 행정동 GeoJSON 등
├── src/
│   ├── components/
│   │   ├── WeatherFitHome.vue   # 홈: 현재날씨 + OOTD + 인터랙티브 마스크 + 시간별 예보(상세 패널)
│   │   └── WeatherFitSearch.vue # 지역 검색 + 카카오 지도
│   ├── stores/
│   │   ├── useWeather.js        # 날씨/추천 fetch + 매핑 (ref 기반 전역 상태)
│   │   └── usehistory.js        # 최근 검색 기록 (localStorage)
│   ├── utils/weather.js         # 아이콘/라벨 등 순수 유틸 (테스트 대상)
│   ├── router/index.js          # 라우트: / , /search
│   ├── App.vue                  # 헤더/푸터/전역 스타일
│   └── main.js                  # 앱 부트 + 서비스워커 등록
├── tests/unit/                  # Vitest 테스트
├── vue.config.js
├── vitest.config.js
└── package.json
```

---

## 동작 메모

### 백엔드 연동
`src/stores/useWeather.js`가 **Lambda Function URL을 직접 호출**합니다(`/weather`, `/recommend` 병렬).
타임아웃(AbortController) + 지수 백오프 재시도 + 최신 요청만 반영(레이스 방지)이 적용되어 있습니다.
응답 필드(`feelsLike`, `uv`, `forecastTimes`, `acc` 등)는 백엔드 변경에도 안전하도록 방어적으로 매핑합니다.

### 위치
Geolocation은 **HTTPS(또는 localhost)** 에서만 동작합니다. 권한 거부 시 최근 검색 → 기본 지역 순으로 폴백합니다.

### PWA
- 서비스워커: 같은 출처 정적자산은 SWR, 페이지 내비게이션은 Network-First→오프라인 시 캐시, **API/카카오 SDK는 캐시하지 않음**(항상 최신).
- 설치: 안드로이드 Chrome ⋮메뉴 "앱 설치", 아이폰 **Safari** 공유→"홈 화면에 추가". **시크릿 모드에선 설치 불가.**
- 서비스워커는 **HTTPS** 필요.

---

## 배포

`develop`/`main` 브랜치의 `frontend/**` 변경 → GitHub Actions(`deploy-frontend.yml`)가 빌드 후 S3에 동기화합니다.

```bash
# 수동 배포 시
npm run build
aws s3 sync dist/ s3://inhatc-team2-3-frontend --delete
```

> 참고: 현재 워크플로우에는 **CloudFront 무효화 단계가 없습니다.** CDN을 앞단에 둔다면 배포 후 캐시 무효화가 필요합니다.
