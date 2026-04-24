# infra/

프로젝트의 AWS 인프라를 코드로 정의하고 관리하는 폴더입니다 (Infrastructure as Code).
SAM/CloudFormation 템플릿과 Athena DDL 스크립트를 포함합니다.

---

## 폴더 구조

```
infra/
├── template.yaml          # 공통 인프라 참고용 템플릿 (S3 버킷, DynamoDB 등)
├── samconfig.toml         # SAM 배포 설정 (참고용 - 실제 배포에 사용하지 않음)
├── athena_ddl/
│   └── weather_parquet.sql
└── README.md
```

---

## ⚠️ SAM CLI 사용 불가 안내

> 학교 AWS 계정은 **비용관리 태그(Cost Allocation Tag)** 기반으로 리소스 CRUD 권한을 제어합니다.
> Lambda 생성 직후 태그가 붙기 전, SAM이 후속 작업(코드 배포, 트리거 연결 등)을 시도하면 **권한 오류(AccessDeniedException)**가 발생합니다.
>
> 따라서 **`sam build` / `sam deploy` 명령어는 우리 환경에서 사용할 수 없습니다.**
> `template.yaml`과 `samconfig.toml`은 인프라 구조 파악을 위한 **참고용 문서**로만 보존합니다.

---

## 핵심 원칙

1. **모든 인프라는 콘솔에서 수동 관리합니다.** S3 버킷, DynamoDB 테이블, Lambda 함수, EventBridge 트리거 등 모든 리소스는 AWS 콘솔(us-east-1 리전)에서 직접 생성/수정합니다.
2. **Lambda 코드만 GitHub Actions가 자동 배포합니다.** `aws lambda update-function-code` 명령어를 통해 코드만 업데이트합니다.
3. **Athena DDL은 SQL 파일로 버전 관리합니다.** 콘솔에서 직접 DDL을 실행하지 말고, SQL 파일을 먼저 커밋한 뒤 실행하세요.

---

## 현재 생성 완료된 리소스

### S3 버킷

| 버킷명 | 용도 |
|--------|------|
| `inhatc-team2-3-frontend` | 프론트엔드 정적 파일 호스팅 |
| `inhatc-team2-5-raw-data` | 원본 수집 데이터 저장 |
| `inhatc-team2-4-parquet-data` | 분석용 Parquet 데이터 저장 |

### DynamoDB 테이블

| 테이블명 | 파티션 키 | 용도 | TTL |
|--------|---------|------|-----|
| `inhatc-team2-5-weather-cache` | `region_code` (S) | 실시간 날씨 상태 | 설정 가능 |
| `inhatc-team2-5-air-cache` | `stationKey` (S) | 실시간 대기질 상태 | 설정 가능 |
| `inhatc-team2-1-recommend-cache` | `weather_pattern` (S) | AI 추천 답변 캐싱 | 영구 (TTL 없음) |

### Lambda 함수

| 함수명 | 트리거 | 담당 |
|--------|--------|------|
| `inhatc-team2-1-recommendAPI` | Function URL | 백엔드(고원영) |
| `inhatc-team2-5-dataAPI` | EventBridge rate(1 hour) | 데이터(김호건) |
| `inhatc-team2-5-real-time-dataAPI` | EventBridge rate(30 minutes) | 데이터(김호건) |

---

## 인프라 변경이 필요한 경우

SAM CLI를 사용할 수 없으므로 모든 인프라 변경은 **AWS 콘솔에서 직접** 진행합니다.

```
AWS 콘솔 접속 → 리전 us-east-1 확인 → 해당 서비스 이동 → 직접 수정
```

변경 후에는 반드시 `template.yaml`도 동일하게 업데이트하여 팀원들이 현재 인프라 구조를 파악할 수 있도록 합니다.

> ⚠️ **prod 환경 인프라 변경**은 인프라 담당자가 진행합니다. 다른 역할의 팀원은 dev 환경까지만 직접 변경하세요.

---

## DynamoDB 테이블 설계

AI 캐시 테이블의 키 설계 변경은 기존 캐시 전체 무효화를 의미하므로, 백엔드/데이터 팀과 반드시 협의 후 진행하세요.

---

## Athena DDL 관리

Athena 테이블 생성/변경 SQL은 `athena_ddl/` 폴더에 파일로 관리합니다.

```bash
# 새 테이블 생성 시
# 1. SQL 파일 작성 후 커밋
# 2. Athena 콘솔 또는 AWS CLI로 실행
aws athena start-query-execution \
  --query-string file://athena_ddl/weather_parquet.sql \
  --result-configuration OutputLocation=s3://<query-results-bucket>/
```

스키마 변경이 필요하면 SQL 파일을 먼저 수정하고, PR을 올린 뒤 머지 후 실행하세요.

---

## 작업 시 주의사항

- IAM 권한이나 OIDC Trust Policy 변경은 반드시 인프라 담당자가 리뷰 후 적용합니다.
- Lambda에 Bedrock 호출 권한(`bedrock:InvokeModel`)이 IAM Role에 포함되어 있는지 확인하세요.
- **Bedrock 모델 접근 권한**: AWS 콘솔 → Bedrock → Model access에서 Claude 3.5 Haiku 모델 접근 요청을 별도로 진행해야 합니다. 이 작업은 인프라 담당자가 처리합니다.
