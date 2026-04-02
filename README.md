# 날씨 기반 생활 추천 서비스

Vue.js + FastAPI + AWS Serverless 기반의 날씨 맞춤 추천 서비스.
Amazon Bedrock(Claude 3.5 Haiku)을 활용한 AI 추천과 DynamoDB 캐싱으로 비용 효율적인 응답을 제공합니다.
모노레포 구조로 프론트엔드, 백엔드, 데이터 파이프라인을 하나의 레포에서 관리합니다.

> **아키텍처 상세 자료**: [Canva 다이어그램](https://www.canva.com/design/DAHEpM74gSI/j0t2oPmaRZED7YnGqsAEmA/edit?utm_content=DAHEpM74gSI&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)<br/>
> **초기 세팅 가이드**: [`docs/AWS_GitHub_초기세팅_가이드.pdf`](./docs/AWS_GitHub_초기세팅_가이드.pdf)<br/>
> **UI 목업**: [Canva 다이어그램](https://www.canva.com/design/DAHE8EaiVWs/tXiPm_2jMnMIUDvkk83_xQ/edit?utm_content=DAHE8EaiVWs&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)<br/>

---

## 목차

- [프로젝트 구조](#프로젝트-구조)
- [추천 시스템 아키텍처](#추천-시스템-아키텍처)
- [로컬 개발 환경 설정](#로컬-개발-환경-설정)
- [환경 변수](#환경-변수)
- [브랜치 전략 및 PR 규칙](#브랜치-전략-및-pr-규칙)
- [CI/CD 파이프라인](#cicd-파이프라인)
- [배포 환경](#배포-환경)
- [AWS 리소스 구성](#aws-리소스-구성)
- [커밋 컨벤션](#커밋-컨벤션)
- [자주 겪는 문제](#자주-겪는-문제)
- [팀 역할 및 권한](#팀-역할-및-권한)

---

## 프로젝트 구조

```
project-root/
├── .github/workflows/
│   ├── deploy-frontend.yml
│   ├── deploy-backend.yml
│   └── deploy-data-pipeline.yml
├── frontend/               # Vue.js (Vite)
├── backend/                # FastAPI + Mangum
├── data_pipeline/          # 기상 데이터 수집 + AI 배치 추론
├── infra/                  # SAM template, Athena DDL
├── docs/                   # 팀 공유 문서
├── .gitignore
└── README.md
```

각 폴더(`frontend/`, `backend/`, `data_pipeline/`, `infra/`)에는 해당 영역의 별도 README가 있습니다.
인프라 정의 파일은 `infra/`에서 관리하며, 임의로 직접 콘솔에서 리소스를 수정하지 마세요.

---

## 추천 시스템 아키텍처

기존 룰 기반 로직 대신 **Amazon Bedrock (Claude 3.5 Haiku)** 를 사용한 AI 추천 시스템입니다.

### 핵심 구조: AI 배치 추론 + DynamoDB 캐싱

```
[전날 자정]
기상청 예보 수집 → 유니크 기상 패턴 추출 (중복 제거)
  → Bedrock 배치 추론 (수십 개 패턴을 한 번에 처리)
  → DynamoDB에 캐싱 (기상 조건 = PK, AI 답변 = Value, TTL 영구)

[사용자 요청 시]
사용자 위치 날씨 조회 → DynamoDB에서 캐싱된 답변 조회 → 즉시 응답
  → 캐시 미스(새로운 기상 패턴) 시 Bedrock 실시간 호출 (프롬프트 캐싱 적용)
```

### 이 구조의 장점

- **비용 절감**: 대부분의 요청이 DynamoDB 캐시에서 처리되어 Bedrock 호출 최소화
- **응답 속도**: 캐시 히트 시 AI 추론 대기 없이 즉시 응답
- **캐시 미스 대응**: 프롬프트 캐싱으로 시스템 지시어 처리를 건너뛰어 토큰 비용과 응답 시간 절감
- **품질**: 프롬프트 정제를 통한 가이드라인 준수로 환각 방지, 공식 기준 기반 답변 제공
- **UX**: 룰 기반 대비 더 자연스럽고 상세한 맞춤 추천

---

## 로컬 개발 환경 설정

### 사전 설치

| 도구 | 버전 | 확인 명령어 |
|------|------|-----------|
| Node.js | 18+ | `node -v` |
| npm | 9+ | `npm -v` |
| Python | 3.11+ | `python --version` |
| AWS CLI | v2 | `aws --version` |
| SAM CLI | 최신 | `sam --version` |
| git-secrets | 최신 | `git secrets --version` |

### 프론트엔드

```bash
cd frontend
npm ci
cp .env.example .env.local   # 환경 변수 복사 후 값 채우기
npm run dev                   # → http://localhost:5173
```

### 백엔드

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # 환경 변수 복사 후 값 채우기
uvicorn app.main:app --reload # → http://localhost:8000
```

API 문서는 로컬 서버 실행 후 `http://localhost:8000/docs`에서 확인할 수 있습니다 (Swagger UI).

### SAM 로컬 테스트 (선택)

```bash
cd infra
sam build
sam local start-api           # Lambda 로컬 에뮬레이션
```

---

## 환경 변수

`.env` 파일은 **절대 커밋하지 않습니다.** 각 폴더의 `.env.example`을 복사해서 사용하세요.
CI/CD에서 필요한 값은 GitHub Repository Settings → Secrets and variables에 등록되어 있습니다.

```
# frontend/.env.local
VITE_API_BASE_URL=
VITE_KAKAO_MAP_API_KEY=

# backend/.env
DYNAMODB_TABLE_NAME=
S3_BUCKET_NAME=
WEATHER_API_KEY=
BEDROCK_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0

# data_pipeline/.env
BEDROCK_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0
DYNAMODB_CACHE_TABLE_NAME=
```

새로운 환경 변수를 추가할 때는 반드시 `.env.example`도 함께 업데이트해 주세요.

---

## 브랜치 전략 및 PR 규칙

```
main ──────────────────────── 운영 배포 (직접 Push 금지)
  └── develop ─────────────── 통합 테스트 / 개발 환경 배포
        └── feature/* ─────── 개별 기능 개발
```

### 규칙

- `feature/*` → `develop` : **PR 필수 + 최소 1명 코드 리뷰 승인** 후 머지
- `develop` → `main` : 전체 테스트 통과 확인 후 머지
- `main`에 직접 Push 금지 (Branch Protection Rule 적용됨)
- 머지 방식: **Squash and Merge** (커밋 로그 깔끔하게 유지)

### 브랜치 네이밍

```
feature/weather-api       # 새 기능
fix/login-redirect        # 버그 수정
hotfix/critical-s3-error  # 긴급 운영 수정 (main에서 분기)
```

---

## CI/CD 파이프라인

GitHub Actions로 자동 배포됩니다. 각 워크플로우에 **path filter**가 설정되어 있어 해당 폴더가 변경될 때만 실행됩니다.

| 워크플로우 | 트리거 경로 | 동작 |
|-----------|-----------|------|
| `deploy-frontend.yml` | `frontend/**` | build → S3 업로드 → CloudFront 캐시 무효화 |
| `deploy-backend.yml` | `backend/**` | pytest → sam build → sam deploy |
| `deploy-data-pipeline.yml` | `data_pipeline/**` | sam build → sam deploy |

### 인증 방식

GitHub ↔ AWS 인증은 **OIDC**를 사용합니다. 장기 Access Key는 사용하지 않습니다.
OIDC 설정 상세는 [초기 세팅 가이드 4.1절](./docs/AWS_GitHub_초기세팅_가이드.pdf)을 참고하세요.

### 수동 배포가 필요할 때

```bash
# 프론트엔드 수동 배포
cd frontend
npm run build
aws s3 sync dist/ s3://<bucket-name> --delete
aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"

# 백엔드 수동 배포
cd backend
sam build
sam deploy --config-env <dev|prod>
```

---

## 배포 환경

개발(dev)과 운영(prod) 환경이 분리되어 있습니다. 리소스를 혼동하지 않도록 주의하세요.

| 구분 | 트리거 브랜치 | S3 버킷 | API 엔드포인트 |
|------|-------------|---------|--------------|
| **Development** | `develop` | `myapp-dev-frontend` | Lambda Function URL (dev) |
| **Production** | `main` | `myapp-prod-frontend` | Lambda Function URL (prod) |

> ⚠️ **리전은 `ap-northeast-2`(서울)로 통일합니다.** 콘솔에서 작업할 때 리전이 다른 곳으로 설정되어 있지 않은지 반드시 확인하세요.

---

## AWS 리소스 구성

```
Frontend:  S3 (정적 호스팅) → CloudFront (CDN + HTTPS)

Backend:   Lambda Function URL (FastAPI + Mangum)
             → DynamoDB (캐싱된 AI 답변 조회)
             → Bedrock (캐시 미스 시 실시간 호출, 프롬프트 캐싱 적용)

Data:      EventBridge (매일 자정)
             → Lambda (기상청 예보 수집 + 유니크 패턴 추출)
             → Bedrock 배치 추론 (수십 개 패턴 일괄 처리)
             → DynamoDB (AI 답변 캐싱, TTL 영구)
             → S3 (원본 데이터) → Glue (ETL) → Athena (분석)
```

### 프리 티어 한도 (주요 서비스)

| 서비스 | 무료 범위 | 비고 |
|--------|----------|------|
| Lambda | 요청 100만/월 + 40만 GB-초 | 무기한, Function URL 요청 포함 |
| DynamoDB | 저장 25GB + R/W 각 25단위 | 무기한 |
| S3 | 저장 5GB | 12개월 |
| CloudFront | 전송 1TB + 요청 1,000만/월 | 무기한 |
| **Bedrock** | **프리 티어 없음** | 입출력 토큰 기반 과금 |
| **Glue** | **프리 티어 없음** | DPU-시간 과금 |
| **Athena** | **프리 티어 없음** | 스캔 TB당 $5 |

> **Bedrock 비용 관리**: 배치 추론으로 대부분의 패턴을 사전 캐싱하고, 캐시 미스 시에는 프롬프트 캐싱을 적용하여 토큰 비용을 절감합니다. 프롬프트 변경이나 새 모델 테스트 시 예상 비용을 팀에 공유해 주세요.

---

## 커밋 컨벤션

```
<type>: <subject>

# 예시
feat: 날씨 API 응답에 미세먼지 데이터 추가
fix: CloudFront 캐시로 인한 구버전 노출 문제 수정
docs: README에 로컬 개발 환경 설정 추가
refactor: 추천 로직 함수 분리
test: AI 추천 캐싱 로직 단위 테스트 추가
chore: GitHub Actions Python 버전 업데이트
```

| type | 설명 |
|------|------|
| `feat` | 새로운 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서 변경 |
| `refactor` | 기능 변경 없는 코드 개선 |
| `test` | 테스트 추가/수정 |
| `chore` | 빌드, 설정 등 기타 변경 |

---

## 자주 겪는 문제

### S3에 배포했는데 화면이 안 바뀌어요

CloudFront 캐시 때문입니다. CI/CD 파이프라인에 무효화 단계가 포함되어 있지만, 수동 배포 시에는 직접 실행해야 합니다.

```bash
aws cloudfront create-invalidation --distribution-id <ID> --paths "/*"
```

### Lambda 배포 시 패키지 용량 초과 에러

ZIP 배포는 압축 해제 시 250MB 제한이 있습니다. 의존성이 많아졌다면 Lambda Layer로 분리하거나 컨테이너 이미지 배포(최대 10GB)로 전환을 검토하세요.

### `sam deploy`에서 권한 에러

- 현재 AWS CLI 프로필의 리전이 `ap-northeast-2`인지 확인 → `aws configure get region`
- IAM 권한이 부족한 경우 인프라 담당자에게 요청하세요
- OIDC Role의 Trust Policy에 본인 브랜치가 허용 조건에 포함되어 있는지 확인하세요

### 로컬에서 DynamoDB 접근이 안 돼요

로컬 개발 시에는 [DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html)을 사용하거나, dev 환경의 테이블을 사용하세요. **prod 테이블에 직접 접근하는 것은 금지**합니다.

### Lambda Function URL에서 CORS 에러

프론트엔드에서 Lambda Function URL을 직접 호출할 때 CORS 에러가 발생할 수 있습니다. FastAPI 앱에서 `CORSMiddleware`를 설정하고, SAM 템플릿의 `FunctionUrlConfig`에서 `Cors` 속성을 적절히 지정해야 합니다. CloudFront를 통해 프록시하는 경우에는 동일 도메인이므로 CORS 이슈가 없습니다.

### Bedrock 호출 시 AccessDeniedException

Bedrock 모델 접근 권한이 없는 경우 발생합니다. AWS 콘솔 → Bedrock → Model access에서 Claude 3.5 Haiku 모델이 활성화되어 있는지 확인하세요. 모델 접근 요청은 인프라 담당자가 처리합니다.

---

## 팀 역할 및 권한

| 담당 | AWS 권한 | 주요 작업 |
|------|---------|----------|
| Frontend | S3, CloudFront | Vue.js UI, 반응형, 지도 연동 |
| Backend | Lambda, DynamoDB, Bedrock | API 설계, AI 추천 로직, 캐시 조회/미스 처리 |
| Data | Lambda, EventBridge, S3, Glue, Athena, Bedrock | 기상 데이터 수집, 배치 추론, 캐싱 파이프라인 |
| Infra | IAM, CloudFormation, SAM, CloudWatch | 인프라 관리, 모니터링, 권한 관리 |
| PM | 읽기 전용 | 일정 관리, 이슈 트래킹 |

본인 역할 범위 외의 AWS 리소스를 직접 수정해야 할 경우, 반드시 인프라 담당자에게 먼저 확인하세요.
