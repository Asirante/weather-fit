# data_pipeline/

기상 데이터 수집과 AI 배치 추론을 담당하는 서버리스 파이프라인.
전날 자정에 기상청 예보를 수집하고, 유니크 기상 패턴을 추출하여 Bedrock 배치 추론으로 AI 답변을 사전 캐싱합니다.

---

## 기술 스택

| 기술 | 용도 |
|------|------|
| Amazon EventBridge | 데이터 수집 및 배치 추론 스케줄링 |
| AWS Lambda | 데이터 수집 + 배치 추론 실행 |
| Amazon Bedrock | AI 추천 생성 (Claude 3.5 Haiku, 배치 추론) |
| Amazon DynamoDB | AI 답변 캐싱 (기상 조건 = PK, TTL 영구) |
| Amazon S3 | 원본 데이터 아카이빙 |
| AWS Glue | CSV → Parquet 변환 (ETL) |
| Amazon Athena | S3 데이터 SQL 분석 |

---

## 파이프라인 흐름

```
[매일 자정 - EventBridge 트리거]

1단계: 기상 데이터 수집
   EventBridge → Lambda (기상청 예보 API 호출)
     → 전국 예보 데이터 수집
     → S3에 원본 저장 + DynamoDB에 실시간 데이터 적재

2단계: AI 배치 추론
   수집된 예보에서 유니크 기상 패턴 추출 (중복 제거)
     → Bedrock 배치 추론 (수십 개 패턴을 한 번에 처리)
     → DynamoDB에 AI 답변 캐싱 (기상 조건 = PK, TTL 영구)

3단계: 분석용 변환 (별도 스케줄)
   S3 (CSV 원본) → Glue (Parquet 변환) → Athena (분석)
```

### 유니크 패턴 추출 예시

```
전국 예보 300건 수집
  → 기온/습도/강수확률/미세먼지 조합으로 패턴화
  → 중복 제거 후 유니크 패턴 약 30~50개
  → 이미 DynamoDB에 캐싱된 패턴 제외
  → 신규 패턴만 Bedrock 배치 추론 요청
```

---

## 폴더 구조

```
data_pipeline/
├── lambdas/
│   ├── weather_collector/
│   │   ├── handler.py         # 기상 데이터 수집 핸들러
│   │   └── requirements.txt
│   ├── batch_inference/
│   │   ├── handler.py         # 유니크 패턴 추출 + Bedrock 배치 추론
│   │   ├── prompts.py         # 배치 추론용 프롬프트 관리
│   │   └── requirements.txt
│   └── ...
├── glue_jobs/
│   └── csv_to_parquet.py      # Glue ETL 스크립트
├── template.yaml               # SAM 템플릿 (파이프라인용)
├── .env.example
└── README.md
```

---

## 환경 변수

| 변수명 | 설명 | 사용 위치 |
|--------|------|----------|
| `WEATHER_API_KEY` | 기상청 API 인증키 | 수집 Lambda |
| `DYNAMODB_TABLE_NAME` | 실시간 기상 데이터 테이블 | 수집 Lambda |
| `DYNAMODB_CACHE_TABLE_NAME` | AI 답변 캐시 테이블 | 배치 추론 Lambda |
| `BEDROCK_MODEL_ID` | Bedrock 모델 ID | 배치 추론 Lambda |
| `S3_RAW_BUCKET` | 원본 CSV 저장 버킷 | 수집 Lambda |
| `S3_PARQUET_BUCKET` | 변환된 Parquet 저장 버킷 | Glue Job |

Lambda 환경 변수는 SAM `template.yaml`에서 정의하며, 배포 환경(dev/prod)별로 분리되어 있습니다.

---

## 로컬 개발 및 테스트

### Lambda 함수 로컬 실행

```bash
cd data_pipeline
sam build

# 수집 Lambda 테스트
sam local invoke WeatherCollectorFunction --event events/test_collect.json

# 배치 추론 Lambda 테스트 (주의: Bedrock 호출 발생, 토큰 과금)
sam local invoke BatchInferenceFunction --event events/test_batch.json
```

### Glue Job 로컬 테스트

Glue Job은 AWS 환경에서만 실행됩니다. 로컬에서는 동일한 로직을 pandas로 테스트할 수 있습니다.

```bash
pip install pandas pyarrow
python glue_jobs/csv_to_parquet.py --local
```

---

## 배포

`develop` 또는 `main` 브랜치에 Push하면 GitHub Actions가 SAM 빌드 → 배포를 수행합니다. 수동 배포:

```bash
sam build
sam deploy --config-env dev
```

---

## 비용 주의사항

| 서비스 | 과금 기준 | 절감 방법 |
|--------|----------|----------|
| **Bedrock** | 입출력 토큰 (프리 티어 없음) | 배치 추론으로 일괄 처리, 유니크 패턴만 추론 |
| **Glue** | DPU-시간 (프리 티어 없음) | 작업 최적화, 불필요한 실행 제거 |
| **Athena** | 스캔 데이터 TB당 $5 (프리 티어 없음) | Parquet 사용 시 최대 95% 절감 |
| DynamoDB | On-Demand R/W (25GB까지 무료) | 불필요한 스캔 쿼리 지양 |
| S3 | 저장량 + 요청 수 | 수명 주기 정책으로 오래된 데이터 아카이빙 |

### Bedrock 비용 관리 핵심

- **배치 추론**: 유니크 패턴만 추출하여 일괄 처리 → 중복 호출 제거
- **DynamoDB 캐싱**: TTL 영구 설정으로 한 번 생성된 답변은 재사용
- **기존 캐시 제외**: 배치 추론 전 DynamoDB에 이미 있는 패턴은 건너뜀
- 프롬프트 변경이나 배치 추론 로직 수정 시 예상 비용을 팀에 공유해 주세요

---

## Athena 테이블 관리

Athena 테이블 DDL은 `infra/athena_ddl/`에서 SQL 파일로 버전 관리합니다. 콘솔에서 직접 DDL을 실행하지 말고, SQL 파일을 먼저 커밋한 뒤 실행하세요.

```sql
-- infra/athena_ddl/weather_parquet.sql
CREATE EXTERNAL TABLE weather_parquet (
  ...
)
STORED AS PARQUET
LOCATION 's3://<parquet-bucket>/weather/';
```

---

## 개발 시 참고사항

### DynamoDB 캐시 테이블 스키마

캐시 테이블의 파티션 키는 기상 조건 조합(기온, 습도, 강수확률 등)으로 구성됩니다. 키 설계를 변경하면 기존 캐시가 모두 무효화되므로, 변경 시 백엔드 팀과 반드시 협의하세요.

### 프롬프트 일관성

배치 추론(`data_pipeline/`)과 실시간 호출(`backend/`)에서 사용하는 시스템 프롬프트가 동일해야 합니다. 프롬프트를 수정할 때는 양쪽 모두 업데이트하세요. 공통 프롬프트를 별도 모듈로 분리하는 것을 권장합니다.
