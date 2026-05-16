import json
import boto3
import os
import csv
from io import StringIO
from urllib.parse import parse_qs, unquote
from decimal import Decimal

# 매핑 파일에서 딕셔너리 가져오기 (코드 중복 제거)
from mapping import gu_to_station

# 1. 환경 변수 감지
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

s3 = boto3.client("s3")

TABLE_NAME = os.environ.get(
    "TABLE_NAME", "inhatc-team2-1-recommend-cache"
)
AIR_TABLE_NAME = os.environ.get(
    "AIR_TABLE_NAME", "inhatc-team2-5-air-cache"
)
WEATHER_TABLE_NAME = os.environ.get(
    "WEATHER_TABLE_NAME", "inhatc-team2-5-weather-cache"
)

recommend_table = dynamodb.Table(TABLE_NAME)
air_table = dynamodb.Table(AIR_TABLE_NAME)
weather_table = dynamodb.Table(WEATHER_TABLE_NAME)

BUCKET_NAME = "inhatc-team2-5-raw-data"
PREFIX = "raw/forecast/ultra_short_forecast/"

# ★ 성능 개선: S3에서 가져온 데이터를 람다 컨테이너 메모리에 캐싱
_CSV_CACHE = None
_LATEST_FILE_KEY = None


def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def load_csv_rows():
    global _CSV_CACHE, _LATEST_FILE_KEY

    # S3에서 최신 파일 목록 조회
    response = s3.list_objects_v2(
        Bucket=BUCKET_NAME, Prefix=PREFIX
    )
    if "Contents" not in response:
        return []

    latest_file = max(
        response["Contents"], key=lambda x: x["Key"]
    )
    latest_key = latest_file["Key"]

    # ★ 성능 개선: 이전에 캐싱된 파일과 키가 같다면 S3에서 다운로드하지 않고 캐시 반환
    if (
        _CSV_CACHE is not None
        and _LATEST_FILE_KEY == latest_key
    ):
        print("Using cached CSV data")
        return _CSV_CACHE

    print(f"Loading new file from S3: {latest_key}")
    file_response = s3.get_object(
        Bucket=BUCKET_NAME, Key=latest_key
    )
    csv_content = (
        file_response["Body"].read().decode("utf-8-sig")
    )
    csv_file = StringIO(csv_content)

    # 캐시 업데이트
    _CSV_CACHE = list(csv.DictReader(csv_file))
    _LATEST_FILE_KEY = latest_key

    return _CSV_CACHE


def get_temperature_data(rows, region, ch):
    result = []
    for row in rows:
        if (
            row["region_name"] == region
            and row["category"] == ch
        ):
            result.append(row["fcstValue"])

    if not result:
        new_region = region.split()[0]
        for row in rows:
            if (
                row["region_name"] == new_region
                and row["category"] == ch
            ):
                result.append(row["fcstValue"])
    return result


