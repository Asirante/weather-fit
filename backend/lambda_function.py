import json
import boto3
import os
import csv
from io import StringIO
from urllib.parse import parse_qs, unquote
from decimal import Decimal

# 1. 환경 변수 감지
IS_LOCAL = os.environ.get('AWS_SAM_LOCAL') == 'true'

if IS_LOCAL:
    # 로컬 도커 환경 전용 설정
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url="http://dynamodb-local:8000",
        region_name="us-east-1",
        aws_access_key_id="local",
        aws_secret_access_key="local"
    )
else:
    # 실제 AWS 배포 환경 전용 설정 (자동으로 IAM 권한 사용)
    dynamodb = boto3.resource('dynamodb')

s3 = boto3.client('s3')

TABLE_NAME = os.environ.get('TABLE_NAME', 'inhatc-team2-1-recommend-cache')
AIR_TABLE_NAME = os.environ.get('AIR_TABLE_NAME', 'inhatc-team2-5-air-cache')
WEATHER_TABLE_NAME = os.environ.get('WEATHER_TABLE_NAME', 'inhatc-team2-5-weather-cache')

recommend_table = dynamodb.Table(TABLE_NAME)
air_table = dynamodb.Table(AIR_TABLE_NAME)
weather_table = dynamodb.Table(WEATHER_TABLE_NAME)

BUCKET_NAME = 'inhatc-team2-5-raw-data'
PREFIX = 'raw/forecast/ultra_short_forecast/'

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

# CSV 한 번만 로드
def load_csv_rows():

    response = s3.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=PREFIX
    )

    latest_file = max(
        response['Contents'],
        key=lambda x: x['Key']
    )

    latest_key = latest_file['Key']

    print(f"최신 파일: {latest_key}")

    file_response = s3.get_object(
        Bucket=BUCKET_NAME,
        Key=latest_key
    )

    csv_content = file_response['Body'].read().decode('utf-8-sig')

    csv_file = StringIO(csv_content)

    return list(csv.DictReader(csv_file))


def get_temperature_data(rows, region, ch):

    result = []

    for row in rows:
        if (
            row['region_name'] == region
            and row['category'] == ch
        ):
            result.append(row['fcstValue'])

    if not result:

        new_region = region.split()[0]

        for row in rows:
            if (
                row['region_name'] == new_region
                and row['category'] == ch
            ):
                result.append(row['fcstValue'])

    return result


def lambda_handler(event, context):

    raw_qs = event.get('rawQueryString', '')
    params = parse_qs(raw_qs)

    region = params.get('region', [''])[0]
    region = unquote(region)

    path = event.get('rawPath', '/')

    region_n = region.split()

    if len(region_n) != 3:
        return {
            'statusCode': 400,
            'body': json.dumps({"error": "region 파라미터 형식 오류"}, ensure_ascii=False)
        }

    gungu = region_n[1]

    raw_station = f"{region_n[0]} {region_n[1]}"

    gu_to_station = {
        '중구': '인천#영종',
        '동구': '인천#송림',
        '미추홀구': '인천#주안',
        '연수구': '인천#송도',
        '남동구': '인천#구월동',
        '부평구': '인천#부평',
        '계양구': '인천#계산',
        '서구': '인천#검단',
        '강화군': '인천#석모리',
        '옹진군': '인천#덕적도'
    }

    station_key = gu_to_station.get(gungu)

    if not station_key:
        return {
            'statusCode': 400,
            'body': json.dumps({"error": "지원하지 않는 지역"}, ensure_ascii=False)
        }

    response = air_table.get_item(Key={'stationKey': station_key})
    air_data = response.get('Item', {})

    # CSV 한 번만 읽기
    rows = load_csv_rows()

    weather_data = get_temperature_data(rows, raw_station, "T1H")
    rain_data = get_temperature_data(rows, raw_station, "RN1")
    sky_data = get_temperature_data(rows, raw_station, "SKY")
    pty_data = get_temperature_data(rows, raw_station, "PTY")

    if path == '/recommend':

        pm10 = str(air_data.get("pm10Grade"))
        pm25 = str(air_data.get("pm25Grade"))

        temp = int(weather_data[0])
        rain = rain_data[0]

        top = '긴팔 티셔츠, 가디건 후드티, 맨투맨'
        bottom = '청바지'
        mask = '마스크 선택'
        pack = '불필요'

        if temp >= 28:
            top = "민소매, 반팔 린넨소재"
            bottom = "반바지, 짧은 치마, 린넨 소재"

        elif temp >= 23:
            top = "반팔, 얇은 셔츠"
            bottom = "반바지, 면바지"

        elif temp >= 17:
            top = "긴팔 티셔츠, 가디건 후드티, 맨투맨"
            bottom = "청바지"

        elif temp >= 12:
            top = "가디건, 야상, 재킷, 니트"
            bottom = "두꺼운 긴바지"

        elif temp >= 5:
            top = "코트, 가죽재킷, 두꺼운 니트"
            bottom = "기모바지"

        elif temp < 5:
            top = "패딩, 두꺼운 롱코트, 방한복, 기모 이너"
            bottom = "방한복, 기모 이너"

        if pm10 == '4' or pm25 in ['3', '4']:
            mask = 'kf94 필수'

        elif pm10 == '3':
            mask = 'kf80 권장'

        if rain == "강수없음" or rain == "0":
            pack = '불필요'

        elif rain == "1mm 미만":
            pack = '접이식 우산'

        else:
            pack = '우산 필수'

        recommend_data = {
            "top": top,
            "bottom": bottom,
            "mask": mask,
            "pack": pack
        }

        pm10 = str(air_data.get("pm10Grade"))    # 미세먼지 지수
        pm25 = str(air_data.get("pm25Grade"))    # 초미세먼지 지수

        top = '긴팔 티셔츠, 가디건 후드티, 맨투맨'
        bottom = '청바지'
        mask = '마스크 선택'
        pack = '불필요'
        
        if pm10 == '4' or pm25 in ['3', '4']:    # 1(좋음), 2(보통), 3(나쁨), 4(매우나쁨)
            mask = 'kf94 필수'
        elif pm10 == '3':mask = 'kf80 권장'

        recommend_data = {
            "top": top,
            "bottom": bottom,
            "mask": mask,
            "pack": pack
        }
        return {
            'statusCode': 200,
            'body': json.dumps(recommend_data, ensure_ascii=False)
        }

    elif path == '/weather':

        sky_result = []

        for sky, pty in zip(sky_data, pty_data):

            sky = sky.strip()
            pty = pty.strip()

            print("sky : ", repr(sky))
            print("pty : ", repr(pty))

            # 강수 형태 우선 처리
            if pty in ['1', '2', '4']:
                sky_result.append('비')

            elif pty == '3':
                sky_result.append('눈')

            # 강수 없을 때 하늘 상태 처리
            else:
                if sky in ['0', '1']:
                    sky_result.append('맑음')
                else:
                    sky_result.append('흐림')

        filtered_data = {
            "temp": weather_data,
            "o3": air_data.get("o3Value"),
            "pm10": air_data.get("pm10Value"),
            "pm10Status": air_data.get("pm10Grade"),
            "pm25": air_data.get("pm25Value"),
            "pm25Status": air_data.get("pm25Grade"),
            "rain": rain_data,
            "sky": sky_result
        }

        return {
            'statusCode': 200,
            'body': json.dumps(filtered_data, ensure_ascii=False, default=decimal_to_float)
        }
    
    else : 
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "주소 오류"}, ensure_ascii=False)
        }