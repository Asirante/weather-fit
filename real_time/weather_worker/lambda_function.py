import json
import os
import logging
import time
import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")

KST = ZoneInfo("Asia/Seoul")

WEATHER_API_URL = os.environ.get("WEATHER_API_URL")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")


def now_kst():
    return datetime.now(KST)


def iso_now_kst():
    return now_kst().isoformat()


def to_decimal_if_number(value):
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return ""

    try:
        return Decimal(str(value))
    except Exception:
        return value


def request_text_with_retry(
    url,
    retries=3,
    timeout=15,
    sleep_seconds=0.5
):
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            request = Request(url, method="GET")
            with urlopen(request, timeout=timeout) as response:
                return response.read().decode("utf-8")

        except HTTPError as e:
            last_error = e
            status = getattr(e, "code", None)

            if status in (429, 500, 502, 503, 504) and attempt < retries:
                wait = sleep_seconds * attempt
                logger.warning(
                    f"HTTPError {status}, retry {attempt}/{retries}, wait={wait}"
                )
                time.sleep(wait)
                continue

            raise

        except URLError as e:
            last_error = e

            if attempt < retries:
                wait = sleep_seconds * attempt
                logger.warning(
                    f"URLError retry {attempt}/{retries}, wait={wait}, error={e}"
                )
                time.sleep(wait)
                continue

            raise

    raise last_error


def get_ultra_short_nowcast_base_datetime():
    current = now_kst()

    if current.minute < 45:
        current -= timedelta(hours=1)

    current = current.replace(minute=0, second=0, microsecond=0)

    return current.strftime("%Y%m%d"), current.strftime("%H%M")


def get_ultra_short_nowcast(locations):
    if not WEATHER_API_URL or not WEATHER_API_KEY:
        raise ValueError("Missing WEATHER_API_URL or WEATHER_API_KEY")

    results = []

    base_date, base_time = get_ultra_short_nowcast_base_datetime()

    logger.info(
        f"Using weather base datetime: base_date={base_date}, base_time={base_time}"
    )

    for idx, row in enumerate(locations, start=1):
        try:
            nx = int(row["nx"])
            ny = int(row["ny"])
            regions = row.get("regions", [])

            params = {
                "ServiceKey": WEATHER_API_KEY,
                "pageNo": "1",
                "numOfRows": "1000",
                "dataType": "JSON",
                "base_date": base_date,
                "base_time": base_time,
                "nx": nx,
                "ny": ny,
            }

            url = f"{WEATHER_API_URL}?{urlencode(params)}"

            logger.info(
                f"Calling weather API ({idx}/{len(locations)}): "
                f"nx={nx}, ny={ny}, region_count={len(regions)}"
            )

            response_text = request_text_with_retry(url)
            api_data = json.loads(response_text)

            results.append({
                "regions": regions,
                "nx": nx,
                "ny": ny,
                "response": api_data,
            })

            time.sleep(0.03)

        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON response: nx={row.get('nx')}, ny={row.get('ny')}, error={e}"
            )
            continue

        except Exception as e:
            logger.error(
                f"Weather collection failed: nx={row.get('nx')}, ny={row.get('ny')}, error={e}"
            )
            continue

    logger.info(f"Collected weather payloads in batch: {len(results)}")

    return results


def build_weather_items(api_data):
    rows = []

    if not isinstance(api_data, list):
        logger.warning(f"build_weather_items expected list, got {type(api_data)}")
        return rows

    updated_at = iso_now_kst()

    for grid_result in api_data:
        region_nx = grid_result.get("nx", "")
        region_ny = grid_result.get("ny", "")
        regions = grid_result.get("regions", [])

        payload = grid_result.get("response", {})

        items = (
            payload.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )

        if isinstance(items, dict):
            items = [items]

        if not isinstance(items, list):
            logger.warning(
                f"Unexpected weather items type: nx={region_nx}, ny={region_ny}, type={type(items)}"
            )
            continue

        for region in regions:
            region_code = region.get("region_code", "")
            region_name = region.get("region_name", "")

            for item in items:
                rows.append({
                    "region_code": region_code,
                    "region_name": region_name,
                    "region_nx": str(region_nx),
                    "region_ny": str(region_ny),

                    "baseDate": item.get("baseDate", ""),
                    "baseTime": item.get("baseTime", ""),
                    "category": item.get("category", ""),

                    "nx": str(item.get("nx", "")),
                    "ny": str(item.get("ny", "")),
                    "obsrValue": to_decimal_if_number(item.get("obsrValue", "")),
                    "updatedAt": updated_at,
                })

    return rows


