# frontend/

Vue.js(Vite) 기반 프론트엔드. 빌드 결과물은 S3에 업로드되어 CloudFront를 통해 서빙됩니다.

---

## 기술 스택

| 기술 | 버전 | 용도 |
|------|------|------|
| Vue.js | 3.x | SPA 프레임워크 |
| Vite | 5.x | 빌드 도구 |
| Geolocation API | - | 사용자 GPS 위치 수집 |
| Kakao Map API | - | 지도 시각화 |

---

## 로컬 실행

```bash
npm ci
cp .env.example .env.local
npm run dev
```

`http://localhost:5173`에서 확인할 수 있습니다.

---

## 환경 변수

`.env.example`을 `.env.local`로 복사한 뒤 값을 채워주세요.

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `VITE_API_BASE_URL` | 백엔드 API 주소 | `http://localhost:8000` (로컬) |
| `VITE_KAKAO_MAP_API_KEY` | 카카오 맵 JavaScript 키 | 카카오 개발자 콘솔에서 발급 |

> 로컬 개발 시 `VITE_API_BASE_URL`은 백엔드 로컬 주소를, dev/prod 배포 시에는 각 환경의 Lambda Function URL을 사용합니다.

---

## 주요 스크립트

```bash
npm run dev       # 로컬 개발 서버
npm run build     # 프로덕션 빌드 (dist/ 생성)
npm run lint      # ESLint 검사
npm run preview   # 빌드 결과물 로컬 미리보기
```

---

## 폴더 구조

```
frontend/
├── public/              # 정적 파일 (favicon 등)
├── src/
│   ├── api/             # API 호출 모듈
│   ├── assets/          # 이미지, 스타일 등
│   ├── components/      # 재사용 컴포넌트
│   ├── views/           # 페이지 단위 컴포넌트
│   ├── router/          # Vue Router 설정
│   ├── stores/          # 상태 관리 (Pinia 등)
│   ├── utils/           # 유틸리티 함수
│   ├── App.vue
│   └── main.js
├── .env.example
├── package.json
├── vite.config.js
└── README.md
```

---

## 개발 시 참고사항

### Geolocation API

사용자 위치 권한을 요청하므로 **HTTPS 환경**(또는 localhost)에서만 동작합니다. 위치 권한이 거부될 경우의 폴백 처리(기본 도시 선택 등)를 반드시 구현해야 합니다.

### 카카오 맵 API

카카오 개발자 콘솔에서 앱을 등록한 뒤 JavaScript 키를 발급받아야 합니다. 도메인 제한이 설정되어 있으므로 `localhost`와 배포 도메인을 모두 등록해 주세요.

### 배포

`develop` 또는 `main` 브랜치에 Push하면 GitHub Actions가 자동으로 빌드 → S3 업로드 → CloudFront 캐시 무효화를 수행합니다. 수동 배포가 필요한 경우:

```bash
npm run build
aws s3 sync dist/ s3://<bucket-name> --delete
aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"
```
