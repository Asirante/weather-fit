import os
import csv
import io
import logging
import boto3
from datetime import datetime
from zoneinfo import ZoneInfo

s3_client = boto3.client("s3")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def read_csv_from_s3(bucket, key):
    response = s3_client.get_object(
        Bucket=bucket,
        Key=key
    )

    text = response["Body"].read().decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(text))
    return reader.fieldnames, list(reader)


def upload_csv(bucket, key, fieldnames, rows):
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

    logger.info(f"Uploaded merged forecast CSV: s3://{bucket}/{key}")

    return key


def lambda_handler(event, context):
    bucket = os.environ["S3_RAW_BUCKET"]
    run_id = event["run_id"]

    prefix = f"raw_tmp/forecast/{run_id}/"

    response = s3_client.list_objects_v2(
        Bucket=bucket,
        Prefix=prefix
    )

    merged_rows = []
    fieldnames = None
    source_files = []

    for obj in response.get("Contents", []):
        key = obj["Key"]

        if not key.endswith("/ultra_short_forecast.csv"):
            continue

        current_fieldnames, rows = read_csv_from_s3(bucket, key)

        if fieldnames is None:
            fieldnames = current_fieldnames

        merged_rows.extend(rows)
        source_files.append(key)

    if not merged_rows:
        raise ValueError(f"No forecast batch files found for run_id={run_id}")

    timestamp = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).strftime("%Y%m%d%H%M%S")

    date_str = timestamp[:8]

    final_key = f"raw/forecast/ultra_short_forecast/{timestamp}.csv"

    upload_csv(
        bucket=bucket,
        key=final_key,
        fieldnames=fieldnames,
        rows=merged_rows
    )

    return {
        "statusCode": 200,
        "run_id": run_id,
        "source_file_count": len(source_files),
        "row_count": len(merged_rows),
        "final_key": final_key,
        "source_files": source_files[:10]
    }