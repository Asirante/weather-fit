# infra/

프로젝트의 AWS 인프라를 코드로 정의하고 관리하는 폴더입니다 (Infrastructure as Code).
SAM/CloudFormation 템플릿과 Athena DDL 스크립트를 포함합니다.

---

## 폴더 구조

```
infra/
├── template.yaml          # 공통 인프라 (S3 버킷, DynamoDB, CloudFront 등)
├── samconfig.toml         # SAM 배포 설정 (dev/prod 환경별)
├── athena_ddl/
│   └── weather_parquet.sql
└── README.md
```

---

## 핵심 원칙

1. **콘솔에서 직접 리소스를 수정하지 마세요.** 모든 인프라 변경은 이 폴더의 템플릿을 수정하고 배포하는 방식으로 진행합니다.
2. **환경(dev/prod)은 `samconfig.toml`에서 분리합니다.** `--config-env dev` 또는 `--config-env prod`로 구분합니다.
3. **변경 전 반드시 changeset을 확인하세요.** `sam deploy`는 기본적으로 changeset 확인을 요청합니다. 예상치 못한 리소스 삭제가 없는지 꼭 검토하세요.

---

## 배포

```bash
# 공통 인프라 배포
cd infra
sam build
sam deploy --config-env dev    # 개발 환경
sam deploy --config-env prod   # 운영 환경 (주의!)
```

> ⚠️ prod 환경 배포는 인프라 담당자가 진행합니다. 다른 역할의 팀원은 dev 환경까지만 직접 배포하세요.

---

## samconfig.toml 예시

```toml
[default.deploy.parameters]
stack_name = "myapp-infra"
region = "ap-northeast-2"
confirm_changeset = true
capabilities = "CAPABILITY_IAM"

[dev.deploy.parameters]
stack_name = "myapp-dev-infra"
parameter_overrides = "Environment=dev"

[prod.deploy.parameters]
stack_name = "myapp-prod-infra"
parameter_overrides = "Environment=prod"
```

---

## 관리하는 리소스 목록

| 리소스 | 설명 | 정의 위치 |
|--------|------|----------|
| S3 버킷 (프론트, 데이터) | 정적 파일 호스팅 + 원본 데이터 저장 | `template.yaml` |
| CloudFront | CDN + HTTPS | `template.yaml` |
| DynamoDB 테이블 | 실시간 날씨 데이터 저장 | `template.yaml` |
| EventBridge Rule | 데이터 수집 스케줄 | `data_pipeline/template.yaml` |
| Lambda 함수 | 백엔드 API + 데이터 수집 | 각 영역 `template.yaml` |
| API Gateway | REST API 엔드포인트 | `backend/template.yaml` |
| Athena 테이블 | S3 데이터 분석용 | `athena_ddl/*.sql` |

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

- `template.yaml` 수정 후에는 `sam validate`로 문법 오류를 먼저 확인하세요.
- CloudFormation 스택이 `ROLLBACK_COMPLETE` 상태가 되면 삭제 후 재생성해야 합니다. 이 경우 인프라 담당자에게 연락하세요.
- IAM 권한이나 OIDC Trust Policy 변경은 반드시 인프라 담당자가 리뷰 후 적용합니다.