def lambda_handler(event, context):
    try:
        raw_qs = event.get("rawQueryString", "")
        params = parse_qs(raw_qs)

        region = params.get("region", [""])[0]
        region = unquote(region)
        path = event.get("rawPath", "/")

        region_n = region.split()

        if len(region_n) < 2:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "region 파라미터 형식 오류 (예: 인천광역시 중구)"
                    },
                    ensure_ascii=False,
                ),
            }

        gungu = region_n[1]
        raw_station = f"{region_n[0]} {region_n[1]}"

        station_key = gu_to_station.get(gungu)

        if not station_key:
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {"error": "지원하지 않는 지역입니다."},
                    ensure_ascii=False,
                ),
            }

        response = air_table.get_item(
            Key={"stationKey": station_key}
        )
        air_data = response.get("Item", {})

        # CSV 데이터 로드 (캐시 적용됨)
        rows = load_csv_rows()

        weather_data = get_temperature_data(
            rows, raw_station, "T1H"
        )
        rain_data = get_temperature_data(
            rows, raw_station, "RN1"
        )
        sky_data = get_temperature_data(
            rows, raw_station, "SKY"
        )
        pty_data = get_temperature_data(
            rows, raw_station, "PTY"
        )

        # ★ 500 에러 방지: 데이터가 하나라도 없으면 에러 처리
        if not weather_data or not rain_data:
            return {
                "statusCode": 404,
                "body": json.dumps(
                    {
                        "error": "해당 지역의 기상 데이터를 S3에서 찾을 수 없습니다."
                    },
                    ensure_ascii=False,
                ),
            }

        if path == "/recommend":
            pm10 = str(air_data.get("pm10Grade", ""))
            pm25 = str(air_data.get("pm25Grade", ""))

            recommend_list = []
            # 현재부터 최대 6개(5시간 후)까지의 시간대 데이터 계산
            loop_count = min(
                6, len(weather_data), len(rain_data)
            )

            for i in range(loop_count):
                temp = int(weather_data[i])
                rain = rain_data[i]

                top = "긴팔 티셔츠, 가디건 후드티, 맨투맨"
                bottom = "청바지"
                mask = "마스크 선택"
                pack = "불필요"

                # 온도에 따른 옷차림 로직
                if temp >= 28:
                    top, bottom = (
                        "민소매, 반팔 린넨소재",
                        "반바지, 짧은 치마, 린넨 소재",
                    )
                elif temp >= 23:
                    top, bottom = (
                        "반팔, 얇은 셔츠",
                        "반바지, 면바지",
                    )
                elif temp >= 17:
                    top, bottom = (
                        "긴팔 티셔츠, 가디건 후드티, 맨투맨",
                        "청바지",
                    )
                elif temp >= 12:
                    top, bottom = (
                        "가디건, 야상, 재킷, 니트",
                        "두꺼운 긴바지",
                    )
                elif temp >= 5:
                    top, bottom = (
                        "코트, 가죽재킷, 두꺼운 니트",
                        "기모바지",
                    )
                else:
                    top, bottom = (
                        "패딩, 두꺼운 롱코트, 방한복, 기모 이너",
                        "방한복, 기모 이너",
                    )

                # 미세먼지에 따른 마스크 로직
                if pm10 == "4" or pm25 in ["3", "4"]:
                    mask = "kf94 필수"
                elif pm10 == "3" or pm25 == "3":
                    mask = "kf80 권장"

                # 강수에 따른 우산 로직
                if rain in ["강수없음", "0"]:
                    pack = "불필요"
                elif rain == "1mm 미만":
                    pack = "접이식 우산"
                else:
                    pack = "우산 필수"

                recommend_list.append(
                    {
                        "top": top,
                        "bottom": bottom,
                        "mask": mask,
                        "pack": pack,
                    }
                )

            return {
                "statusCode": 200,
                "body": json.dumps(
                    recommend_list, ensure_ascii=False
                ),
            }

        elif path == "/weather":
            sky_result = []

            for sky, pty in zip(sky_data, pty_data):
                sky = sky.strip()
                pty = pty.strip()

                if pty in ["1", "2", "4"]:
                    sky_result.append("비")
                elif pty == "3":
                    sky_result.append("눈")
                else:
                    if sky in ["0", "1"]:
                        sky_result.append("맑음")
                    else:
                        sky_result.append("흐림")

            filtered_data = {
                "temp": weather_data,
                "o3": air_data.get("o3Value"),
                "pm10": air_data.get("pm10Value"),
                "pm10Status": air_data.get("pm10Grade"),
                "pm25": air_data.get("pm25Value"),
                "pm25Status": air_data.get("pm25Grade"),
                "rain": rain_data,
                "sky": sky_result,
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
        # 예상치 못한 에러가 났을 때 Lambda가 죽어버리지 않도록 방어
        print(f"Error occurred: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"error": "서버 내부 오류가 발생했습니다."},
                ensure_ascii=False,
            ),
        }
