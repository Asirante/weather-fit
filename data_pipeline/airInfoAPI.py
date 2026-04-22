import json
import os
import logging
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ENDPOINTS = {
    "forecast_weekly": "/getMinuDustWeekFrcstDspth",
}


def call_api(endpoint, extra_params=None):
    base_url = os.environ.get("AIR_INFO_API_URL")
    service_key = os.environ.get("WEATHER_API_KEY")

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
    request = Request(url, method="GET")

    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))

def get_minu_dust_week_frcst_dspth():
    return call_api(ENDPOINTS["forecast_weekly"])