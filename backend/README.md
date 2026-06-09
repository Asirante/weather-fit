# backend/

옷차림 추천·날씨 **서빙 API**. 단일 AWS Lambda(`inhatc-team2-1-recommendAPI`)이며 **Lambda Function URL**로 노출됩니다.

> ⚠️ FastAPI/Mangum/Bedrock 실시간 호출을 쓰지 않습니다. **단일 `lambda_function.py`** 가 경로(`rawPath`)로 분기하고, **DynamoDB 조회만** 합니다. 추천은 `ai_pipeline`이 미리 생성해 `recommend-cache`에 넣어둡니다.

---

## 구성

```
backend/
├── lambda_function.py   # 핸들러: /weather, /recommend 분기 + 패턴키(SK) 생성 + 조회
├── mapping.py           # region_to_code(지역명→코드), gu_to_station(지역→측정소)
├── docker-compose.yml   # 로컬 DynamoDB Local (선택)
├── env.json             # SAM local용 더미 env (실제 시크릿 아님)
└── README.md
```

---

## 엔드포인트 (Lambda Function URL)

| 경로 | 파라미터 | 동작 |
|------|---------|------|
| `GET /weather` | `region`(지역명) 또는 `region_code` | weather-cache(실황)·forecast-cache(예보)·air-cache(대기질) 조회 → 현재/시간별 응답 |
| `GET /recommend` | 동일 | 기상으로 패턴키(SK) 생성 → recommend-cache 조회 |

### `/weather` 주요 응답 필드
```json
{
  "region_code": "1147062000", "region_name": "서울특별시 양천구",
  "baseDate": "20260607", "baseTime": "1800",
  "temp": 26.1, "feelsLike": 26.2,
  "tempForecast": [27, 26, 25, ...], "feelsLikeForecast": [...],
  "forecastTimes": ["202606071900", ...],
  "rain": ["강수없음", ...], "sky": ["흐림", ...],
  "uv": 0.0, "uvForecast": [3.0, 5.0, ...], "o3": 0.038,
  "pm10": 32.0, "pm10Grade": "2", "pm25": 15.0, "pm25Grade": "1"
}
```
- **체감온도**(`feelsLike`)는 캐시의 풍속(WSD)/습도(REH)로 기상청 공식(저온=풍속냉각, 고온=습도식) 계산.
- **시간별 예보**는 "가장 최근 발표(baseDate+baseTime) 기준"만 사용하고 실제 예보시각(`forecastTimes`)을 함께 반환(누적 잔재 제거).
- **자외선**(V5)은 발표시각 기준 3시간 단위(`h0/h3/.../h75`)이므로, hN의 실제시각(=발표시각+N시간)으로 정렬해 예보 시각별 값을 `uvForecast`로 반환(프론트 시간별 상세에 표시). `/recommend` 패턴키의 `uv_level`은 **현재 시각 기준 now~+6h 최댓값**으로 산정.

### `/recommend` 패턴키(SK)
`temp:{zone}|diff:{lvl}|rain:{lvl}|pm:{grade}|wind:{lvl}|uv:{lvl}|pty:{type}` 형식.
이 임계값/enum은 **`ai_pipeline/pattern_domains.py`와 정확히 일치해야** 캐시 히트됩니다(현재 일치).

---

## 의존 테이블
`recommend-cache`(추천) · `weather-cache`(실황) · `air-cache`(대기질) · `forecast-cache`(예보).
키 스키마는 루트 README의 "데이터 저장소" 표 참고.

---

## 로컬 실행 (선택)

DynamoDB Local로 핸들러를 단독 실행할 수 있습니다.

```bash
cd backend
docker compose up -d           # DynamoDB Local
# AWS_SAM_LOCAL=true 면 lambda_function.py가 로컬 DynamoDB로 접속
python -c "import lambda_function as f; print(f.lambda_handler({'rawPath':'/weather','rawQueryString':'region_code=1147062000'}, None))"
```

> `env.json`의 `local` 자격증명은 DynamoDB Local용 더미입니다(실제 키 아님).

---

## 배포

> ⚠️ **SAM CLI 사용 불가**(학교 계정 비용관리 태그 정책). 배포는 GitHub Actions가 `update-function-code`로 수행합니다.

`develop`/`main`의 `backend/**` 변경 → `deploy-all-lambdas.yml`이 자동 배포:

```bash
# 워크플로우 동작(요지)
cd backend
zip -r ../deploy.zip lambda_function.py mapping.py ...   # 최상위 파일만
aws lambda update-function-code \
  --function-name inhatc-team2-1-recommendAPI \
  --zip-file fileb://../deploy.zip
```

Lambda 환경변수/트리거/메모리 등 **설정 변경은 AWS 콘솔(us-east-1)** 에서 직접 합니다.

---

## 참고/주의

- **CORS**: Function URL 레벨에서 설정됩니다(코드엔 헤더 없음). 운영 도메인으로 제한 권장.
- **입력**: `region`/`region_code`는 매핑 딕셔너리 조회에만 쓰여 인젝션 위험은 낮습니다.
- **에러**: 내부 오류는 일반 메시지의 500으로 반환(상세 비노출).
- 추천 임계값을 바꾸면 `ai_pipeline`도 함께 바꿔 **재생성**해야 합니다(아니면 캐시 미스→404).
