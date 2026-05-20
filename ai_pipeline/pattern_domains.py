# pattern_domains.py

TEMP_ZONES  = ["35over","30-34","25-29","20-24","15-19","10-14","5-9","0-4","-10--1","under-11"]
DIFF_LEVELS = ["none","small","normal","large","xlarge"]
RAIN_LEVELS = ["none","drizzle","light","moderate","heavy"]
PM_GRADES   = ["good","normal","bad","very_bad"]
WIND_LEVELS = ["calm","moderate","strong"]
UV_LEVELS   = ["low","normal","high"]
PTY_TYPES   = ["none","rain","snow"]

# 10×5×5×4×3×3×3 = 27,000가지

def get_temp_zone(temp):
    if temp >= 35: return "35over"
    elif temp >= 30: return "30-34"
    elif temp >= 25: return "25-29"
    elif temp >= 20: return "20-24"
    elif temp >= 15: return "15-19"
    elif temp >= 10: return "10-14"
    elif temp >= 5:  return "5-9"
    elif temp >= 0:  return "0-4"
    elif temp >= -10: return "-10--1"
    else: return "under-11"

def get_diff_level(diff):
    if diff <= 2:   return "none"
    elif diff <= 5: return "small"
    elif diff <= 8: return "normal"
    elif diff <= 12: return "large"
    else: return "xlarge"

def get_rain_level(rains):
    for r in rains:
        if r in ["강수없음","0"]: continue
        if "미만" in r: return "drizzle"
        val = int(r.split("~")[0].replace("mm","").strip())
        if val >= 15: return "heavy"
        elif val >= 3: return "moderate"
        else: return "light"
    return "none"

def get_pm_grade(pm10, pm25):
    if pm25 in ["3","4"] or pm10 == "4": return "very_bad"
    elif pm10 == "3": return "bad"
    elif pm10 == "2": return "normal"
    else: return "good"

def get_wind_level(wsd_max):
    if wsd_max >= 3: return "strong"
    elif wsd_max >= 2: return "moderate"
    else: return "calm"

def get_uv_level(uv_max):
    if uv_max >= 6: return "high"
    elif uv_max >= 3: return "normal"
    else: return "low"

def get_pty_type(ptys):
    if "3" in ptys: return "snow"
    if any(p in ["1","2","4"] for p in ptys): return "rain"
    return "none"

def build_sk(temp_zone, diff_level, rain_level,
             pm_grade, wind_level, uv_level, pty_type):
    return (f"temp:{temp_zone}|diff:{diff_level}|rain:{rain_level}"
            f"|pm:{pm_grade}|wind:{wind_level}|uv:{uv_level}|pty:{pty_type}")

if __name__ == "__main__":
    # 기온 테스트
    print("=== 기온 테스트 ===")
    print(f"27도  → {get_temp_zone(27)}")    # 25-29
    print(f"34.5도 → {get_temp_zone(34.5)}") # 30-34
    print(f"-5도  → {get_temp_zone(-5)}")    # -10--1

    # 강수량 테스트
    print("\n=== 강수량 테스트 ===")
    print(f"강수없음 → {get_rain_level(['강수없음'])}")  # none
    print(f"1mm 미만 → {get_rain_level(['1mm 미만'])}")  # drizzle
    print(f"5~10mm  → {get_rain_level(['5~10mm'])}")    # moderate

    # SK 생성 테스트
    print("\n=== SK 생성 테스트 ===")
    sk = build_sk("25-29", "normal", "none", "good", "calm", "high", "none")
    print(f"SK: {sk}")

    # 전체 패턴 수 확인
    from itertools import product
    total = len(list(product(
        TEMP_ZONES, DIFF_LEVELS, RAIN_LEVELS,
        PM_GRADES, WIND_LEVELS, UV_LEVELS, PTY_TYPES
    )))
    print(f"\n전체 패턴 수: {total:,}개")