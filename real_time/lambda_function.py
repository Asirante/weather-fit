import json
import os
import logging
import csv
import re
import time
from functools import lru_cache
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import boto3

# -------------------------------------------------
# 기본 설정
# -------------------------------------------------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

KST = ZoneInfo("Asia/Seoul")

LOCATION_BUCKET = os.environ.get(
    "LOCATION_BUCKET", "inhatc-team2-5-raw-data"
)
LOCATION_KEY = os.environ.get(
    "LOCATION_KEY", "location.csv"
)

WEATHER_API_URL = os.environ.get("WEATHER_API_URL")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")

AIR_POLLUTION_API_URL = os.environ.get(
    "AIR_POLLUTION_API_URL"
)
AIR_API_KEY = os.environ.get("AIR_API_KEY")

"""
SIDO_LIST = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산",
    "경기", "강원", "충북", "충남", "전북", "전남",
    "경북", "경남", "제주", "세종"
]"""

SIDO_LIST = ["인천"]


# --------------------------------------------------
# 공통 유틸
# --------------------------------------------------
def now_kst() -> datetime:
    return datetime.now(KST)


def iso_now_kst() -> str:
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
    url: str,
    *,
    decode: str = "utf-8",
    retries: int = 3,
    timeout: int = 15,
    sleep_seconds: float = 0.5,
) -> str:
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            request = Request(url, method="GET")
            with urlopen(
                request, timeout=timeout
            ) as response:
                return response.read().decode(decode)

        except HTTPError as e:
            last_error = e
            status = getattr(e, "code", None)

            # 429, 500계열만 재시도
            if (
                status in (429, 500, 502, 503, 504)
                and attempt < retries
            ):
                wait = sleep_seconds * attempt
                logger.warning(
                    f"HTTPError {status} on attempt {attempt}/{retries}. "
                    f"Retrying in {wait:.1f}s. URL={url}"
                )
                time.sleep(wait)
                continue

            logger.error(
                f"HTTPError {status}: {e} URL={url}"
            )
            raise

        except URLError as e:
            last_error = e
            if attempt < retries:
                wait = sleep_seconds * attempt
                logger.warning(
                    f"URLError on attempt {attempt}/{retries}. "
                    f"Retrying in {wait:.1f}s. URL={url}, error={e}"
                )
                time.sleep(wait)
                continue

            logger.error(f"URLError: {e} URL={url}")
            raise

        except Exception as e:
            last_error = e
            logger.error(
                f"Unexpected request error: {e} URL={url}"
            )
            raise

    raise last_error


# --------------------------------------------------
# 지역명 정규화
# --------------------------------------------------
def normalize_sido_name(name: str) -> str:
    if not name:
        return ""

    mapping = {
        "서울특별시": "서울",
        "부산광역시": "부산",
        "대구광역시": "대구",
        "인천광역시": "인천",
        "광주광역시": "광주",
        "대전광역시": "대전",
        "울산광역시": "울산",
        "세종특별자치시": "세종",
        "경기도": "경기",
        "강원특별자치도": "강원",
        "강원도": "강원",
        "충청북도": "충북",
        "충청남도": "충남",
        "전북특별자치도": "전북",
        "전라북도": "전북",
        "전라남도": "전남",
        "경상북도": "경북",
        "경상남도": "경남",
        "제주특별자치도": "제주",
        "제주도": "제주",
    }
    return mapping.get(name.strip(), name.strip())


