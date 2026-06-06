import json
import os
import logging
import boto3
import csv
import io
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed

from airStatsAPI import collect_air_stats_data
from airInfoAPI import get_minu_dust_week_frcst_dspth

s3_client = boto3.client("s3")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 안전한 함수 실행 
def run_job(job_name, func):
    try:
        result = func()
        logger.info(f"{job_name} collected successfully")
        return job_name, result, None
    except Exception as e:
        logger.exception(f"{job_name} collection failed: {e}")
        return job_name, None, str(e)


# 파서 선택 함수
def convert_api_to_rows(api_name, api_data):
    parser = PARSERS.get(api_name)
    if not parser:
        logger.warning(f"No parser found for {api_name}")
        return []
    return parser(api_data)


# csv로 업로드
def upload_group_as_csv(bucket_name, prefix, data, now):
    for api_name, api_data in data.items():
        try:
            rows = convert_api_to_rows(api_name, api_data)

            if not rows:
                logger.warning(f"No rows extracted for {api_name}, skipping")
                continue

            fieldnames = list(rows[0].keys())

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

            key = f"raw/{prefix}/{api_name}/{now}.csv"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=output.getvalue().encode("utf-8-sig"),
                ContentType="text/csv"
            )

            logger.info(f"{api_name} CSV uploaded to s3://{bucket_name}/{key}")

        except Exception as e:
            logger.exception(f"Failed to upload CSV for {prefix}/{api_name}: {e}")



# 시도별 실시간 평균정보 파싱  
def parse_ctprvn_avg(api_data):
    rows = []

    if not isinstance(api_data, dict):
        logger.warning(f"ctprvn_avg: expected dict, got {type(api_data)}")
        return rows

    for item_code, response_data in api_data.items():
        response = response_data.get("response", {})
        header = response.get("header", {})

        if header.get("resultCode") != "00":
            logger.warning(f"ctprvn_avg invalid response for {item_code}: {response_data}")
            continue

        items = (
            response.get("body", {})
            .get("items", [])
        )

        if isinstance(items, dict):
            items = [items]

        for item in items:
            rows.append({
                "itemCode": item_code,
                "dataTime": item.get("dataTime", ""),
                "seoul": item.get("seoul", ""),
                "busan": item.get("busan", ""),
                "daegu": item.get("daegu", ""),
                "incheon": item.get("incheon", ""),
                "gwangju": item.get("gwangju", ""),
                "daejeon": item.get("daejeon", ""),
                "ulsan": item.get("ulsan", ""),
                "gyeonggi": item.get("gyeonggi", ""),
                "gangwon": item.get("gangwon", ""),
                "chungbuk": item.get("chungbuk", ""),
                "chungnam": item.get("chungnam", ""),
                "jeonbuk": item.get("jeonbuk", ""),
                "jeonnam": item.get("jeonnam", ""),
                "gyeongbuk": item.get("gyeongbuk", ""),
                "gyeongnam": item.get("gyeongnam", ""),
                "jeju": item.get("jeju", ""),
                "sejong": item.get("sejong", "")
            })

    return rows


# 시군구별 실시간 평균정보 파싱
def parse_sigungu_avg(api_data_list):
    rows = []

    if not isinstance(api_data_list, list):
        logger.warning(f"sigungu_avg: expected list, got {type(api_data_list)}")
        return rows

    for api_data in api_data_list:
        response = api_data.get("response", {})
        header = response.get("header", {})

        if header.get("resultCode") != "00":
            logger.warning(f"sigungu_avg invalid response: {api_data}")
            continue

        items = response.get("body", {}).get("items", [])
        if isinstance(items, dict):
            items = [items]

        for item in items:
            rows.append({
                "dataTime": item.get("dataTime", ""),
                "sidoName": item.get("sidoName", ""),
                "cityName": item.get("cityName", ""),
                "so2Value": item.get("so2Value", ""),
                "coValue": item.get("coValue", ""),
                "o3Value": item.get("o3Value", ""),
                "no2Value": item.get("no2Value", ""),
                "pm10Value": item.get("pm10Value", ""),
                "pm25Value": item.get("pm25Value", "")
            })

    return rows


# 초미세먼지 주간예보 파싱
def parse_weekly_air_forecast(api_data):
    rows = []

    response = api_data.get("response", {})
    header = response.get("header", {})
    

    if header.get("resultCode") != "00":
        logger.warning(f"weekly_air_forecast invalid response: {api_data}")
        return rows

    items = (
        response.get("body", {})
        .get("items", [])
    )

    if isinstance(items, dict):
        items = [items]

    for item in items:
        rows.append({
            #"forecastDate": item.get("forecastDate", ""),
            "frcstOneDt": item.get("frcstOneDt", ""),
            "frcstOneCn": item.get("frcstOneCn", ""),
            "frcstTwoDt": item.get("frcstTwoDt", ""),
            "frcstTwoCn": item.get("frcstTwoCn", ""),
            "frcstThreeDt": item.get("frcstThreeDt", ""),
            "frcstThreeCn": item.get("frcstThreeCn", ""),
            "frcstFourDt": item.get("frcstFourDt", ""),
            "frcstFourCn": item.get("frcstFourCn", ""),
            "frcstFiveDt": item.get("frcstFiveDt", ""),
            "frcstFiveCn": item.get("frcstFiveCn", ""),
            "frcstSixDt": item.get("frcstSixDt", ""),
            "frcstSixCn": item.get("frcstSixCn", ""),
            "frcstSevenDt": item.get("frcstSevenDt", ""),
            "frcstSevenCn": item.get("frcstSevenCn", ""),
            "PresnatnDt": item.get("PresnatnDt", "")
        })

    return rows


# 파서 정의
PARSERS = {
    #"uv_index": parse_uv_index_and_air_diffusion,
    #"air_diffusion": parse_uv_index_and_air_diffusion,

    #"ultra_short_nowcast": parse_ultra_short_nowcast,
    #"ultra_short_forecast": parse_ultra_short_forecast,
    #"short_forecast": parse_short_forecast,

    "ctprvn_avg": parse_ctprvn_avg,
    "sigungu_avg": parse_sigungu_avg,

    "weekly_air_forecast": parse_weekly_air_forecast
}


def lambda_handler(event, context):
    bucket_name = os.environ.get("S3_RAW_BUCKET")
    if not bucket_name:
        raise ValueError("Missing environment variable S3_RAW_BUCKET")

    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d%H%M%S")

    jobs = {
        "air_stats": collect_air_stats_data,
        "weekly_air_forecast": get_minu_dust_week_frcst_dspth
    }

    results = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {
            executor.submit(run_job, job_name, job_func): job_name
            for job_name, job_func in jobs.items()
        }

        for future in as_completed(future_map):
            job_name, result, error = future.result()

            if error:
                errors[job_name] = error
            else:
                results[job_name] = result
                

    if "air_stats" in results:
        upload_group_as_csv(bucket_name, "air_stats", results["air_stats"], now)

    if "weekly_air_forecast" in results:
        upload_group_as_csv(
            bucket_name,
            "air_info",
            {"weekly_air_forecast": results["weekly_air_forecast"]},
            now
        )

    return {
        "statusCode": 200,
        "message": "Completed with partial success allowed",
        "success_jobs": list(results.keys()),
        "failed_jobs": errors
    }