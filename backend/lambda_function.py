import json
import math
import boto3
import os
from urllib.parse import parse_qs
from decimal import Decimal
from boto3.dynamodb.conditions import Key

from mapping import gu_to_station, region_to_code

IS_LOCAL = os.environ.get("AWS_SAM_LOCAL") == "true"

if IS_LOCAL:
    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url="http://dynamodb-local:8000",
        region_name="us-east-1",
        aws_access_key_id="local",
        aws_secret_access_key="local",
    )
else:
    dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ.get(
    "TABLE_NAME", "inhatc-team2-1-recommend-cache"
)
AIR_TABLE_NAME = os.environ.get(
    "AIR_TABLE_NAME", "inhatc-team2-5-air-cache"
)
WEATHER_TABLE_NAME = os.environ.get(
    "WEATHER_TABLE_NAME", "inhatc-team2-5-weather-cache"
)
FORECAST_TABLE_NAME = os.environ.get(
    "FORECAST_TABLE_NAME", "inhatc-team2-5-forecast-cache"
)

recommend_table = dynamodb.Table(TABLE_NAME)
air_table = dynamodb.Table(AIR_TABLE_NAME)
weather_table = dynamodb.Table(WEATHER_TABLE_NAME)
forecast_table = dynamodb.Table(FORECAST_TABLE_NAME)


def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def safe_float(value, default=0.0):
    if value is None:
        return default
    s = str(value).strip().lstrip("'")
    if not s or s == "-":
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def calc_apparent_temp(temp, wind_ms, humidity):
    """기상청 기준 체감온도 계산.

    - 저온(<=10도) + 바람: 풍속냉각(Wind Chill)
    - 고온(>=25도) + 습도: 습도 기반(여름철 체감온도, 습구온도 이용)
    - 그 외: 기온과 거의 동일하므로 기온 그대로 반환
    풍속은 m/s, 습도는 %.
    """
    if temp is None:
        return None

    # 겨울철 풍속냉각 (바람 4.8km/h=약 1.3m/s 이상에서만 유의미)
    if temp <= 10 and wind_ms is not None and wind_ms >= 1.3:
        v = wind_ms * 3.6  # m/s -> km/h
        v_pow = v ** 0.16
        at = 13.12 + 0.6215 * temp - 11.37 * v_pow + 0.3965 * v_pow * temp
        return round(at, 1)

    # 여름철 습도 기반 체감온도
    if temp >= 25 and humidity:
        rh = humidity
        tw = (
            temp * math.atan(0.151977 * (rh + 8.313659) ** 0.5)
            + math.atan(temp + rh)
            - math.atan(rh - 1.67633)
            + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
            - 4.686035
        )
        at = (
            -0.2442 + 0.55399 * tw + 0.45535 * temp
            - 0.0022 * tw ** 2 + 0.00278 * tw * temp + 3.0
        )
        return round(at, 1)

    return round(temp, 1)


# ──────────────────────────────────────────────
# 패턴 키 빌드 함수
# ──────────────────────────────────────────────


def get_temp_zone(temp):
    if temp >= 35:
        return "35over"
    elif temp >= 30:
        return "30-34"
    elif temp >= 25:
        return "25-29"
    elif temp >= 20:
        return "20-24"
    elif temp >= 15:
        return "15-19"
    elif temp >= 10:
        return "10-14"
    elif temp >= 5:
        return "5-9"
    elif temp >= 0:
        return "0-4"
    elif temp >= -10:
        return "-10--1"
    else:
        return "under-11"


def get_diff_level(diff):
    if diff <= 2:
        return "none"
    elif diff <= 5:
        return "small"
    elif diff <= 8:
        return "normal"
    elif diff <= 12:
        return "large"
    else:
        return "xlarge"


def get_rain_level_from_value(rn1):
    if rn1 <= 0:
        return "none"
    elif rn1 < 1:
        return "drizzle"
    elif rn1 < 3:
        return "light"
    elif rn1 < 15:
        return "moderate"
    else:
        return "heavy"


