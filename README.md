# WeatherFit ☀️🧥

현재 위치와 날씨·미세먼지에 맞춰 **오늘의 옷차림(OOTD)** 을 추천해주는 서버리스 웹 서비스입니다.
사용자는 별도 가입 없이 현재 위치(또는 지역 검색)의 날씨·대기질·시간별 예보와 함께,
기상 패턴에 맞춘 AI 옷차림 추천(상·하의, 소지품, 마스크)을 바로 확인할 수 있습니다.

> 인하공전 2팀 프로젝트 · 전 구간 AWS 서버리스 아키텍처

---

## 아키텍처 한눈에 보기

```
[수집/추론 파이프라인]                         [서빙]

기상청/에어코리아 공공 API                       사용자 브라우저 (PWA)
   │  (Step Functions Distributed Map)            │
   ▼                                              ▼
 수집 Lambda들 ──► S3(raw) / DynamoDB        Vue SPA (S3 정적 호스팅)
   │  실황·예보·대기질·자외선                      │  fetch
   ▼                                              ▼
 AI 배치(Bedrock) ──► recommend-cache        recommendAPI Lambda (Function URL)
   (27,000 패턴 사전 생성)                        │  DynamoDB 조회만 (실시간 추론 X)
                                                  ▼
                                          weather/air/forecast/recommend-cache
```

- **추천은 미리 생성(배치)** 되어 `recommend-cache`에 저장됩니다. 서빙 Lambda는 **DynamoDB 조회만** 하므로 빠르고 저렴합니다(요청 시 Bedrock 호출 없음).
- **수집은 Step Functions(Distributed Map)** 으로 전국 격자/측정소를 병렬 처리합니다.

---

## 모듈 구성

| 폴더 | 역할 | 런타임/스택 | 배포 |
|------|------|------------|------|
| [`frontend/`](frontend/) | Vue 3 SPA + PWA (날씨·OOTD·지역검색) | Vue CLI(webpack), Vitest | `deploy-frontend.yml` → S3 |
| [`backend/`](backend/) | 추천/날씨 서빙 API (단일 Lambda) | Python, Lambda Function URL | `deploy-all-lambdas.yml` |
| [`data_pipeline/`](data_pipeline/) | 예보·대기질·자외선 수집 Lambda들 | Python, Step Functions | `deploy-all-lambdas.yml` |
| [`real_time/`](real_time/) | 초단기실황·대기질 실시간 수집 | Python, Step Functions | `deploy-all-lambdas.yml` |
| [`ai_pipeline/`](ai_pipeline/) | Bedrock 배치로 27,000 패턴 추천 생성 | Python, Bedrock Batch | `deploy-all-lambdas.yml` |
| [`infra/`](infra/) | 공통 리소스(버킷/테이블) 참고 템플릿·문서 | CloudFormation(참고용) | 콘솔 수동 |

---

## 데이터 저장소 (DynamoDB)

| 테이블 | 키 | 내용 | 쓰는 곳 | TTL |
|--------|----|------|---------|-----|
| `inhatc-team2-5-weather-cache` | `region_code`(PK) + `category`(SK) | 초단기실황(기온/습도/풍속)·자외선 | `real_time/weather_worker` | – |
| `inhatc-team2-5-air-cache` | `stationKey`(PK) | 실시간 대기오염(PM10/PM2.5/O3…) | `real_time`(air) | – |
| `inhatc-team2-5-forecast-cache` | `region_code`(PK) + `forecast_key`(SK) | 초단기예보(시간별 기온/강수/하늘) | `data_pipeline/forecast_worker` | `expireAt` |
| `inhatc-team2-1-recommend-cache` | `PK="weather_pattern"` + `SK`(패턴키) | AI 옷차림 추천(사전 생성) | `ai_pipeline/batch_save` | 영구 |

> 표의 SK는 코드 기준입니다. 실제 리소스는 콘솔에서 관리됩니다(아래 "배포/인프라" 참고).

서빙 Lambda는 사용자 지역코드로 위 4개 테이블을 조회해 응답을 조립합니다.

---

## 서빙 API (Lambda Function URL)

| 경로 | 설명 |
|------|------|
| `GET /weather?region=<지역명>` 또는 `?region_code=<코드>` | 현재 기온·체감·미세먼지 + 시간별 예보(`tempForecast`/`forecastTimes`/`rain`/`sky`/`uvForecast` — 자외선은 시각별) |
| `GET /recommend?region=...` | 기상 패턴키(SK)로 `recommend-cache`에서 옷차림 추천 조회 |

응답 예시는 `backend/README.md` 참고.

---

## 로컬 개발

```bash
# 프론트엔드
cd frontend
npm ci
npm run serve        # 개발 서버
npm run test:unit    # 단위 테스트(Vitest)
npm run build        # 프로덕션 빌드(dist/)
```

> 프론트는 카카오맵 키가 필요합니다. `frontend/README.md`의 환경변수 참고.
> 백엔드/파이프라인 Lambda 로컬 실행은 각 모듈 README 참고.

---

## 배포 / 인프라

- **코드 배포는 GitHub Actions가 자동 수행**합니다.
  - 프론트: `frontend/**` 변경 → 빌드 후 `s3://inhatc-team2-3-frontend` 동기화
  - 람다: `backend|data_pipeline|real_time|ai_pipeline/**` 변경 → `aws lambda update-function-code`
- **인프라(버킷/테이블/Step Functions/스케줄)는 AWS 콘솔에서 수동 관리**합니다.
  - 학교 계정의 비용관리 태그 정책 때문에 `sam deploy`를 쓸 수 없어, SAM/CFN 템플릿은 **참고용**입니다. (`infra/README.md` 참고)

### 운영 체크리스트
- GitHub Secret `KAKAO_API_KEY` 등록 (없으면 배포 사이트 지도 미표시)
- `forecast-cache` 테이블 TTL 속성 `expireAt` 활성화
- 수집 Step Functions의 EventBridge 스케줄 활성 상태 확인 (멈추면 화면에 옛 데이터 노출)
  - 차등 주기: 실황·미세먼지 `1시간` / 초단기예보 `3시간` / 자외선·대기확산 `6시간`

---

## 기술 스택 요약

`Vue 3` · `PWA` · `AWS Lambda(Function URL)` · `DynamoDB` · `S3` · `Step Functions(Distributed Map)` · `EventBridge` · `Amazon Bedrock(Claude Haiku, Batch)` · `기상청/에어코리아 공공 API` · `GitHub Actions(OIDC)`
