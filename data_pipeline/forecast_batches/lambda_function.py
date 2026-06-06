import json
import csv
import os
import boto3
from datetime import datetime
from zoneinfo import ZoneInfo

s3_client = boto3.client("s3")

LOCATION_BUCKET = "inhatc-team2-5-raw-data"
LOCATION_KEY = "location.csv"

# 배치 사이즈 설정
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "50"))


def lambda_handler(event, context):
    output_bucket = os.environ["S3_RAW_BUCKET"]

    response = s3_client.get_object(
        Bucket=LOCATION_BUCKET,
        Key=LOCATION_KEY
    )

    lines = response["Body"].read().decode("utf-8-sig").splitlines()
    reader = csv.DictReader(lines)

    unique = {}

    for row in reader:
        nx = row.get("격자 X")
        ny = row.get("격자 Y")

        if not nx or not ny:
            continue

        key = (nx, ny)

        if key not in unique:
            unique[key] = {
                "nx": int(nx),
                "ny": int(ny),
                "regions": []
            }

        unique[key]["regions"].append({
            "region_code": row.get("행정구역코드", ""),
            "region_name": " ".join(filter(None, [
                row.get("1단계"),
                row.get("2단계"),
                row.get("3단계")
            ]))
        })

    locations = list(unique.values())

    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d%H%M%S")
    run_id = event.get("run_id", now)

    batches = []

    for i in range(0, len(locations), BATCH_SIZE):
        batches.append({
            "run_id": run_id,
            "batch_id": i // BATCH_SIZE,
            "locations": locations[i:i + BATCH_SIZE]
        })

    manifest_key = f"manifests/forecast/ultra_short_forecast/{run_id}/batches.json"

    s3_client.put_object(
        Bucket=output_bucket,
        Key=manifest_key,
        Body=json.dumps(batches, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json"
    )

    return {
        "run_id": run_id,
        "bucket": output_bucket,
        "manifest_key": manifest_key,
        "batch_count": len(batches),
        "location_count": len(locations),
        "created_at": now
    }