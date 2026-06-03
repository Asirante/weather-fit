import json
import os
import csv
import io
import boto3
import logging
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

s3_client = boto3.client("s3")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ENDPOINT = "/getUltraSrtFcst"


def get_base_datetime():
    now = datetime.now(ZoneInfo("Asia/Seoul")) - timedelta(hours=1)
    return now.strftime("%Y%m%d"), now.strftime("%H00")


def call_api(location):
    base_url = os.environ["FORECAST_API_URL"]
    service_key = os.environ["WEATHER_API_KEY"]

    base_date, base_time = get_base_datetime()

    params = {
        "ServiceKey": service_key,
        "pageNo": "1",
        "numOfRows": "1000",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": location["nx"],
        "ny": location["ny"]
    }

    url = f"{base_url}{ENDPOINT}?{urlencode(params)}"

    request = Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    },
    method="GET"
)

    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_rows(location, api_data):
    rows = []

    items = (
        api_data.get("response", {})
        .get("body", {})
        .get("items", {})
        .get("item", [])
    )

    if isinstance(items, dict):
        items = [items]

    for item in items:
        rows.append({
            "region_code": location.get("region_code", ""),
            "region_name": location.get("region_name", ""),
            "region_nx": location.get("nx", ""),
            "region_ny": location.get("ny", ""),
            "baseDate": item.get("baseDate", ""),
            "baseTime": item.get("baseTime", ""),
            "fcstDate": item.get("fcstDate", ""),
            "fcstTime": item.get("fcstTime", ""),
            "category": item.get("category", ""),
            "fcstValue": item.get("fcstValue", ""),
            "nx": item.get("nx", ""),
            "ny": item.get("ny", "")
        })

    return rows


def upload_csv(bucket, run_id, batch_id, rows):
    if not rows:
        return None

    output = io.StringIO()

    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    key = (
        f"raw_tmp/forecast/{run_id}/"
        f"batch_{batch_id}/ultra_short_forecast.csv"
    )

    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=output.getvalue().encode("utf-8-sig"),
        ContentType="text/csv"
    )

    return key

def lambda_handler(event, context):
    bucket = os.environ["S3_RAW_BUCKET"]

    batch_id = event["batch_id"]
    locations = event["locations"]

    run_id = event.get(
        "run_id",
        datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d%H%M%S")
    )

    all_rows = []
    errors = []

    for location in locations:
        try:
            api_data = call_api(location)
            rows = parse_rows(location, api_data)
            all_rows.extend(rows)

        except Exception as e:
            logger.exception(f"API failed: {location}")
            errors.append({
                "location": location,
                "error": str(e)
            })

    s3_key = upload_csv(bucket, run_id, batch_id, all_rows)

    return {
        "run_id": run_id,
        "batch_id": batch_id,
        "s3_key": s3_key,
        "row_count": len(all_rows),
        "error_count": len(errors),
        "errors": errors[:5]
    }