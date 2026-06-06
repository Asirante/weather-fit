# batch_generate.py
import itertools, json, boto3, os, time
# from dotenv import load_dotenv
# load_dotenv()

from pattern_domains import (
    TEMP_ZONES, DIFF_LEVELS, RAIN_LEVELS,
    PM_GRADES, WIND_LEVELS, UV_LEVELS, PTY_TYPES,
    build_sk
)
from prompts import SYSTEM_PROMPT, make_user_message

# ============================================================
# 설정
# ============================================================
TABLE      = "inhatc-team2-1-recommend-cache"
MODEL      = "us.anthropic.claude-3-5-haiku-20241022-v1:0"
PK_VAL     = "weather_pattern"
VERSION    = "v1"
BUCKET     = "inhatc-team2-4-batch-data"
INPUT_KEY  = "batch/input/patterns.jsonl"
OUTPUT_URI = f"s3://{BUCKET}/batch/output/"
ROLE_ARN   = "arn:aws:iam::269578498605:role/SafeRole-inhatc-team2-4"

s3       = boto3.client("s3", region_name="us-east-1")
bedrock  = boto3.client("bedrock", region_name="us-east-1")
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table    = dynamodb.Table(TABLE)


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
    """DynamoDB에 이미 있는지 확인"""
    res = table.get_item(Key={"PK": PK_VAL, "SK": sk})
    return "Item" in res


def make_jsonl() -> str:
    """
    패턴을 JSONL 형식으로 변환
    이미 DynamoDB에 있는 패턴은 제외
    """
    lines = []
    skipped = 0

    for sk in all_pattern_sks():
        if already_exists(sk):
            skipped += 1
            continue

        line = {
            "recordId": sk,
            "modelInput": {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": make_user_message(sk)}
                ]
            }
        }
        lines.append(json.dumps(line, ensure_ascii=False))

    print(f"JSONL 생성: {len(lines)}개 (스킵: {skipped}개)")
    return "\n".join(lines)


def upload_to_s3(jsonl_content: str):
    """JSONL 파일 S3에 업로드"""
    s3.put_object(
        Bucket=BUCKET,
        Key=INPUT_KEY,
        Body=jsonl_content.encode("utf-8"),
        ContentType="application/jsonl"
    )
    print(f"S3 업로드 완료: s3://{BUCKET}/{INPUT_KEY}")


def create_batch_job() -> str:
    """Bedrock Batch Job 생성 및 실행"""
    job_name = f"weather-fit-batch-{int(time.time())}"

    response = bedrock.create_model_invocation_job(
        jobName=job_name,
        modelId=MODEL,
        inputDataConfig={
            "s3InputDataConfig": {
                "s3Uri": f"s3://{BUCKET}/{INPUT_KEY}",
                "s3InputFormat": "JSONL"
            }
        },
        outputDataConfig={
            "s3OutputDataConfig": {
                "s3Uri": OUTPUT_URI
            }
        },
        roleArn=ROLE_ARN
    )

    job_arn = response["jobArn"]
    print(f"Batch Job 생성 완료: {job_arn}")
    return job_arn


# ============================================================
# Lambda 핸들러
# ============================================================

def lambda_handler(event, context):
    """
    1단계: JSONL 생성 → S3 업로드 → Batch Job 실행
    Batch 완료 후 결과 저장은 batch_save.py가 처리
    """
    # 1. JSONL 생성
    jsonl_content = make_jsonl()

    if not jsonl_content.strip():
        print("처리할 패턴 없음 (모두 이미 존재)")
        return {"statusCode": 200, "body": "처리할 패턴 없음"}

    # 2. S3 업로드
    upload_to_s3(jsonl_content)

    # 3. Batch Job 실행
    job_arn = create_batch_job()

    return {
        "statusCode": 200,
        "body": f"Batch Job 시작됨: {job_arn}"
    }


if __name__ == "__main__":
    result = lambda_handler({}, None)
    print(f"\n결과: {result}")