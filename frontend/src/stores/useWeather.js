import { ref } from 'vue';

export const currentWeather = ref(null);
export const currentOutfit = ref(null);
export const hourlyData = ref([]);
export const hourlyOutfitData = ref([]);
export const isLoading = ref(false);
export const errorMessage = ref('');

// 상태 코드를 한글로 변환하는 함수 (null 방어 로직 추가)
export const getDustStatusText = (statusCode) => {
    if (statusCode === null || statusCode === undefined) return "정보없음";
    const code = String(statusCode);
    if (code === "1") return "좋음";
    if (code === "2") return "보통";
    if (code === "3") return "나쁨";
    if (code === "4") return "매우나쁨";
    return "보통";
};

// Lambda 응답 파싱 헬퍼
export const parseLambdaResponse = (raw) => {
    if (raw && typeof raw.body === 'string') {
        return JSON.parse(raw.body);
    }
    return raw;
};

// 백엔드 관측 기준 시각(baseDate "YYYYMMDD" + baseTime "HHMM") → Date
export const parseBaseDateTime = (baseDate, baseTime) => {
    if (!baseDate || !baseTime) return null;
    const d = String(baseDate);
    const t = String(baseTime).padStart(4, '0');
    if (d.length < 8 || t.length < 4) return null;
    const dt = new Date(
        Number(d.slice(0, 4)),
        Number(d.slice(4, 6)) - 1,
        Number(d.slice(6, 8)),
        Number(t.slice(0, 2)),
        Number(t.slice(2, 4))
    );
    return isNaN(dt.getTime()) ? null : dt;
};

// UV 지수 → 한글 단계 (기상청 기준)
export const getUvLevel = (uv) => {
    if (uv == null) return null;
    const v = Number(uv);
    if (v >= 11) return '위험';
    if (v >= 8) return '매우높음';
    if (v >= 6) return '높음';
    if (v >= 3) return '보통';
    return '낮음';
};

// 네트워크 안정화 설정
const REQUEST_TIMEOUT_MS = 8000; // 단일 요청 타임아웃 (콜드스타트 대비)
const MAX_ATTEMPTS = 3;          // 최초 1회 + 재시도 2회

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// 타임아웃이 적용된 fetch (AbortController) — 무한 대기 방지
const fetchWithTimeout = async (url, ms = REQUEST_TIMEOUT_MS) => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), ms);
    try {
        return await fetch(url, { signal: controller.signal });
    } finally {
        clearTimeout(timer);
    }
};

// 날씨/추천 API를 1회 호출하고 파싱된 결과를 반환 (실패 시 throw)
const requestWeatherOnce = async (encodedRegion) => {
    const base = 'https://ldotjyg6azeu5pjitdud2bpdey0xgkit.lambda-url.us-east-1.on.aws';
    const [weatherRes, recommendRes] = await Promise.all([
        fetchWithTimeout(`${base}/weather?region=${encodedRegion}`),
        fetchWithTimeout(`${base}/recommend?region=${encodedRegion}`)
    ]);

    if (!weatherRes.ok || !recommendRes.ok) {
        throw new Error(`서버 에러 발생 (날씨: ${weatherRes.status}, 추천: ${recommendRes.status})`);
    }

    return {
        weatherData: parseLambdaResponse(await weatherRes.json()),
        recommendData: parseLambdaResponse(await recommendRes.json())
    };
};

// 최신 요청 추적 (지역을 빠르게 바꿀 때 오래된 응답이 화면을 덮어쓰지 않도록)
let activeRequestId = 0;

