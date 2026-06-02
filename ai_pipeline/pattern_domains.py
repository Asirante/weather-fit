# pattern_domains.py

TEMP_ZONES  = ["hot", "warm", "mild", "cool", "cold", "freeze"]
RAIN_LEVELS = ["none", "drizzle", "heavy"]
PM_GRADES   = ["good", "normal", "bad", "very_bad"]

# 6×3×4 = 72가지

def get_temp_zone(temp: float) -> str:
    """기온(℃)을 구간 코드로 변환"""
    if temp >= 28:   return "hot"
    elif temp >= 23: return "warm"
    elif temp >= 17: return "mild"
    elif temp >= 12: return "cool"
    elif temp >= 5:  return "cold"
    else:            return "freeze"

def get_rain_level(rains: list) -> str:
    """강수량 목록을 레벨 코드로 변환"""
    for r in rains:
        if r in ["강수없음", "0"]: continue
        if "미만" in r: return "drizzle"
        return "heavy"
    return "none"

def get_pm_grade(pm10: str, pm25: str) -> str:
    """미세먼지 등급 코드 반환"""
    if pm25 in ["3","4"] or pm10 == "4": return "very_bad"
    elif pm10 == "3": return "bad"
    elif pm10 == "2": return "normal"
    else: return "good"

def build_sk(temp_zone, rain_level, pm_grade):
    """3개 변수로 패턴 키(SK) 생성"""
    return f"temp:{temp_zone}|rain:{rain_level}|pm:{pm_grade}"


if __name__ == "__main__":
    print("=== 기온 테스트 ===")
    print(f"30도 → {get_temp_zone(30)}")   # hot
    print(f"25도 → {get_temp_zone(25)}")   # warm
    print(f"20도 → {get_temp_zone(20)}")   # mild
    print(f"15도 → {get_temp_zone(15)}")   # cool
    print(f"8도  → {get_temp_zone(8)}")    # cold
    print(f"0도  → {get_temp_zone(0)}")    # freeze

    print("\n=== 강수량 테스트 ===")
    print(f"강수없음 → {get_rain_level(['강수없음'])}")  # none
    print(f"1mm 미만 → {get_rain_level(['1mm 미만'])}")  # drizzle
    print(f"5~10mm  → {get_rain_level(['5~10mm'])}")    # heavy

    print("\n=== SK 생성 테스트 ===")
    sk = build_sk("hot", "none", "good")
    print(f"SK: {sk}")

    from itertools import product
    total = len(list(product(TEMP_ZONES, RAIN_LEVELS, PM_GRADES)))
    print(f"\n전체 패턴 수: {total:,}개")