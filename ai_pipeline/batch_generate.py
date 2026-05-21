# batch_generate.py
import itertools, json, boto3, time, os
from pattern_domains import (
    TEMP_ZONES, DIFF_LEVELS, RAIN_LEVELS,
    PM_GRADES, WIND_LEVELS, UV_LEVELS, PTY_TYPES,
    build_sk
)
from prompts import SYSTEM_PROMPT, make_user_message

# ============================================================
# 설정
# ============================================================
TABLE   = "inhatc-team2-1-recommend-cache"
MODEL   = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
PK_VAL  = "weather_pattern"
VERSION = "v1"

# 로컬 vs Lambda 자동 감지
is_local = os.environ.get("IS_LOCAL") == "true"

dynamodb = boto3.resource(
    "dynamodb",
    region_name="us-east-1",
    endpoint_url="http://localhost:8000" if is_local else None
)
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
table   = dynamodb.Table(TABLE)


# ============================================================
# 함수
# ============================================================

def all_pattern_sks():
    """27,000개 패턴 키 생성"""
    for combo in itertools.product(
        TEMP_ZONES, DIFF_LEVELS, RAIN_LEVELS,
        PM_GRADES, WIND_LEVELS, UV_LEVELS, PTY_TYPES
    ):
        yield build_sk(*combo)


def already_exists(sk: str) -> bool:
    """DynamoDB에 이미 있는지 확인 → 있으면 스킵"""
    res = table.get_item(Key={"PK": PK_VAL, "SK": sk})
    return "Item" in res


def call_bedrock(sk: str) -> dict:
    """Bedrock 호출 → JSON 응답 반환"""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": make_user_message(sk)}]
    })
    res  = bedrock.invoke_model(modelId=MODEL, body=body)
    text = json.loads(res["body"].read())["content"][0]["text"]

    # AI가 마크다운 코드블록으로 감쌀 경우 제거
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    return json.loads(text.strip())


def save(sk: str, data: dict):
    """DynamoDB에 결과 저장"""
    table.put_item(Item={
        "PK":      PK_VAL,
        "SK":      sk,
        "top":     data["top"],
        "bottom":  data["bottom"],
        "mask":    data["mask"],
        "pack":    data["pack"],
        "acc":     data.get("acc", []),
        "reason":  data.get("reason", ""),
        "model":   MODEL,
        "version": VERSION,
    })


# ============================================================
# Lambda 핸들러
# ============================================================

def lambda_handler(event, context):
    """
    AWS Lambda 진입점

    event 파라미터:
        limit (int): 테스트 시 처리할 패턴 수 제한
                     없으면 전체 처리
    예시:
        {"limit": 10}  → 10개만 처리 (테스트용)
        {}             → 전체 처리 (실전용)
    """
    limit = event.get("limit", None)
    total = skipped = saved = errors = 0
    consecutive_errors = 0

    for sk in all_pattern_sks():

        # limit 있으면 그 개수만 처리
        if limit and total >= limit:
            print(f"limit {limit}개 도달 → 종료")
            break

        total += 1

        # 100개마다 진행률 출력
        if total % 100 == 0:
            print(f"[{total}] 저장:{saved} 스킵:{skipped} 오류:{errors}")

        # 이미 있으면 스킵
        if already_exists(sk):
            skipped += 1
            continue

        try:
            data = call_bedrock(sk)
            save(sk, data)
            saved += 1
            consecutive_errors = 0
            time.sleep(0.1)  # API 호출 제한 방지

        except Exception as e:
            print(f"ERROR {sk}: {e}")
            errors += 1
            consecutive_errors += 1

            # 연속 에러 10개 넘으면 중단
            if consecutive_errors >= 10:
                print("연속 에러 10개 초과 → 중단!")
                break

    result = f"완료: 전체{total} 스킵{skipped} 저장{saved} 오류{errors}"
    print(result)
    return {"statusCode": 200, "body": result}


# ============================================================
# 로컬 Mock 테스트용
# ============================================================

if __name__ == "__main__":
    print("=== Mock 테스트 시작 ===\n")

    # call_bedrock을 Mock으로 교체
    def mock_bedrock(sk: str) -> dict:
        return {
            "top": ["반팔"],
            "bottom": ["반바지"],
            "mask": "마스크 선택",
            "pack": "불필요",
            "acc": ["선크림"],
            "reason": "더운 날씨, 시원하게 입어요"
        }

    # 전역 함수 교체
    import sys
    current_module = sys.modules[__name__]
    current_module.call_bedrock = mock_bedrock

    # 5개만 테스트
    result = lambda_handler({"limit": 5}, None)
    print(f"\n결과: {result}")