def save_nowcast_to_dynamodb(api_data, table_name):
    table = dynamodb.Table(table_name)
    rows = build_weather_items(api_data)

    if not rows:
        logger.warning("No weather rows parsed from nowcast API")
        return 0

    saved_count = 0
    skipped_count = 0

    with table.batch_writer() as batch:
        for row in rows:
            try:
                if (
                    not row.get("region_code")
                    or not row.get("baseDate")
                    or not row.get("baseTime")
                    or not row.get("category")
                ):
                    skipped_count += 1
                    continue

                batch.put_item(Item=row)
                saved_count += 1

            except Exception as e:
                skipped_count += 1
                logger.error(f"Skipping invalid weather item: row={row}, error={e}")

    logger.info(
        f"Saved weather items: saved={saved_count}, skipped={skipped_count}"
    )

    return saved_count


def read_latest_uv_index_csv(bucket, prefix):
    # 페이지네이션: 파일이 1000개를 넘어도 최신 CSV를 놓치지 않도록 전체 조회
    objects = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects.extend(page.get("Contents", []))

    csv_files = [
        obj for obj in objects
        if obj["Key"].endswith(".csv")
    ]

    if not csv_files:
        logger.warning(f"No UV index csv found under prefix={prefix}")
        return []

    latest = max(csv_files, key=lambda x: x["LastModified"])
    key = latest["Key"]

    logger.info(f"Reading latest UV index csv: s3://{bucket}/{key}")

    obj = s3_client.get_object(
        Bucket=bucket,
        Key=key
    )

    text = obj["Body"].read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    return list(reader)



def build_uv_index_items(rows):
    items = []
    updated_at = iso_now_kst()

    keep_columns = [
        "h0", "h3", "h6"
    ]

    for row in rows:
        region_code = str(row.get("areaNo", "")).strip()
        region_name = row.get("areaNm", "")

        if not region_code:
            continue

        item = {
            "region_code": region_code,
            "region_name": region_name,
            "category": "UV_INDEX",
            "code": row.get("code", ""),
            "date": str(row.get("date", "")).strip(),
            "updatedAt": updated_at,
        }

        for col in keep_columns:
            item[col] = to_decimal_if_number(row.get(col, ""))

        items.append(item)

    return items



def save_uv_index_to_dynamodb(table_name, bucket, prefix):
    table = dynamodb.Table(table_name)

    rows = read_latest_uv_index_csv(bucket, prefix)
    items = build_uv_index_items(rows)

    if not items:
        logger.warning("No UV index items parsed")
        return 0

    saved_count = 0
    skipped_count = 0

    with table.batch_writer() as batch:
        for item in items:
            try:
                if (
                    not item.get("region_code")
                    or not item.get("category")
                ):
                    skipped_count += 1
                    continue

                batch.put_item(Item=item)
                saved_count += 1

            except Exception as e:
                skipped_count += 1
                logger.error(f"Skipping invalid UV item: item={item}, error={e}")

    logger.info(
        f"Saved UV index items: saved={saved_count}, skipped={skipped_count}"
    )

    return saved_count



def lambda_handler(event, context):
    weather_table_name = os.environ.get("WEATHER_DYNAMODB_TABLE_NAME")

    if not weather_table_name:
        raise ValueError("Missing WEATHER_DYNAMODB_TABLE_NAME")

    batch_id = event.get("batch_id", "unknown")
    locations = event.get("items", [])

    if not locations:
        raise ValueError("No batch items provided")

    logger.info(
        f"Starting weather batch: batch_id={batch_id}, size={len(locations)}"
    )

    nowcast_data = get_ultra_short_nowcast(locations)

    saved_count = save_nowcast_to_dynamodb(
    nowcast_data,
    weather_table_name
)

    uv_saved_count = 0

    if str(batch_id) == "0":
        uv_bucket = os.environ.get("S3_RAW_BUCKET")
        uv_prefix = os.environ.get("UV_INDEX_PREFIX", "raw/weather/uv_index/")

        if uv_bucket:
            uv_saved_count = save_uv_index_to_dynamodb(
                table_name=weather_table_name,
                bucket=uv_bucket,
                prefix=uv_prefix
            )

    return {
        "statusCode": 200,
        "message": "Weather batch saved successfully",
        "batchId": batch_id,
        "batchSize": len(locations),
        "collectedPayloadCount": len(nowcast_data),
        "savedWeatherCount": saved_count,
        "savedUvIndexCount": uv_saved_count,
    }