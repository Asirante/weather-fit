# data_pipeline/

기상 **예보·자외선·대기 통계** 수집 Lambda 모음. 전국 격자/측정소를 **Step Functions Distributed Map**으로 병렬 수집해 S3/DynamoDB에 적재합니다.

> ℹ️ AI 배치 추론은 이 폴더가 아니라 [`ai_pipeline/`](../ai_pipeline/)에서 합니다. 실시간 실황/대기질 수집은 [`real_time/`](../real_time/)에 있습니다.

---

## 구성 (실제)

```
data_pipeline/
├── lambda_function.py            # dataAPI: 대기 통계(시도/시군구 평균) + 초미세먼지 주간예보 → S3
├── airStatsAPI.py                # 에어코리아 통계 호출 (스레드풀)
├── airInfoAPI.py                 # 에어코리아 주간예보 호출
├── forecast_batches/             # 격자 분할 → 매니페스트(S3) 생성
├── forecast_worker/              # 초단기예보(getUltraSrtFcst) → forecast-cache + S3 (TTL: expireAt)
├── forecast_merge/               # 배치 CSV 병합 → S3
├── weather_batches/              # 자외선(getUVIdxV5)·대기확산(getAirDiffusionIdxV5) 수집 → S3
├── weather_merge/                # 배치 CSV 병합 → S3
└── README.md
```

각 하위 폴더의 `lambda_function.py`가 개별 Lambda로 배포됩니다.

---

## 수집 파이프라인 (Step Functions Distributed Map)

전국을 단일 Lambda로 돌리면 너무 오래 걸려, **매니페스트로 배치를 나누고 Distributed Map(maxConcurrency)** 으로 병렬 처리합니다.

```
예보(forecast) 상태머신:
  forecast-data-batches  (격자 dedup → 배치 매니페스트 S3 저장)
    → Distributed Map (maxConcurrency=5)
        → forecast-data-worker (getUltraSrtFcst 호출 → forecast-cache 적재 + 배치 CSV)
    → forecast-data-merge (배치 CSV 병합 → S3)

부가배치(weather) 상태머신:
  GenerateRunId(배치 정의)
    → Map (maxConcurrency=3)
        → weather-data-batches (자외선·대기확산 수집 → S3)
    → weather-data-merge (병합)
    → dataAPI (대기 통계 + 주간예보 → S3)
```

> 상태머신 정의(ASL)와 EventBridge 스케줄은 **콘솔에서 관리**되며 레포에는 포함되지 않습니다.
>
> **수집 주기(EventBridge Scheduler, 데이터 특성별 차등):** 실황·미세먼지 `1시간` / 초단기예보 `3시간` / 자외선·대기확산 `6시간`. 각 람다는 실행 시점 기준으로 base_time을 계산하므로 주기만 바꾸면 됩니다(코드 변경 불필요).

---

## 사용 외부 API (공공데이터포털)

| API | 호출 위치 | 적재 |
|-----|----------|------|
| 기상청 초단기예보 `getUltraSrtFcst` | `forecast_worker` | forecast-cache (+S3) |
| 생활기상지수 자외선 `getUVIdxV5` / 대기확산 `getAirDiffusionIdxV5` (발표시각 기준 3시간 단위 h0~h75 예측값) | `weather_batches` | S3 |
| 에어코리아 시도/시군구 평균 | `airStatsAPI` | S3 |
| 에어코리아 초미세먼지 주간예보 `getMinuDustWeekFrcstDspth` | `airInfoAPI` | S3 |

인증키 env: `WEATHER_API_KEY`(기상청·생활지수·에어코리아 공통), 베이스 URL: `FORECAST_API_URL`/`WEATHER_API_URL`/`AIR_STATS_API_URL`/`AIR_INFO_API_URL`.

---

## forecast-cache 적재 규칙
- 키: `region_code`(PK) + `forecast_key = fcstDate#fcstTime#category`(SK).
- 같은 대상시각+카테고리는 덮어쓰기되지만 **지나간 대상시각 항목은 누적**되므로, 각 항목에 **`expireAt`(대상시각+12h) TTL**을 부여해 자동 삭제합니다.
  → DynamoDB 테이블에서 **TTL 속성 `expireAt` 활성화 필요**(콘솔).
- 서빙(`backend`)은 조회 시에도 "가장 최근 발표분만" 사용해 누적 영향을 한 번 더 차단합니다.

---

## 로컬 실행

```bash
cd data_pipeline
python -c "from forecast_worker.lambda_function import lambda_handler; print(lambda_handler({'batch_id':0,'locations':[{'nx':60,'ny':127,'regions':[]}]}, None))"
```
> 실제 AWS 리소스 접근 테스트는 dev 자격증명만 사용하고 **prod 리소스 접근 금지**.

---

## 배포

> ⚠️ SAM CLI 사용 불가. `develop`/`main`의 `data_pipeline/**` 변경 → `deploy-all-lambdas.yml`이 변경된 하위 폴더를 감지해 해당 Lambda에 `update-function-code`로 배포합니다.

스케줄/상태머신/환경변수 변경은 **AWS 콘솔(us-east-1)** 에서 직접.

---

## 알려진 개선 포인트
- `forecast_worker`는 배치 내 API를 **순차 호출**합니다(`weather_batches`는 스레드풀). 공공 API 호출 제한(차단) 회피를 위한 **의도적 선택**으로, 대량 처리 시 느릴 수 있습니다.
- 격자 dedup·배치 분할 로직이 여러 파일에 유사하게 존재 → 공용 모듈로 추출 여지.

> ✅ 해결됨: `airStatsAPI`/`airInfoAPI` **재시도**(`fetch_json_with_retry`, 3회) 추가 · merge/UV 탐색 `list_objects_v2` **페이지네이션**(`get_paginator`) 적용.