def normalize_area_token(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    suffixes = [
        "특별자치시",
        "특별자치도",
        "특별시",
        "광역시",
        "시",
        "군",
        "구",
        "읍",
        "면",
        "동",
        "리",
    ]
    for suffix in suffixes:
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break

    text = re.sub(r"\s+", "", text)
    return text


def normalize_station_name(station_name: str) -> str:
    if not station_name:
        return ""
    return normalize_area_token(station_name)


# --------------------------------------------------
# 위치 정보 로드 및 인덱스
# --------------------------------------------------
@lru_cache(maxsize=1)
def load_locations():
    response = s3_client.get_object(
        Bucket=LOCATION_BUCKET, Key=LOCATION_KEY
    )
    lines = (
        response["Body"]
        .read()
        .decode("utf-8-sig")
        .splitlines()
    )
    reader = csv.DictReader(lines)
    locations = list(reader)
    logger.info(
        f"Loaded {len(locations)} locations from s3://{LOCATION_BUCKET}/{LOCATION_KEY}"
    )
    return locations


@lru_cache(maxsize=1)
def build_region_index():
    locations = load_locations()

    exact_map = {}
    partial_candidates = []

    for row in locations:
        sido = normalize_sido_name(row.get("1단계", ""))
        lv2 = normalize_area_token(row.get("2단계", ""))
        lv3 = normalize_area_token(row.get("3단계", ""))
        region_code = row.get("행정구역코드", "")

        if sido and lv2 and region_code:
            exact_map[(sido, lv2)] = region_code

        if sido and lv3 and region_code:
            partial_candidates.append(
                {
                    "sido": sido,
                    "name": lv3,
                    "region_code": region_code,
                }
            )

        if sido and lv2 and region_code:
            partial_candidates.append(
                {
                    "sido": sido,
                    "name": lv2,
                    "region_code": region_code,
                }
            )

    logger.info(
        f"Built region index: exact_map={len(exact_map)}, "
        f"partial_candidates={len(partial_candidates)}"
    )
    return exact_map, partial_candidates


def find_region_code_for_air(
    sido_name: str, station_name: str
) -> str:
    exact_map, partial_candidates = build_region_index()

    sido = normalize_sido_name(sido_name)
    station = normalize_station_name(station_name)

    if not sido or not station:
        return ""

    exact_key = (sido, station)
    if exact_key in exact_map:
        return exact_map[exact_key]

    for candidate in partial_candidates:
        if candidate["sido"] != sido:
            continue

        cand_name = candidate["name"]
        if (
            station == cand_name
            or station in cand_name
            or cand_name in station
        ):
            return candidate["region_code"]

    logger.warning(
        f"[MATCH FAIL] sido={sido_name}, station={station_name}"
    )
    return ""


# --------------------------------------------------
# 시간 정규화
# --------------------------------------------------
def normalize_data_time(data_time_str: str) -> str:
    if not data_time_str or not data_time_str.strip():
        return ""

    parts = data_time_str.split()
    if len(parts) != 2:
        return ""

    date_part, time_part = parts

    if time_part == "24:00":
        dt = datetime.strptime(
            date_part, "%Y-%m-%d"
        ) + timedelta(days=1)
        return dt.strftime("%Y%m%d") + "0000"

    dt = datetime.strptime(data_time_str, "%Y-%m-%d %H:%M")
    return dt.strftime("%Y%m%d%H%M")


def get_ultra_short_nowcast_base_datetime() -> (
    tuple[str, str]
):
    """
    초단기실황/근접 발표 데이터용 보정.
    너무 이른 분(minute)에 호출하면 아직 최신 정시 데이터가 없을 수 있으므로
    45분 이전이면 이전 시각 기준으로 내린다.
    """
    current = now_kst()

    if current.minute < 45:
        current -= timedelta(hours=1)

    current = current.replace(
        minute=0, second=0, microsecond=0
    )
    return current.strftime("%Y%m%d"), current.strftime(
        "%H%M"
    )


# --------------------------------------------------
# XML / JSON 파싱
# --------------------------------------------------
def parse_xml_response(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []

    for item in root.findall(".//item"):
        row = {}
        for child in item:
            row[child.tag] = (
                child.text if child.text is not None else ""
            )
        items.append(row)

    return items


def build_weather_items(api_data: list[dict]) -> list[dict]:
    rows = []

    if not isinstance(api_data, list):
        logger.warning(
            f"build_weather_items: expected list, got {type(api_data)}"
        )
        return rows

    updated_at = iso_now_kst()

    for region in api_data:
        region_code = region.get("region_code", "")
        region_name = region.get("region_name", "")
        region_nx = region.get("nx", "")
        region_ny = region.get("ny", "")

        payload = region.get("response", {})
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
                f"Unexpected items type for region_code={region_code}: {type(items)}"
            )
            continue

        for item in items:
            base_date = item.get("baseDate", "")
            base_time = item.get("baseTime", "")
            category = item.get("category", "")

            row = {
                # DynamoDB에서 region별 + 시각별 + 카테고리별 유일키로 쓰기 좋게 추가
                "weatherKey": f"{region_code}#{base_date}#{base_time}#{category}",
                "region_code": region_code,
                "region_name": region_name,
                "region_nx": str(region_nx),
                "region_ny": str(region_ny),
                "baseDate": base_date,
                "baseTime": base_time,
                "category": category,
                "nx": str(item.get("nx", "")),
                "ny": str(item.get("ny", "")),
                "obsrValue": to_decimal_if_number(
                    item.get("obsrValue", "")
                ),
                "updatedAt": updated_at,
            }
            rows.append(row)

    return rows


def build_air_item(raw: dict) -> dict:
    sido_name = raw.get("sidoName", "")
    station_name = raw.get("stationName", "")
    data_time_raw = raw.get("dataTime", "")
    data_time_normalized = normalize_data_time(
        data_time_raw
    )

    region_code = find_region_code_for_air(
        sido_name, station_name
    )

    item = {
        "stationKey": f"{sido_name}#{station_name}",
        "region_code": region_code,
        "sidoName": sido_name,
        "stationName": station_name,
        "dataTimeRaw": data_time_raw,
        "dataTimeNormalized": data_time_normalized,
        "mangName": raw.get("mangName", ""),
        "so2Value": to_decimal_if_number(
            raw.get("so2Value")
        ),
        "coValue": to_decimal_if_number(raw.get("coValue")),
        "o3Value": to_decimal_if_number(raw.get("o3Value")),
        "no2Value": to_decimal_if_number(
            raw.get("no2Value")
        ),
        "pm10Value": to_decimal_if_number(
            raw.get("pm10Value")
        ),
        "pm10Value24": to_decimal_if_number(
            raw.get("pm10Value24")
        ),
        "pm25Value": to_decimal_if_number(
            raw.get("pm25Value")
        ),
        "pm25Value24": to_decimal_if_number(
            raw.get("pm25Value24")
        ),
        "khaiValue": to_decimal_if_number(
            raw.get("khaiValue")
        ),
        "khaiGrade": raw.get("khaiGrade", ""),
        "so2Grade": raw.get("so2Grade", ""),
        "coGrade": raw.get("coGrade", ""),
        "o3Grade": raw.get("o3Grade", ""),
        "no2Grade": raw.get("no2Grade", ""),
        "pm10Grade": raw.get("pm10Grade", ""),
        "pm25Grade": raw.get("pm25Grade", ""),
        "so2Flag": raw.get("so2Flag", "") or "",
        "coFlag": raw.get("coFlag", "") or "",
        "o3Flag": raw.get("o3Flag", "") or "",
        "no2Flag": raw.get("no2Flag", "") or "",
        "pm10Flag": raw.get("pm10Flag", "") or "",
        "pm25Flag": raw.get("pm25Flag", "") or "",
        "updatedAt": iso_now_kst(),
    }

    return item


# --------------------------------------------------
# 외부 API 호출
# --------------------------------------------------
def get_air_pollution_data(sido_name: str) -> list[dict]:
    if not AIR_POLLUTION_API_URL or not AIR_API_KEY:
        raise ValueError(
            "Missing AIR_POLLUTION_API_URL or AIR_API_KEY"
        )

    params = {
        "serviceKey": AIR_API_KEY,
        "returnType": "xml",
        "numOfRows": "1000",
        "pageNo": "1",
        "sidoName": sido_name,
        "ver": "1.0",
    }

    url = f"{AIR_POLLUTION_API_URL}?{urlencode(params)}"
    logger.info(f"Calling air API for sido={sido_name}")

    response_text = request_text_with_retry(url)
    items = parse_xml_response(response_text)

    logger.info(
        f"Fetched air item count: sido={sido_name}, count={len(items)}"
    )
    return items


def get_ultra_short_nowcast(
    extra_params=None,
) -> list[dict]:
    if not WEATHER_API_URL or not WEATHER_API_KEY:
        raise ValueError(
            "Missing WEATHER_API_URL or WEATHER_API_KEY"
        )

    locations = load_locations()
    results = []

    base_date, base_time = (
        get_ultra_short_nowcast_base_datetime()
    )
    logger.info(
        f"Using weather base datetime: base_date={base_date}, base_time={base_time}"
    )

    for idx, row in enumerate(locations, start=1):
        try:
            region_code = row.get("행정구역코드", "")
            region_name = f"{row.get('1단계', '')} {row.get('2단계', '')}".strip()
            nx = int(row["격자 X"])
            ny = int(row["격자 Y"])

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

            if extra_params:
                params.update(extra_params)

            url = f"{WEATHER_API_URL}?{urlencode(params)}"
            logger.info(
                f"Calling weather API ({idx}/{len(locations)}): "
                f"region_code={region_code}, nx={nx}, ny={ny}"
            )

            response_text = request_text_with_retry(url)
            api_data = json.loads(response_text)

            results.append(
                {
                    "region_code": region_code,
                    "region_name": region_name,
                    "nx": nx,
                    "ny": ny,
                    "response": api_data,
                }
            )

            # 과도한 연속호출 방지
            time.sleep(0.15)

        except KeyError as e:
            logger.error(
                f"Missing location field: region row={row}, error={e}"
            )
            continue

        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON response for region_code={row.get('행정구역코드', '')}: {e}"
            )
            continue

        except Exception as e:
            logger.error(
                f"Weather collection failed for region_code={row.get('행정구역코드', '')}: {e}"
            )
            continue

    logger.info(
        f"Collected weather payloads: {len(results)}"
    )
    return results