export const fetchWeatherData = async (regionName) => {
    // 동일 지역도 항상 최신 데이터로 새로고침 (현재위치/다시시도 버튼이 동작하도록)
    const requestId = ++activeRequestId;

    isLoading.value = true;
    errorMessage.value = '';

    try {
        const encodedRegion = encodeURIComponent(regionName);

        // 실패(네트워크/타임아웃/5xx) 시 지수 백오프로 재시도
        let weatherData, recommendData;
        for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            try {
                ({ weatherData, recommendData } = await requestWeatherOnce(encodedRegion));
                break;
            } catch (err) {
                if (attempt === MAX_ATTEMPTS) throw err;
                console.warn(`날씨 요청 실패 (${attempt}/${MAX_ATTEMPTS}), 재시도합니다.`, err);
                await sleep(500 * attempt); // 0.5s, 1s
            }
        }

        // 더 새로운 요청이 시작됐다면 이 응답은 버림 (레이스 방지)
        if (requestId !== activeRequestId) return;

        // 🌟 백엔드 변경 1: 현재 기온과 예보 기온 분리
        const currentTemp = weatherData.temp !== undefined ? Math.round(Number(weatherData.temp)) : 15;
        const tempForecast = weatherData.tempForecast || [];
        const feelsLikeForecast = weatherData.feelsLikeForecast || [];
        // 체감온도는 구버전 백엔드에선 없을 수 있으므로 방어적으로 처리
        const currentFeelsLike = weatherData.feelsLike != null ? Math.round(Number(weatherData.feelsLike)) : null;
        const rainArray = weatherData.rain || [];
        const skyArray = weatherData.sky || [];
        
        // 🌟 백엔드 변경 2: top, bottom 배열을 문자열로 결합하여 기존 UI(.includes) 완벽 호환
        const topStr = Array.isArray(recommendData.top) ? recommendData.top.join(', ') : (recommendData.top || '데이터 없음');
        const bottomStr = Array.isArray(recommendData.bottom) ? recommendData.bottom.join(', ') : (recommendData.bottom || '데이터 없음');

        // 갱신 시각: 백엔드 관측 기준 시각(baseDate/baseTime) 우선, 없으면 현재 시각으로 폴백
        const baseDateTime = parseBaseDateTime(weatherData.baseDate, weatherData.baseTime);
        const updateTime = baseDateTime || new Date();
        if (!baseDateTime) {
            updateTime.setMinutes(Math.floor(updateTime.getMinutes() / 30) * 30);
        }

        // UV 지수 (구버전 백엔드 대비 방어)
        const uvValue = weatherData.uv != null ? Number(weatherData.uv) : null;

        // 1. 현재 날씨 데이터 매핑
        currentWeather.value = {
            location: regionName,
            temp: currentTemp,
            feelsLike: currentFeelsLike,
            uv: uvValue,
            uvLevel: getUvLevel(uvValue),
            pm10Status: getDustStatusText(weatherData.pm10Grade),
            pm10: weatherData.pm10 || 0,
            pm25Status: getDustStatusText(weatherData.pm25Grade),
            pm25: weatherData.pm25 || 0,
            o3: weatherData.o3 || 0,
            rain: rainArray.length > 0 ? rainArray[0] : '강수없음',
            sky: skyArray.length > 0 ? skyArray[0] : '맑음',
            updatedAt: updateTime.toLocaleTimeString('ko-KR', { hour: 'numeric', minute: 'numeric', hour12: true })
        };

        // 2. 현재 옷차림 추천 데이터 매핑
        currentOutfit.value = {
            top: topStr,
            bottom: bottomStr,
            mask: recommendData.mask || '선택 사항',
            pack: recommendData.pack || '불필요',
            acc: Array.isArray(recommendData.acc) ? recommendData.acc : [],
            reason: recommendData.reason || ''
        };

        const today = new Date();
        today.setMinutes(0, 0, 0);

        // 백엔드가 준 실제 예보 시각(YYYYMMDDHHMM)으로 라벨링.
        // 없으면(구버전 백엔드) 현재 시각 + index 로 폴백.
        const forecastTimes = weatherData.forecastTimes || [];
        const labelForIndex = (index) => {
            const ft = forecastTimes[index];
            if (ft) {
                const s = String(ft);
                const dt = parseBaseDateTime(s.slice(0, 8), s.slice(8));
                if (dt) return dt.toLocaleString('ko-KR', { hour: 'numeric', hour12: true });
            }
            const date = new Date(today);
            date.setHours(today.getHours() + index);
            return date.toLocaleString('ko-KR', { hour: 'numeric', hour12: true });
        };

        // 3. 시간별 예보 데이터 동적 매핑
        hourlyData.value = tempForecast.map((tempStr, index) => {
            return {
                time: labelForIndex(index),
                temp: Math.round(Number(tempStr)),
                feelsLike: feelsLikeForecast[index] != null ? Math.round(Number(feelsLikeForecast[index])) : null,
                rain: rainArray[index] || '강수없음',
                sky: skyArray[index] || '맑음',
                pm25: weatherData.pm25 || 0,
                pm25Status: getDustStatusText(weatherData.pm25Grade)
            };
        });

        // 4. 시간별 옷차림 데이터 - 단일 추천값을 모든 시간대에 동일하게 복제
        hourlyOutfitData.value = tempForecast.map((_, index) => {
            return {
                top: topStr,
                bottom: bottomStr,
                mask: recommendData.mask || '선택 사항',
                pack: recommendData.pack || '불필요',
                time: labelForIndex(index)
            };
        });

    } catch (error) {
        // 오래된(중첩된) 요청의 실패는 화면에 반영하지 않음
        if (requestId !== activeRequestId) return;
        console.error('데이터 호출 중 오류 발생:', error);
        errorMessage.value = '정보를 가져오는 중 오류가 발생했습니다.';
        currentWeather.value = null;
        currentOutfit.value = null;
        hourlyData.value = [];
        hourlyOutfitData.value = [];
    } finally {
        // 최신 요청일 때만 로딩 해제 (오래된 요청이 새 로딩을 끄지 않도록)
        if (requestId === activeRequestId) isLoading.value = false;
    }
};