def get_rain_level_from_str(rn1_str):
    s = str(rn1_str).strip()
    if s in ("강수없음", "0", ""):
        return "none"
    if "미만" in s:
        return "drizzle"
    try:
        val = float(
            s.split("~")[0].replace("mm", "").strip()
        )
        if val >= 15:
            return "heavy"
        elif val >= 3:
            return "moderate"
        elif val >= 1:
            return "light"
        else:
            return "drizzle"
    except (ValueError, IndexError):
        return "none"


RAIN_RANK = {
    "none": 0,
    "drizzle": 1,
    "light": 2,
    "moderate": 3,
    "heavy": 4,
}


def get_pm_grade(pm10_grade, pm25_grade):
    if pm25_grade in ("3", "4") or pm10_grade == "4":
        return "very_bad"
    elif pm10_grade == "3":
        return "bad"
    elif pm10_grade == "2":
        return "normal"
    else:
        return "good"


def get_wind_level(wsd):
    if wsd >= 3:
        return "strong"
    elif wsd >= 2:
        return "moderate"
    else:
        return "calm"


def get_uv_level(uv_max):
    if uv_max >= 6:
        return "high"
    elif uv_max >= 3:
        return "normal"
    else:
        return "low"


def get_pty_type(pty_codes):
    codes = [str(c).strip() for c in pty_codes]
    if "3" in codes:
        return "snow"
    if any(c in ("1", "2", "4") for c in codes):
        return "rain"
    return "none"


def build_sk(
    temp_zone,
    diff_level,
    rain_level,
    pm_grade,
    wind_level,
    uv_level,
    pty_type,
):
    return (
        f"temp:{temp_zone}|diff:{diff_level}|rain:{rain_level}"
        f"|pm:{pm_grade}|wind:{wind_level}|uv:{uv_level}|pty:{pty_type}"
    )


# ──────────────────────────────────────────────
# DynamoDB 조회
# ──────────────────────────────────────────────


def query_weather(region_code):
    response = weather_table.query(
        KeyConditionExpression=Key("region_code").eq(
            region_code
        )
    )
    weather_map = {}
    for item in response.get("Items", []):
        cat = item.get("category", "")
        if cat:
            weather_map[cat] = item
    return weather_map


def query_forecast(region_code):
    response = forecast_table.query(
        KeyConditionExpression=Key("region_code").eq(
            region_code
        )
    )
    return response.get("Items", [])


def parse_forecast_series(forecast_items):
    series = {}
    for item in forecast_items:
        cat = item.get("category", "")
        fcst_time = item.get("fcstDate", "") + item.get(
            "fcstTime", ""
        )
        if cat not in series:
            series[cat] = []
        series[cat].append(
            {
                "time": fcst_time,
                "value": item.get("fcstValue", ""),
            }
        )

    for cat in series:
        series[cat].sort(key=lambda x: x["time"])

    return series


def build_pattern(weather_map, forecast_items, air_data):
    series = parse_forecast_series(forecast_items)

    t1h_values = [
        safe_float(v["value"])
        for v in series.get("T1H", [])
    ]
    if t1h_values:
        temp_min = min(t1h_values)
        temp_zone = get_temp_zone(temp_min)
        diff = max(t1h_values) - temp_min
        diff_level = get_diff_level(diff)
    else:
        temp = safe_float(
            weather_map.get("T1H", {}).get("obsrValue")
        )
        temp_zone = get_temp_zone(temp)
        diff_level = "normal"

    rn1_values = series.get("RN1", [])
    if rn1_values:
        max_rain = "none"
        for v in rn1_values:
            level = get_rain_level_from_str(v["value"])
            if RAIN_RANK.get(level, 0) > RAIN_RANK.get(
                max_rain, 0
            ):
                max_rain = level
        rain_level = max_rain
    else:
        rn1 = safe_float(
            weather_map.get("RN1", {}).get("obsrValue")
        )
        rain_level = get_rain_level_from_value(rn1)

    pm10_grade = str(air_data.get("pm10Grade", ""))
    pm25_grade = str(air_data.get("pm25Grade", ""))
    pm_grade = get_pm_grade(pm10_grade, pm25_grade)

    wsd_values = [
        safe_float(v["value"])
        for v in series.get("WSD", [])
    ]
    if wsd_values:
        wind_level = get_wind_level(max(wsd_values))
    else:
        wsd = safe_float(
            weather_map.get("WSD", {}).get("obsrValue")
        )
        wind_level = get_wind_level(wsd)

    uv_item = weather_map.get("UV_INDEX", {})
    uv_max = max(
        safe_float(uv_item.get("h0")),
        safe_float(uv_item.get("h3")),
        safe_float(uv_item.get("h6")),
    )
    uv_level = get_uv_level(uv_max)

    pty_values = series.get("PTY", [])
    if pty_values:
        pty_codes = [v["value"] for v in pty_values]
        pty_type = get_pty_type(pty_codes)
    else:
        pty_code = str(
            weather_map.get("PTY", {}).get("obsrValue", "0")
        )
        pty_type = get_pty_type([pty_code])

    return build_sk(
        temp_zone,
        diff_level,
        rain_level,
        pm_grade,
        wind_level,
        uv_level,
        pty_type,
    )


