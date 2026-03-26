# backend/

FastAPI + Mangum 기반 백엔드 API. AWS Lambda 위에서 실행되며, API Gateway를 통해 외부에 노출됩니다.

---

## 기술 스택

| 기술 | 용도 |
|------|------|
| Python 3.11+ | 런타임 |
| FastAPI | REST API 프레임워크 |
| Mangum | FastAPI → Lambda 어댑터 |
| pytest | 테스트 프레임워크 |
| boto3 | AWS SDK (DynamoDB, S3 접근) |

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
| `DYNAMODB_TABLE_NAME` | 날씨 데이터 테이블명 | `weather-data-dev` |
| `S3_BUCKET_NAME` | 원본 데이터 버킷명 | `myapp-dev-raw-data` |
| `WEATHER_API_KEY` | 기상청 API 인증키 | 공공데이터포털에서 발급 |

---

## 폴더 구조

```
backend/
├── app/
│   ├── main.py           # FastAPI 앱 + Mangum 핸들러
│   ├── routers/          # 엔드포인트별 라우터
│   ├── services/         # 비즈니스 로직
│   ├── models/           # Pydantic 스키마
│   ├── utils/            # 유틸리티 함수
│   └── config.py         # 환경 변수 로드
├── tests/
│   ├── test_weather.py
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
pytest tests/test_weather.py

# 커버리지 포함
pytest --cov=app
```

CI/CD 파이프라인에서 pytest가 실패하면 배포가 중단됩니다. PR 올리기 전에 로컬에서 반드시 테스트를 돌려주세요.

---

## Mangum 핸들러

`app/main.py`에서 FastAPI 앱을 Mangum으로 감싸서 Lambda 핸들러로 내보냅니다.

```python
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

# 라우터 등록
# app.include_router(...)

handler = Mangum(app)  # Lambda 진입점
```

로컬에서는 `uvicorn`으로 실행하고, Lambda에서는 `handler`가 진입점이 됩니다. SAM 템플릿의 `Handler` 값이 `app.main.handler`로 설정되어 있는지 확인하세요.

---

## 배포

`develop` 또는 `main` 브랜치에 Push하면 GitHub Actions가 자동으로 테스트 → SAM 빌드 → 배포를 수행합니다. 수동 배포가 필요한 경우:

```bash
sam build
sam deploy --config-env dev   # 개발 환경
sam deploy --config-env prod  # 운영 환경
```

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
