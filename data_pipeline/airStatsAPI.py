import json
import os
import time
import logging
import concurrent.futures
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def fetch_json_with_retry(url, retries=3, timeout=15, sleep_seconds=0.5):
    """일시적 오류(429/5xx, 네트워크)에 한해 지수 백오프로 재시도.
    그 외 오류는 즉시 raise (과도한 재요청으로 차단되지 않도록 보수적으로)."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            request = Request(url, method="GET")
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            last_error = e
            if getattr(e, "code", None) in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(sleep_seconds * attempt)
                continue
            raise
        except URLError as e:
            last_error = e
            if attempt < retries:
                time.sleep(sleep_seconds * attempt)
                continue
            raise
    raise last_error

ENDPOINTS = {
    "ctprvn_avg": "/getCtprvnMesureLIst",
    "sigungu_avg": "/getCtprvnMesureSidoLIst"
}


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
        raise ValueError("Missing AIR_STATS_API_URL or WEATHER_API_KEY")

    params = {
        "serviceKey": service_key,
        "returnType": "json",
        "pageNo": "1",
        "numOfRows": "1000"
    }

    if extra_params:
        params.update(extra_params)

    url = f"{base_url}{endpoint}?{urlencode(params)}"
    # 서비스키가 URL에 포함되므로 전체 URL을 로그에 남기지 않음 (엔드포인트만)
    logger.info(f"Calling Air Stats API: {endpoint}")

    return fetch_json_with_retry(url)

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