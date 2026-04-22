import json
import os
import time
import logging
import boto3
import csv
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ENDPOINTS = {
    "ultra_short_forecast": "/getUltraSrtFcst",
    #"short_forecast": "/getVilageFcst"
}

s3_client = boto3.client("s3")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

"""
def get_short_forecast_base_datetime():
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    base_times = ["0500", "0800", "1100", "1400", "1700", "2000", "2300"]

    current_time = now.strftime("%H%M")
    available_times = [t for t in base_times if t <= current_time]

    if available_times:
        return now.strftime("%Y%m%d"), available_times[-1]
    else:
        yesterday = now - timedelta(days=1)
        return yesterday.strftime("%Y%m%d"), "2300"
"""

def get_ultra_short_forecast_base_datetime():
    now = datetime.now(ZoneInfo("Asia/Seoul")) - timedelta(hours=1)
    return now.strftime("%Y%m%d"), now.strftime("%H00")


def get_base_datetime(endpoint):
    """
    if endpoint == ENDPOINTS["short_forecast"]:
        return get_short_forecast_base_datetime()
    elif endpoint == ENDPOINTS["ultra_short_forecast"]:
        return get_ultra_short_forecast_base_datetime()
    """
    if endpoint == ENDPOINTS["ultra_short_forecast"]:
        return get_ultra_short_forecast_base_datetime()
    else:
        raise ValueError(f"Unknown endpoint: {endpoint}")


# 좌표 불러오기(중복격자 제거)
def load_locations():
    response = s3_client.get_object(
        Bucket="inhatc-team2-5-raw-data",
        Key="location.csv"
    )
    lines = response["Body"].read().decode("utf-8-sig").splitlines()
    reader = csv.DictReader(lines)

    unique = {}
    for row in reader:
        key = (row["격자 X"], row["격자 Y"])
        if key not in unique:
            unique[key] = row

    return list(unique.values())


def call_api(endpoint, extra_params=None):
    base_url = os.environ.get("FORECAST_API_URL")
    service_key = os.environ.get("WEATHER_API_KEY")

    if not base_url or not service_key:
        raise ValueError("Missing API config")

    locations = load_locations()
    results = []
    base_date, base_time = get_base_datetime(endpoint)
    

    for row in locations:
        region_code = row["행정구역코드"]
        region_name = " ".join(filter(None, [row.get("1단계"), row.get("2단계"), row.get("3단계")]))
        nx = int(row["격자 X"])
        ny = int(row["격자 Y"])

        now = datetime.now(ZoneInfo("Asia/Seoul"))
        params = {
            "ServiceKey": service_key,
            "pageNo": "1",
            "numOfRows": "1000",
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": nx,
            "ny": ny
        }

        if extra_params:
            params.update(extra_params)

        url = f"{base_url}{endpoint}?{urlencode(params)}"
        logger.info(f"Calling API: {url}")


        request = Request(url, method="GET")
        with urlopen(request) as response:
            api_data = json.loads(response.read().decode("utf-8"))

        results.append({
            "region_code": region_code,
            "region_name": region_name,
            "nx": nx,
            "ny": ny,
            "response": api_data
        })
        time.sleep(1)

    return results


def get_ultra_short_forecast():
    return call_api(ENDPOINTS["ultra_short_forecast"])

"""
def get_short_forecast():
    return call_api(ENDPOINTS["short_forecast"])
"""

def collect_forecast_data():
    return {
        "ultra_short_forecast": get_ultra_short_forecast(),
        #"short_forecast": get_short_forecast()
    }