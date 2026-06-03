import os
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")

KST = ZoneInfo("Asia/Seoul")

AIR_POLLUTION_API_URL = os.environ.get("AIR_POLLUTION_API_URL")
AIR_API_KEY = os.environ.get("AIR_API_KEY")

SIDO_LIST = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산",
    "경기", "강원", "충북", "충남", "전북", "전남",
    "경북", "경남", "제주", "세종"
]


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


def request_text_with_retry(url, retries=3, timeout=15, sleep_seconds=0.5):
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


def normalize_data_time(data_time_str):
    if not data_time_str or not data_time_str.strip():
        return ""

    parts = data_time_str.split()
    if len(parts) != 2:
        return ""

    date_part, time_part = parts

    if time_part == "24:00":
        dt = datetime.strptime(date_part, "%Y-%m-%d") + timedelta(days=1)
        return dt.strftime("%Y%m%d") + "0000"

    dt = datetime.strptime(data_time_str, "%Y-%m-%d %H:%M")
    return dt.strftime("%Y%m%d%H%M")


def parse_xml_response(xml_text):
    root = ET.fromstring(xml_text)
    items = []

    for item in root.findall(".//item"):
        row = {}
        for child in item:
            row[child.tag] = child.text if child.text is not None else ""
        items.append(row)

    return items


def get_air_pollution_data(sido_name):
    if not AIR_POLLUTION_API_URL or not AIR_API_KEY:
        raise ValueError("Missing AIR_POLLUTION_API_URL or AIR_API_KEY")

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

    logger.info(f"Fetched air item count: sido={sido_name}, count={len(items)}")
    return items


def collect_all_sido_air_data():
    all_items = []

    for sido in SIDO_LIST:
        try:
            items = get_air_pollution_data(sido)
            all_items.extend(items)
        except Exception as e:
            logger.error(f"{sido} air collection failed: {e}")

    return all_items


def build_air_item(raw):
    sido_name = raw.get("sidoName", "")
    station_name = raw.get("stationName", "")
    data_time_raw = raw.get("dataTime", "")
    data_time_normalized = normalize_data_time(data_time_raw)

    return {
        "stationKey": f"{sido_name}#{station_name}",
        "sidoName": sido_name,
        "stationName": station_name,
        "dataTimeRaw": data_time_raw,
        "dataTimeNormalized": data_time_normalized,

        "so2Value": to_decimal_if_number(raw.get("so2Value")),
        "coValue": to_decimal_if_number(raw.get("coValue")),
        "o3Value": to_decimal_if_number(raw.get("o3Value")),
        "no2Value": to_decimal_if_number(raw.get("no2Value")),
        "pm10Value": to_decimal_if_number(raw.get("pm10Value")),
        "pm25Value": to_decimal_if_number(raw.get("pm25Value")),
        "khaiValue": to_decimal_if_number(raw.get("khaiValue")),

        "khaiGrade": raw.get("khaiGrade", ""),
        "so2Grade": raw.get("so2Grade", ""),
        "coGrade": raw.get("coGrade", ""),
        "o3Grade": raw.get("o3Grade", ""),
        "no2Grade": raw.get("no2Grade", ""),
        "pm10Grade": raw.get("pm10Grade", ""),
        "pm25Grade": raw.get("pm25Grade", ""),

        "updatedAt": iso_now_kst(),
    }


def save_air_items_to_dynamodb(items, table_name):
    table = dynamodb.Table(table_name)

    saved_count = 0
    skipped_count = 0

    with table.batch_writer() as batch:
        for raw in items:
            try:
                db_item = build_air_item(raw)

                if not db_item["stationKey"] or not db_item["dataTimeNormalized"]:
                    skipped_count += 1
                    continue

                batch.put_item(Item=db_item)
                saved_count += 1

            except Exception as e:
                skipped_count += 1
                logger.error(f"Skipping invalid air item: raw={raw}, error={e}")

    logger.info(f"Saved air items: saved={saved_count}, skipped={skipped_count}")
    return saved_count


def lambda_handler(event, context):
    air_table_name = os.environ.get("AIR_DYNAMODB_TABLE_NAME")

    if not air_table_name:
        raise ValueError("Missing AIR_DYNAMODB_TABLE_NAME")

    air_items = collect_all_sido_air_data()
    saved_count = save_air_items_to_dynamodb(air_items, air_table_name)

    return {
        "statusCode": 200,
        "message": "Air pollution data saved successfully",
        "savedAirCount": saved_count,
    }