# data_pipeline/

날씨 데이터 수집, 저장, 변환(ETL)을 담당하는 서버리스 파이프라인.
EventBridge로 스케줄링되며, Lambda가 데이터를 수집하고, Glue가 분석에 최적화된 형태로 변환합니다.

---

## 기술 스택

| 기술 | 용도 |
|------|------|
| Amazon EventBridge | 데이터 수집 스케줄링 (cron) |
| AWS Lambda | 데이터 수집 실행 |
| Amazon DynamoDB | 실시간 데이터 저장 |
| Amazon S3 | 원본 데이터 아카이빙 |
| AWS Glue | CSV → Parquet 변환 (ETL) |
| Amazon Athena | S3 데이터 SQL 분석 |

---

## 데이터 흐름

```
EventBridge (매 시간)
  → Lambda (기상청 API 호출)
  → DynamoDB (실시간 조회용) + S3 (원본 CSV 아카이빙)

S3 (CSV 원본)
  → Glue (Parquet 변환)
  → S3 (Parquet 저장)
  → Athena (SQL 분석)
```

---

## 폴더 구조

```
data_pipeline/
├── lambdas/
│   ├── weather_collector/
│   │   ├── handler.py       # 수집 Lambda 핸들러
│   │   └── requirements.txt
│   └── ...
├── glue_jobs/
│   └── csv_to_parquet.py    # Glue ETL 스크립트
├── template.yaml             # SAM 템플릿 (파이프라인용)
├── .env.example
└── README.md
```

---

## 환경 변수

| 변수명 | 설명 | 사용 위치 |
|--------|------|----------|
| `WEATHER_API_KEY` | 기상청 API 인증키 | 수집 Lambda |
| `DYNAMODB_TABLE_NAME` | 실시간 데이터 테이블 | 수집 Lambda |
| `S3_RAW_BUCKET` | 원본 CSV 저장 버킷 | 수집 Lambda |
| `S3_PARQUET_BUCKET` | 변환된 Parquet 저장 버킷 | Glue Job |

Lambda 환경 변수는 SAM `template.yaml`에서 정의하며, 배포 환경(dev/prod)별로 분리되어 있습니다.

---

## 로컬 개발 및 테스트

### Lambda 함수 로컬 실행

```bash
cd data_pipeline
sam build
sam local invoke WeatherCollectorFunction --event events/test_event.json
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
| **Glue** | DPU-시간 (프리 티어 없음) | 작업 최적화, 불필요한 실행 제거 |
| **Athena** | 스캔 데이터 TB당 $5 (프리 티어 없음) | Parquet 사용 시 최대 95% 절감 |
| DynamoDB | On-Demand R/W (25GB까지 무료) | 불필요한 스캔 쿼리 지양 |
| S3 | 저장량 + 요청 수 | 수명 주기 정책으로 오래된 데이터 아카이빙 |

Glue Job이나 Athena 쿼리를 새로 추가하거나 변경할 때는 예상 비용을 팀에 공유해 주세요.

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