def lambda_handler(event, context):
    try:
        raw_qs = event.get("rawQueryString", "")
        params = parse_qs(raw_qs)
        path = event.get("rawPath", "/")

        region_code = params.get("region_code", [""])[0]
        region = params.get("region", [""])[0]

        if not region_code and not region:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "region_code 또는 region 파라미터가 필요합니다."
                    },
                    ensure_ascii=False,
                ),
            }

        if not region_code and region:
            region_code = region_to_code.get(region, "")

        # ── 1. 기상 데이터 조회 (weather-cache) ──
        weather_map = {}
        region_name = region

        if region_code:
            weather_map = query_weather(region_code)

            if weather_map and not region_name:
                for item in weather_map.values():
                    if item.get("region_name"):
                        region_name = item.get(
                            "region_name"
                        )
                        break

        if not weather_map:
            return {
                "statusCode": 404,
                "body": json.dumps(
                    {
                        "error": "해당 지역의 기상 데이터를 찾을 수 없습니다."
                    },
                    ensure_ascii=False,
                ),
            }

        # ── 2. 대기질 데이터 조회 (air-cache) ──
        station_key = gu_to_station.get(region_name)
        if not station_key:
            parts = region_name.split()
            if len(parts) >= 2:
                short_region = f"{parts[0]} {parts[1]}"
                station_key = gu_to_station.get(
                    short_region
                )

        air_data = {}

        if station_key:
            air_response = air_table.get_item(
                Key={"stationKey": station_key}
            )
            air_data = air_response.get("Item", {})

        pm10_val = safe_float(air_data.get("pm10Value"))
        pm25_val = safe_float(air_data.get("pm25Value"))
        pm10_grade = str(
            air_data.get("pm10Grade", "")
        ).strip()
        pm25_grade = str(
            air_data.get("pm25Grade", "")
        ).strip()

        # 등급이 비어있으면 수치로 직접 채우기
        if not pm10_grade and pm10_val > 0:
            if pm10_val <= 30:
                pm10_grade = "1"
            elif pm10_val <= 80:
                pm10_grade = "2"
            elif pm10_val <= 150:
                pm10_grade = "3"
            else:
                pm10_grade = "4"

        if not pm25_grade and pm25_val > 0:
            if pm25_val <= 15:
                pm25_grade = "1"
            elif pm25_val <= 35:
                pm25_grade = "2"
            elif pm25_val <= 75:
                pm25_grade = "3"
            else:
                pm25_grade = "4"

        # 보정된 데이터를 딕셔너리에 다시 덮어씌움
        air_data["pm10Value"] = pm10_val
        air_data["pm25Value"] = pm25_val
        air_data["pm10Grade"] = pm10_grade
        air_data["pm25Grade"] = pm25_grade

        # ── 3. 경로별 응답 ──
        if path == "/recommend":
            forecast_items = query_forecast(region_code)
            sk = build_pattern(
                weather_map, forecast_items, air_data
            )

            rec_response = recommend_table.get_item(
                Key={"PK": "weather_pattern", "SK": sk}
            )
            rec_data = rec_response.get("Item")

            if not rec_data:
                return {
                    "statusCode": 404,
                    "body": json.dumps(
                        {
                            "error": "해당 패턴의 추천 데이터가 없습니다.",
                            "pattern": sk,
                        },
                        ensure_ascii=False,
                    ),
                }

            result = {
                "pattern": sk,
                "top": rec_data.get("top", []),
                "bottom": rec_data.get("bottom", []),
                "mask": rec_data.get("mask", ""),
                "pack": rec_data.get("pack", ""),
                "acc": rec_data.get("acc", []),
                "reason": rec_data.get("reason", ""),
            }

            return {
                "statusCode": 200,
                "body": json.dumps(
                    result,
                    ensure_ascii=False,
                    default=decimal_to_float,
                ),
            }

        elif path == "/weather":
            forecast_items = query_forecast(region_code)
            series = parse_forecast_series(forecast_items)

            temp_list = [
                safe_float(v["value"])
                for v in series.get("T1H", [])
            ]
            rain_list = [
                v["value"] for v in series.get("RN1", [])
            ]
            pty_list = [
                v["value"] for v in series.get("PTY", [])
            ]
            sky_list = [
                v["value"] for v in series.get("SKY", [])
            ]
            reh_list = [
                safe_float(v["value"])
                for v in series.get("REH", [])
            ]
            wsd_list = [
                safe_float(v["value"])
                for v in series.get("WSD", [])
            ]

            # 시간대별 체감온도 (기온 배열 기준, 같은 인덱스의 습도/풍속 사용)
            feels_like_forecast = []
            for i, t in enumerate(temp_list):
                wind_i = wsd_list[i] if i < len(wsd_list) else None
                reh_i = reh_list[i] if i < len(reh_list) else 0
                feels_like_forecast.append(
                    calc_apparent_temp(t, wind_i, reh_i)
                )

            sky_result = []
            for i in range(len(sky_list)):
                pty = (
                    str(pty_list[i]).strip()
                    if i < len(pty_list)
                    else "0"
                )
                sky = str(sky_list[i]).strip()

                if pty in ("1", "2", "4"):
                    sky_result.append("비")
                elif pty == "3":
                    sky_result.append("눈")
                elif sky in ("1", "2"):
                    sky_result.append("맑음")
                else:
                    sky_result.append("흐림")

            current_temp = safe_float(
                weather_map.get("T1H", {}).get("obsrValue")
            )

            # 현재(실황) 체감온도
            current_wind = safe_float(
                weather_map.get("WSD", {}).get("obsrValue")
            )
            current_reh = safe_float(
                weather_map.get("REH", {}).get("obsrValue")
            )
            current_feels_like = calc_apparent_temp(
                current_temp, current_wind, current_reh
            )

            uv_item = weather_map.get("UV_INDEX", {})
            uv_max = max(
                safe_float(uv_item.get("h0")),
                safe_float(uv_item.get("h3")),
                safe_float(uv_item.get("h6")),
            )

            base_date = ""
            base_time = ""
            for item in weather_map.values():
                if item.get(
                    "category"
                ) != "UV_INDEX" and item.get("baseDate"):
                    base_date = item.get("baseDate", "")
                    base_time = item.get("baseTime", "")
                    break

            filtered_data = {
                "region_code": region_code,
                "region_name": region_name,
                "baseDate": base_date,
                "baseTime": base_time,
                "temp": current_temp,
                "feelsLike": current_feels_like,
                "tempForecast": temp_list,
                "feelsLikeForecast": feels_like_forecast,
                "rain": rain_list,
                "sky": sky_result,
                "uv": uv_max,
                "o3": air_data.get("o3Value"),
                "pm10": air_data.get("pm10Value"),
                "pm10Grade": air_data.get("pm10Grade"),
                "pm25": air_data.get("pm25Value"),
                "pm25Grade": air_data.get("pm25Grade"),
            }

            return {
                "statusCode": 200,
                "body": json.dumps(
                    filtered_data,
                    ensure_ascii=False,
                    default=decimal_to_float,
                ),
            }

        else:
            return {
                "statusCode": 404,
                "body": json.dumps(
                    {"error": "잘못된 API 경로입니다."},
                    ensure_ascii=False,
                ),
            }

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": "서버 내부 오류가 발생했습니다."},
                ensure_ascii=False,
            ),
        }
