import os
import csv
import json
import logging
from functools import lru_cache
from datetime import datetime
from zoneinfo import ZoneInfo

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")

LOCATION_BUCKET = os.environ.get("LOCATION_BUCKET", "inhatc-team2-5-raw-data")
LOCATION_KEY = os.environ.get("LOCATION_KEY", "location.csv")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "30"))


@lru_cache(maxsize=1)
def load_locations():
    response = s3_client.get_object(
        Bucket=LOCATION_BUCKET,
        Key=LOCATION_KEY
    )

    lines = response["Body"].read().decode("utf-8-sig").splitlines()
    reader = csv.DictReader(lines)

    return list(reader)


def load_unique_grid_locations():
    locations = load_locations()
    unique = {}

    for row in locations:
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
                row.get("1단계", ""),
                row.get("2단계", "")
            ])).strip()
        })

    result = list(unique.values())

    logger.info(
        f"Unique grid locations: {len(result)} / original={len(locations)}"
    )

    return result


def chunk_list(items, batch_size):
    batches = []

    for i in range(0, len(items), batch_size):
        batches.append({
            "batch_id": i // batch_size,
            "items": items[i:i + batch_size]
        })

    return batches


def lambda_handler(event, context):
    output_bucket = os.environ["S3_RAW_BUCKET"]

    locations = load_unique_grid_locations()
    batches = chunk_list(locations, BATCH_SIZE)

    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d%H%M%S")

    manifest_key = f"manifests/weather/realtime/{now}/batches.json"

    s3_client.put_object(
        Bucket=output_bucket,
        Key=manifest_key,
        Body=json.dumps(batches, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json"
    )

    logger.info(
        f"Created weather manifest: s3://{output_bucket}/{manifest_key}, "
        f"batch_count={len(batches)}, location_count={len(locations)}"
    )

    return {
        "bucket": output_bucket,
        "manifest_key": manifest_key,
        "batch_count": len(batches),
        "location_count": len(locations),
        "created_at": now
    }