# --------------------------------------------------
# 수집 함수
# --------------------------------------------------
def collect_all_sido_air_data() -> list[dict]:
    all_items = []

    for sido in SIDO_LIST:
        try:
            items = get_air_pollution_data(sido)
            all_items.extend(items)
        except Exception as e:
            logger.error(
                f"{sido} air collection failed: {e}"
            )

    logger.info(
        f"Collected total air items: {len(all_items)}"
    )
    return all_items


# --------------------------------------------------
# DynamoDB 저장
# --------------------------------------------------
def save_air_items_to_dynamodb(
    items: list[dict], table_name: str
) -> int:
    table = dynamodb.Table(table_name)
    saved_count = 0
    skipped_count = 0

    with table.batch_writer() as batch:
        for raw in items:
            try:
                db_item = build_air_item(raw)

                if (
                    not db_item["stationKey"]
                    or not db_item["dataTimeNormalized"]
                ):
                    skipped_count += 1
                    continue

                batch.put_item(Item=db_item)
                saved_count += 1

            except Exception as e:
                skipped_count += 1
                logger.error(
                    f"Skipping invalid air item: raw={raw}, error={e}"
                )

    logger.info(
        f"Saved air items: saved={saved_count}, skipped={skipped_count}"
    )
    return saved_count


