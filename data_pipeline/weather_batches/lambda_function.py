import json
import os
import csv
import io
import logging
import boto3
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.parse import urlencode

s3_client = boto3.client("s3")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

LOCATION_BUCKET = "inhatc-team2-5-raw-data"
LOCATION_KEY = "location.csv"

ENDPOINTS = {
    "uv_index": "/getUVIdxV4",
    "air_diffusion": "/getAirDiffusionIdxV4"
}


def load_locations():
    response = s3_client.get_object(
        Bucket=LOCATION_BUCKET,
        Key=LOCATION_KEY
    )
    lines = response["Body"].read().decode("utf-8-sig").splitlines()
    reader = csv.DictReader(lines)
    return list(reader)


def call_api(endpoint, area_no):
    base_url = os.environ.get("WEATHER_API_URL")
    service_key = os.environ.get("WEATHER_API_KEY")

    if not base_url or not service_key:
        raise ValueError("Missing WEATHER_API_URL or WEATHER_API_KEY")

    params = {
        "ServiceKey": service_key,
        "pageNo": "1",
        "numOfRows": "100",
        "dataType": "JSON",
        "time": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d%H"),
        "areaNo": area_no
    }

    url = f"{base_url}{endpoint}?{urlencode(params)}"
    request = Request(url, method="GET")

    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def collect_one_location(location):
    area_no = str(location["행정구역코드"])

    area_name = " ".join(filter(None, [
        location.get("1단계"),
        location.get("2단계"),
        location.get("3단계")
    ]))

    result = {
        "uv_index": None,
        "air_diffusion": None
    }

    try:
        result["uv_index"] = {
            "areaNo": area_no,
            "areaNm": area_name,
            "response": call_api(ENDPOINTS["uv_index"], area_no)
        }
    except Exception as e:
        logger.exception(f"uv_index failed for {area_no}: {e}")

    try:
        result["air_diffusion"] = {
            "areaNo": area_no,
            "areaNm": area_name,
            "response": call_api(ENDPOINTS["air_diffusion"], area_no)
        }
    except Exception as e:
        logger.exception(f"air_diffusion failed for {area_no}: {e}")

    return result


def parse_uv_index_and_air_diffusion(api_data_list):
    rows = []

    for region_data in api_data_list:
        area_no = region_data.get("areaNo", "")
        area_name = region_data.get("areaNm", "")
        response_data = region_data.get("response", {})

        items = (
            response_data.get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )

        if isinstance(items, dict):
            items = [items]

        for item in items:
            row = {
                "areaNo": area_no,
                "areaNm": area_name
            }
            row.update(item)
            rows.append(row)

    return rows


def upload_csv(bucket_name, key, rows):
    if not rows:
        logger.warning(f"No rows to upload: {key}")
        return None

    output = io.StringIO()
    fieldnames = list(rows[0].keys())

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=output.getvalue().encode("utf-8-sig"),
        ContentType="text/csv"
    )

    logger.info(f"Uploaded: s3://{bucket_name}/{key}")
    return key


def lambda_handler(event, context):
    bucket_name = os.environ["S3_RAW_BUCKET"]

    run_id = event.get("run_id")
    if not run_id:
        run_id = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d%H%M%S")

    batch_index = int(event.get("batch_index", 0))
    batch_size = int(event.get("batch_size", 30))

    locations = load_locations()

    start = batch_index * batch_size
    end = start + batch_size
    batch_locations = locations[start:end]

    aggregated = {
        "uv_index": [],
        "air_diffusion": []
    }

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(collect_one_location, loc)
            for loc in batch_locations
        ]

        for future in as_completed(futures):
            location_result = future.result()

            for api_name in aggregated.keys():
                if location_result.get(api_name):
                    aggregated[api_name].append(location_result[api_name])

    uploaded_keys = []

    for api_name, api_data in aggregated.items():
        rows = parse_uv_index_and_air_diffusion(api_data)

        key = f"raw_tmp/weather/{run_id}/batch_{batch_index}/{api_name}.csv"
        uploaded_key = upload_csv(bucket_name, key, rows)

        if uploaded_key:
            uploaded_keys.append(uploaded_key)

    return {
        "statusCode": 200,
        "run_id": run_id,
        "batch_index": batch_index,
        "batch_size": batch_size,
        "uploaded_keys": uploaded_keys
    }