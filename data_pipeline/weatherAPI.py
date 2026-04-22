import json
import os
import csv
import logging
import boto3
import io
import concurrent.futures
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed

# 엔드포인드 정의
ENDPOINTS = {
    "apparent_temperature": "/getSenTaIdxV4",
    "uv_index": "/getUVIdxV4",
    "air_diffusion": "/getAirDiffusionIdxV4"
}

# S3클라이언트, 로거 
s3_client = boto3.client("s3")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


LOCATION_BUCKET = "inhatc-team2-5-raw-data"
LOCATION_KEY = "location.csv"


def load_locations():
    response = s3_client.get_object(
        Bucket=LOCATION_BUCKET,
        Key=LOCATION_KEY
    )
    lines = response["Body"].read().decode("utf-8-sig").splitlines()
    reader = csv.DictReader(lines)
    return list(reader)


# API 호출 함수
def call_api(endpoint, area_no, extra_params=None):
    base_url = os.environ.get("WEATHER_API_URL")
    service_key = os.environ.get("WEATHER_API_KEY")

    if not base_url or not service_key:
        raise ValueError("Missing API config")

    params = {
        "ServiceKey": service_key,
        "pageNo": "1",
        "numOfRows": "100",
        "dataType": "JSON",
        "time": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d%H"),
        "areaNo": area_no
    }

    if extra_params:
        params.update(extra_params)

    url = f"{base_url}{endpoint}?{urlencode(params)}"
    request = Request(url, method="GET")

    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


"""
def get_apparent_temperature():
    return call_api(
        ENDPOINTS["apparent_temperature"],
        {"requestCode": "A47"}
    )
"""


def get_uv_index(area_no):
    return call_api(ENDPOINTS["uv_index"], area_no)



def get_air_diffusion(area_no):
    return call_api(ENDPOINTS["air_diffusion"], area_no)



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
            "response": get_uv_index(area_no)
        }
    except Exception as e:
        logger.exception(f"uv_index failed for {area_no}: {e}")

    try:
        result["air_diffusion"] = {
            "areaNo": area_no,
            "areaNm": area_name,
            "response": get_air_diffusion(area_no)
        }
    except Exception as e:
        logger.exception(f"air_diffusion failed for {area_no}: {e}")

    return result



def collect_weather_data():
    locations = load_locations()

    aggregated = {
        "uv_index": [],
        "air_diffusion": []
    }

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(collect_one_location, loc) for loc in locations]

        for future in as_completed(futures):
            location_result = future.result()

            if location_result is None:
                continue

            for api_name in aggregated.keys():
                if location_result.get(api_name) is not None:
                    aggregated[api_name].append(location_result[api_name])

    return aggregated