def save_nowcast_to_dynamodb(
    api_data: list[dict], table_name: str
) -> int:
    table = dynamodb.Table(table_name)
    rows = build_weather_items(api_data)

    if not rows:
        logger.warning(
            "No weather rows parsed from nowcast API"
        )
        return 0

    saved_count = 0
    skipped_count = 0

    with table.batch_writer() as batch:
        for row in rows:
            try:
                if (
                    not row.get("weatherKey")
                    or not row.get("region_code")
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
                logger.error(
                    f"Skipping invalid weather item: row={row}, error={e}"
                )

    logger.info(
        f"Saved weather items: saved={saved_count}, skipped={skipped_count}"
    )
    return saved_count


# --------------------------------------------------
# Lambda 핸들러
# --------------------------------------------------
def lambda_handler(event, context):
    weather_table_name = os.environ.get(
        "WEATHER_DYNAMODB_TABLE_NAME"
    )
    air_table_name = os.environ.get(
        "AIR_DYNAMODB_TABLE_NAME"
    )

    if not weather_table_name:
        raise ValueError(
            "Missing WEATHER_DYNAMODB_TABLE_NAME"
        )

    if not air_table_name:
        raise ValueError("Missing AIR_DYNAMODB_TABLE_NAME")

    saved_weather_count = 0
    saved_air_count = 0

    logger.info("Starting weather collection")

    try:
        nowcast_data = get_ultra_short_nowcast()
        logger.info(
            f"Weather payload count={len(nowcast_data)}"
        )

        if nowcast_data:
            saved_weather_count = save_nowcast_to_dynamodb(
                nowcast_data, weather_table_name
            )
    except Exception as e:
        logger.error(f"Weather collection failed: {e}")

    logger.info("Starting air collection")

    try:
        air_items = collect_all_sido_air_data()
        logger.info(f"Air payload count={len(air_items)}")

        if air_items:
            saved_air_count = save_air_items_to_dynamodb(
                air_items, air_table_name
            )
    except Exception as e:
        logger.error(f"Air collection failed: {e}")

    # ----------------------------
    # 결과 로그
    # ----------------------------
    logger.info(
        f"Lambda completed: saved_weather={saved_weather_count}, "
        f"saved_air={saved_air_count}"
    )

    return {
        "statusCode": 200,
        "message": "Air pollution and weather data saved successfully",
        "savedWeatherCount": saved_weather_count,
        "savedAirCount": saved_air_count,
    }
