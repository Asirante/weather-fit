import json
import os
import logging
import concurrent.futures
from urllib.request import Request, urlopen
from urllib.parse import urlencode

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ENDPOINTS = {
    "ctprvn_avg": "/getCtprvnMesureLIst",
    "sigungu_avg": "/getCtprvnMesureSidoLIst"
}


# 데이터 받는 지역 전범위로 확대
SIDO_NAMES = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산",
    "경기", "강원", "충북", "충남", "전북", "전남",
    "경북", "경남", "제주", "세종"
]

#SIDO_NAMES = ["인천"]

ITEM_CODES = ["SO2", "CO", "O3", "NO2", "PM10"]

def call_api(endpoint, extra_params=None):
    base_url = os.environ.get("AIR_STATS_API_URL")
    service_key = os.environ.get("WEATHER_API_KEY")

    if not base_url or not service_key:
        raise ValueError("Missing AIR_STATS_API_URL or AIR_API_KEY")

    params = {
        "serviceKey": service_key,
        "returnType": "json",
        "pageNo": "1",
        "numOfRows": "1000"
    }

    if extra_params:
        params.update(extra_params)

    url = f"{base_url}{endpoint}?{urlencode(params)}"
    logger.info(f"Calling Air Stats API: {url}")

    request = Request(url, method="GET")
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))

def get_ctprvn_measure_list(item_code):
    return call_api(
        ENDPOINTS["ctprvn_avg"],
        {"itemCode": item_code,
         "dataGubun": "DAILY",
         "searchCondition": "MONTH"}
    )

def get_ctprvn_measure_sido_list(sido_name="서울"):
    return call_api(
        ENDPOINTS["sigungu_avg"],
        {
            "sidoName": sido_name,
            "searchCondition": "DAILY"
        }
    )

def collect_air_stats_data():
    ctprvn_avg = {}
    sigungu_avg = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        ctprvn_futures = {
            executor.submit(get_ctprvn_measure_list, item_code): item_code
            for item_code in ITEM_CODES
        }

        sigungu_futures = {
            executor.submit(get_ctprvn_measure_sido_list, sido_name): sido_name
            for sido_name in SIDO_NAMES
        }

        for future in concurrent.futures.as_completed(ctprvn_futures):
            item_code = ctprvn_futures[future]
            try:
                ctprvn_avg[item_code] = future.result()
            except Exception as e:
                logger.exception(f"ctprvn_avg failed for itemCode={item_code}: {e}")

        for future in concurrent.futures.as_completed(sigungu_futures):
            sido_name = sigungu_futures[future]
            try:
                sigungu_avg.append(future.result())
            except Exception as e:
                logger.exception(f"sigungu_avg failed for sidoName={sido_name}: {e}")

    return {
        "ctprvn_avg": ctprvn_avg,
        "sigungu_avg": sigungu_avg
    }