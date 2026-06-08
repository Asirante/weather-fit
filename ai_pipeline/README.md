# ai_pipeline/

Amazon Bedrock **배치 추론**으로 모든 기상 패턴의 옷차림 추천을 **사전 생성**해 `recommend-cache`에 저장합니다.
서빙(`backend`)은 이 캐시를 조회만 하므로 요청 시 LLM 호출이 없습니다.

---

## 구성

```
ai_pipeline/
├── pattern_domains.py   # 기상 패턴 도메인(enum/임계값) + 패턴키(SK) 생성기
├── prompts.py           # 시스템 프롬프트 + 사용자 메시지(패턴키 → 지시문)
├── batch_generate.py    # 27,000 패턴 JSONL 생성 → S3 업로드 → Bedrock 배치 잡 생성
├── batch_save.py        # 배치 결과(JSONL) 파싱 → recommend-cache 적재
├── requirements.txt
└── README.md
```

---

## 동작

```
batch_generate.py
  1. 모든 패턴 조합 생성: temp(10)×diff(5)×rain(5)×pm(4)×wind(3)×uv(3)×pty(3) = 27,000
  2. 이미 recommend-cache에 있는 패턴은 제외
  3. 신규 패턴을 JSONL(모델 입력)로 만들어 S3 업로드
  4. Bedrock create_model_invocation_job(배치)로 일괄 추론

(배치 완료 후)
batch_save.py
  - 배치 출력 JSONL 파싱 → 각 패턴(SK)별 추천(top/bottom/mask/pack/acc/reason)을
    recommend-cache(PK="weather_pattern", SK=패턴키)에 저장
```

- 모델: `anthropic.claude-3-5-haiku`(Bedrock 배치)
- 패턴키(SK) 포맷: `temp:..|diff:..|rain:..|pm:..|wind:..|uv:..|pty:..`

---

## ⚠️ 패턴 임계값은 backend와 반드시 일치
`pattern_domains.py`의 `get_temp_zone/get_diff_level/get_rain_level/get_pm_grade/get_wind_level/get_uv_level/get_pty_type/build_sk`는
**`backend/lambda_function.py`의 동일 함수들과 임계값·enum·SK 포맷이 정확히 일치해야** 합니다.
하나라도 어긋나면 서빙 시 캐시 미스(404)가 납니다. (현재 일치 — 변경 시 양쪽 동시 수정 권장, 가능하면 공용 모듈로 분리)

---

## 비용/운영 주의
- 신규 패턴만 추론(기존 캐시 제외)하므로 재실행 비용을 줄입니다. 단 `already_exists`가 패턴마다 `GetItem`을 호출하므로 대량 시 느릴 수 있습니다(BatchGetItem/스캔으로 개선 여지).
- `max_tokens`가 너무 작으면 JSON 출력이 잘려 저장 단계에서 드롭될 수 있으니 여유를 둡니다.
- 하드코딩된 계정/역할/버킷 ARN은 환경변수/파라미터화 권장.

---

## 배포
`develop`/`main`의 `ai_pipeline/**` 변경 → `deploy-all-lambdas.yml`(batchAPI)이 `update-function-code`로 배포.
> 외부 의존성이 필요하면 Lambda Layer로 분리하세요(현재 워크플로우는 `requirements.txt`를 vendoring하지 않음).
