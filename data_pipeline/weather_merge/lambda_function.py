import os
import csv
import io
import logging
import boto3
from datetime import datetime
from zoneinfo import ZoneInfo

timestamp = datetime.now(
    ZoneInfo("Asia/Seoul")
).strftime("%Y%m%d%H%M%S")


s3_client = boto3.client("s3")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def list_all_objects(bucket, prefix):
    # 페이지네이션: 배치가 1000개를 넘어도 누락 없이 전체 수집
    objs = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objs.extend(page.get("Contents", []))
    return objs


def read_csv_from_s3(bucket, key):
    response = s3_client.get_object(Bucket=bucket, Key=key)
    text = response["Body"].read().decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(text))
    return reader.fieldnames, list(reader)


def upload_merged_csv(bucket, key, fieldnames, rows):
    output = io.StringIO()

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=output.getvalue().encode("utf-8-sig"),
        ContentType="text/csv"
    )

    logger.info(f"Merged uploaded: s3://{bucket}/{key}")
    return key


def merge_weather_api(bucket, run_id, api_name):
    prefix = f"raw_tmp/weather/{run_id}/"

    merged_rows = []
    fieldnames = None

    for obj in list_all_objects(bucket, prefix):
        key = obj["Key"]

        if not key.endswith(f"/{api_name}.csv"):
            continue

        current_fieldnames, rows = read_csv_from_s3(bucket, key)

        if fieldnames is None:
            fieldnames = current_fieldnames

        merged_rows.extend(rows)

    if not merged_rows:
        logger.warning(f"No rows found for {api_name}")
        return None


    date_str = timestamp[:8]

    final_key = f"raw/weather/{api_name}/{timestamp}.csv"

    return upload_merged_csv(
        bucket=bucket,
        key=final_key,
        fieldnames=fieldnames,
        rows=merged_rows
    )


def lambda_handler(event, context):
    bucket = os.environ["S3_RAW_BUCKET"]
    run_id = event["run_id"]

    final_keys = []

    for api_name in ["uv_index", "air_diffusion"]:
        key = merge_weather_api(bucket, run_id, api_name)

        if key:
            final_keys.append(key)

    return {
        "statusCode": 200,
        "run_id": run_id,
        "final_keys": final_keys
    }