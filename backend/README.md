# backend/

FastAPI + Mangum 기반 백엔드 API. AWS Lambda 위에서 실행되며, Lambda Function URL을 통해 외부에 노출됩니다.
사용자 요청 시 DynamoDB에서 캐싱된 AI 추천을 조회하고, 캐시 미스 시 Bedrock를 실시간 호출합니다.

---

## 기술 스택

| 기술 | 용도 |
|------|------|
| Python 3.11+ | 런타임 |
| FastAPI | REST API 프레임워크 |
| Mangum | FastAPI → Lambda 어댑터 |
| Lambda Function URL | API 엔드포인트 |
| Amazon Bedrock | AI 추천 생성 (Claude 3.5 Haiku) |
| Amazon DynamoDB | AI 답변 캐시 저장소 |
| boto3 | AWS SDK (DynamoDB, S3, Bedrock 접근) |
| pytest | 테스트 프레임워크 |

---

## 추천 응답 흐름

```
사용자 요청 (위치 + 날씨)
  → 기상 조건으로 DynamoDB 파티션 키 생성
  → DynamoDB 캐시 조회
    → 캐시 히트: 저장된 AI 답변 즉시 반환
    → 캐시 미스: Bedrock 실시간 호출 (프롬프트 캐싱 적용)
      → 응답을 DynamoDB에 저장 후 반환
```

대부분의 기상 패턴은 전날 자정 배치 추론으로 사전 캐싱되어 있으므로, 실시간 Bedrock 호출은 예외적인 경우에만 발생합니다.

---

## 로컬 실행

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

`http://localhost:8000`에서 실행됩니다.
API 문서는 `http://localhost:8000/docs` (Swagger UI)에서 확인할 수 있습니다.

---

## 환경 변수

`.env.example`을 `.env`로 복사한 뒤 값을 채워주세요.

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `DYNAMODB_TABLE_NAME` | AI 추천 캐시 테이블명 | `weather-recommend-dev` |
| `S3_BUCKET_NAME` | 원본 데이터 버킷명 | `myapp-dev-raw-data` |
| `WEATHER_API_KEY` | 기상청 API 인증키 | 공공데이터포털에서 발급 |
| `BEDROCK_MODEL_ID` | Bedrock 모델 ID | `anthropic.claude-3-5-haiku-20241022-v1:0` |

---

## 폴더 구조

```
backend/
├── app/
│   ├── main.py           # FastAPI 앱 + Mangum 핸들러
│   ├── routers/          # 엔드포인트별 라우터
│   ├── services/
│   │   ├── recommend.py  # 추천 로직 (캐시 조회 → Bedrock 호출)
│   │   ├── bedrock.py    # Bedrock 클라이언트 및 프롬프트 관리
│   │   ├── cache.py      # DynamoDB 캐시 읽기/쓰기
│   │   └── weather.py    # 기상 데이터 조회
│   ├── models/           # Pydantic 스키마
│   ├── prompts/          # 시스템 프롬프트 템플릿
│   ├── utils/            # 유틸리티 함수
│   └── config.py         # 환경 변수 로드
├── tests/
│   ├── test_recommend.py
│   ├── test_cache.py
│   └── conftest.py
├── requirements.txt
├── template.yaml          # SAM 템플릿 (백엔드용)
├── .env.example
└── README.md
```

---

## 테스트

```bash
# 전체 테스트
pytest

# 특정 파일
pytest tests/test_recommend.py

# 커버리지 포함
pytest --cov=app
```

CI/CD 파이프라인에서 pytest가 실패하면 배포가 중단됩니다. PR 올리기 전에 로컬에서 반드시 테스트를 돌려주세요.

---

## Bedrock 연동 참고사항

### 프롬프트 캐싱

캐시 미스로 Bedrock를 실시간 호출할 때, **프롬프트 캐싱**을 적용하여 반복되는 시스템 지시어의 토큰 처리를 건너뜁니다. 이를 통해 토큰 비용과 응답 시간을 절감합니다.

### 프롬프트 관리

시스템 프롬프트는 `app/prompts/` 폴더에서 관리합니다. 프롬프트 변경 시 주의사항:
- 변경 후 반드시 여러 기상 패턴으로 테스트하여 환각(hallucination) 발생 여부 확인
- 공식 기준(기상청 기준, 의류 가이드라인 등)을 프롬프트에 포함하여 답변 신뢰성 확보
- 프롬프트 변경은 PR에 변경 사유와 테스트 결과를 함께 기재

### DynamoDB 캐시 키 설계

파티션 키는 기상 조건(기온, 습도, 강수 확률 등)의 조합으로 구성됩니다. 키 설계 변경 시 기존 캐시가 무효화될 수 있으므로 데이터 팀과 반드시 협의하세요.

### 로컬에서 Bedrock 테스트

로컬에서 Bedrock를 호출하려면 AWS 자격 증명이 필요합니다. dev 환경의 자격 증명을 사용하되, 불필요한 반복 호출을 피하세요 (토큰 과금). 테스트 시에는 DynamoDB 캐시 히트 시나리오 위주로 확인하고, Bedrock 직접 호출 테스트는 최소한으로 진행합니다.

---

## 배포

`develop` 또는 `main` 브랜치에 Push하면 GitHub Actions가 자동으로 테스트 → SAM 빌드 → 배포를 수행합니다. 수동 배포가 필요한 경우:

```bash
sam build
sam deploy --config-env dev   # 개발 환경
sam deploy --config-env prod  # 운영 환경
```

배포 완료 후 출력되는 Function URL이 API 엔드포인트입니다.

### Lambda 패키징 주의사항

- ZIP 배포 시 압축 해제 기준 **250MB 제한**이 있습니다.
- 의존성이 늘어나면 Lambda Layer로 분리하거나 컨테이너 이미지 배포를 검토하세요.
- `requirements.txt`에 불필요한 패키지가 포함되지 않도록 관리해 주세요.

---

## 개발 시 참고사항

### DynamoDB 접근

- 로컬 개발 시: [DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html) 또는 dev 환경 테이블 사용
- **prod 테이블에 직접 접근 금지**
- boto3 클라이언트 생성 시 `region_name="ap-northeast-2"` 명시

### API 버전 관리

엔드포인트 경로에 버전 접두사를 사용합니다: `/api/v1/weather`, `/api/v1/recommend`
breaking change가 필요하면 `/api/v2/...`로 새 버전을 추가하고, 기존 버전은 일정 기간 유지합니다.
