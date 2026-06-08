import json
import os
import time
import logging
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ENDPOINTS = {
    "forecast_weekly": "/getMinuDustWeekFrcstDspth",
}


def fetch_json_with_retry(url, retries=3, timeout=15, sleep_seconds=0.5):
    """일시적 오류(429/5xx, 네트워크)에 한해 지수 백오프로 재시도. 그 외는 즉시 raise."""
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


def call_api(endpoint, extra_params=None):
    base_url = os.environ.get("AIR_INFO_API_URL")
    service_key = os.environ.get("WEATHER_API_KEY")

    if not base_url or not service_key:
        raise ValueError("Missing AIR_INFO_API_URL or WEATHER_API_KEY")

    params = {
        "serviceKey": service_key,
        "returnType": "json",
        "numOfRows": "1000",
        "pageNo": "1",
        "searchDate": (datetime.now(ZoneInfo("Asia/Seoul")) - timedelta(days=1)).strftime("%Y-%m-%d")
    }

    if extra_params:
        params.update(extra_params)

    url = f"{base_url}{endpoint}?{urlencode(params)}"
    return fetch_json_with_retry(url)

def get_minu_dust_week_frcst_dspth():
    return call_api(ENDPOINTS["forecast_weekly"])