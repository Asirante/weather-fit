# batch_save.py
import json, boto3, os
# from dotenv import load_dotenv
# load_dotenv()

# ============================================================
# 설정
# ============================================================
TABLE         = "inhatc-team2-1-recommend-cache"
MODEL         = "us.anthropic.claude-4-5-haiku-20241022-v1:0"
PK_VAL        = "weather_pattern"
VERSION       = "v1"
BUCKET        = "inhatc-team2-4-batch-data"
OUTPUT_PREFIX = "batch/output/"

s3       = boto3.client("s3", region_name="us-east-1")
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table    = dynamodb.Table(TABLE)


def save_to_dynamodb(sk: str, data: dict):
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


def lambda_handler(event, context):
    """
    S3 결과 파일 읽어서 DynamoDB 저장
    Batch Job 완료 후 수동으로 실행
    """
    response = s3.list_objects_v2(
        Bucket=BUCKET,
        Prefix=OUTPUT_PREFIX
    )

    if "Contents" not in response:
        print("결과 파일 없음")
        return {"statusCode": 200, "body": "결과 파일 없음"}

    total = saved = errors = 0

    for obj in response["Contents"]:
        key = obj["Key"]
        if not key.endswith(".jsonl.out"):
            continue

        # 결과 파일 읽기
        file_obj = s3.get_object(Bucket=BUCKET, Key=key)
        content = file_obj["Body"].read().decode("utf-8")

        # 한 줄씩 파싱
        for line in content.strip().split("\n"):
            if not line:
                continue
            total += 1
            try:
                result = json.loads(line)
                sk = result["recordId"]
                output = result["modelOutput"]["content"][0]["text"]

                # 마크다운 코드블록 제거
                output = output.strip()
                if output.startswith("```"):
                    output = output.split("```")[1]
                    if output.startswith("json"):
                        output = output[4:]

                data = json.loads(output.strip())
                save_to_dynamodb(sk, data)
                saved += 1

            except Exception as e:
                print(f"ERROR: {e}")
                errors += 1

    result_msg = f"완료: 전체{total} 저장{saved} 오류{errors}"
    print(result_msg)
    return {"statusCode": 200, "body": result_msg}


if __name__ == "__main__":
    result = lambda_handler({}, None)
    print(f"\n결과: {result}")