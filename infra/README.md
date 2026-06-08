# infra/

프로젝트 공통 AWS 리소스(버킷·테이블)의 **참고용** 정의와 운영 메모입니다.

> ⚠️ **SAM CLI 사용 불가**: 학교 AWS 계정은 비용관리 태그(Cost Allocation Tag) 기반으로 리소스 CRUD 권한을 제어합니다. Lambda 생성 직후 태그가 붙기 전 SAM이 후속 작업을 시도하면 `AccessDeniedException`이 납니다. 따라서 `sam build/deploy`는 쓰지 않으며, **모든 인프라는 콘솔에서 수동 관리**합니다.
>
> `infra/template.yaml`은 현재 리소스 구조를 **문서화한 참고 템플릿**입니다(그대로 배포용 아님).

---

## 폴더 구조

```
infra/
├── template.yaml   # 공통 리소스(버킷·테이블) 참고 정의 — 코드 기준 현행화됨
└── README.md
```

> 모듈별(backend/real_time)에 있던 SAM 템플릿은 **삭제**했습니다(미사용 + 실제와 불일치). 람다 배포는 `update-function-code`, 오케스트레이션은 Step Functions(콘솔)입니다.

---

## 핵심 원칙

1. **인프라는 콘솔에서 수동 관리** (S3·DynamoDB·Lambda·Step Functions·EventBridge).
2. **Lambda 코드만 GitHub Actions가 자동 배포** (`aws lambda update-function-code`).
3. 인프라를 바꾸면 `template.yaml`도 같이 갱신해 팀이 현재 구조를 파악하도록 유지.

---

## 현재 리소스

### S3 버킷
| 버킷 | 용도 |
|------|------|
| `inhatc-team2-3-frontend` | 프론트 정적 호스팅 |
| `inhatc-team2-5-raw-data` | 수집 원본(CSV/매니페스트) |
| `inhatc-team2-4-parquet-data` | 분석용 Parquet |
| `inhatc-team2-4-batch-data` | Bedrock 배치 입출력 |

### DynamoDB 테이블 (키는 코드 기준)
| 테이블 | PK | SK | TTL |
|--------|----|----|-----|
| `inhatc-team2-5-weather-cache` | `region_code` | `category` | – |
| `inhatc-team2-5-air-cache` | `stationKey` | – | – |
| `inhatc-team2-5-forecast-cache` | `region_code` | `forecast_key` | `expireAt` |
| `inhatc-team2-1-recommend-cache` | `PK` | `SK` | 영구 |

> weather/forecast는 한 지역에 여러 row(카테고리·예보시각)를 두므로 **복합키**입니다. `forecast-cache`는 누적 방지를 위해 **TTL(`expireAt`) 활성화 필요**.

### 수집 오케스트레이션 (Step Functions, 콘솔 관리)
| 상태머신 | 내용 | 적재 |
|----------|------|------|
| 실시간 실황 | `getUltraSrtNcst` Distributed Map | weather-cache |
| 예보 | `getUltraSrtFcst` Distributed Map + merge | forecast-cache |
| 부가배치 | 자외선·대기확산·통계·주간예보 | S3 (+UV는 실황이 캐시 반영) |
| 대기질(실시간) | 에어코리아 시도별 | air-cache |

EventBridge 스케줄로 주기 실행됩니다(예: 실황 15분). **스케줄이 멈추면 화면에 옛 데이터가 노출**되므로 상태 점검이 중요합니다.

### Lambda 함수(주요)
| 함수 | 트리거 | 담당 |
|------|--------|------|
| `inhatc-team2-1-recommendAPI` | Function URL | 서빙 |
| `inhatc-team2-5-*` (real-time/forecast/weather worker·merge·batches) | Step Functions | 수집 |
| `inhatc-team2-4-batchAPI` | 수동/스케줄 | AI 배치 |

---

## 변경 시 주의
- 추천 캐시 키(PK/SK) 설계 변경 = 기존 캐시 전체 무효화 → backend/ai_pipeline 팀과 협의.
- IAM/OIDC Trust Policy 변경은 인프라 담당자 리뷰 후 적용.
- Bedrock 모델 접근 권한(콘솔 → Bedrock → Model access)과 Lambda의 `bedrock:InvokeModel`/DynamoDB 권한 확인.
- prod 인프라 변경은 인프라 담당자만.
