import { ref } from 'vue';

export const currentWeather = ref(null);
export const currentOutfit = ref(null);
export const hourlyData = ref([]);
export const hourlyOutfitData = ref([]);
export const isLoading = ref(false);
export const errorMessage = ref('');

// 상태 코드를 한글로 변환하는 함수 (null 방어 로직 추가)
const getDustStatusText = (statusCode) => {
    if (statusCode === null || statusCode === undefined) return "정보없음";
    const code = String(statusCode);
    if (code === "1") return "좋음";
    if (code === "2") return "보통";
    if (code === "3") return "나쁨";
    if (code === "4") return "매우나쁨";
    return "보통";
};

// Lambda 응답 파싱 헬퍼
const parseLambdaResponse = (raw) => {
    if (raw && typeof raw.body === 'string') {
        return JSON.parse(raw.body);
    }
    return raw;
};

export const fetchWeatherData = async (regionName) => {
    if (currentWeather.value?.location === regionName) return;

    isLoading.value = true;
    errorMessage.value = '';

    try {
        const encodedRegion = encodeURIComponent(regionName);
        
        const weatherApiUrl = `https://ldotjyg6azeu5pjitdud2bpdey0xgkit.lambda-url.us-east-1.on.aws/weather?region=${encodedRegion}`;
        const recommendApiUrl = `https://ldotjyg6azeu5pjitdud2bpdey0xgkit.lambda-url.us-east-1.on.aws/recommend?region=${encodedRegion}`;

        const [weatherRes, recommendRes] = await Promise.all([
            fetch(weatherApiUrl),
            fetch(recommendApiUrl)
        ]);

        if (!weatherRes.ok || !recommendRes.ok) {
            throw new Error(`서버 에러 발생 (날씨: ${weatherRes.status}, 추천: ${recommendRes.status})`);
        }

        const weatherData = parseLambdaResponse(await weatherRes.json());
        const recommendData = parseLambdaResponse(await recommendRes.json());

        // 🌟 백엔드 변경 1: 현재 기온과 예보 기온 분리
        const currentTemp = weatherData.temp !== undefined ? Math.round(Number(weatherData.temp)) : 15;
        const tempForecast = weatherData.tempForecast || [];
        const rainArray = weatherData.rain || [];
        const skyArray = weatherData.sky || [];
        
        // 🌟 백엔드 변경 2: top, bottom 배열을 문자열로 결합하여 기존 UI(.includes) 완벽 호환
        const topStr = Array.isArray(recommendData.top) ? recommendData.top.join(', ') : (recommendData.top || '데이터 없음');
        const bottomStr = Array.isArray(recommendData.bottom) ? recommendData.bottom.join(', ') : (recommendData.bottom || '데이터 없음');

        const updateTime = new Date();
        updateTime.setMinutes(Math.floor(updateTime.getMinutes() / 30) * 30);

        // 1. 현재 날씨 데이터 매핑
        currentWeather.value = {
            location: regionName,
            temp: currentTemp,
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
            reason: recommendData.reason || ''
        };

        const today = new Date();
        today.setMinutes(0, 0, 0);

        // 3. 시간별 예보 데이터 동적 매핑
        hourlyData.value = tempForecast.map((tempStr, index) => {
            const date = new Date(today);
            date.setHours(today.getHours() + index);
            
            return {
                time: date.toLocaleString('ko-KR', { hour: 'numeric', hour12: true }),
                temp: Math.round(Number(tempStr)),
                rain: rainArray[index] || '강수없음',
                sky: skyArray[index] || '맑음',
                pm25: weatherData.pm25 || 0,
                pm25Status: getDustStatusText(weatherData.pm25Grade)
            };
        });

        // 4. 시간별 옷차림 데이터 - 단일 추천값을 모든 시간대에 동일하게 복제
        hourlyOutfitData.value = tempForecast.map((_, index) => {
            const date = new Date(today);
            date.setHours(today.getHours() + index);

            return {
                top: topStr,
                bottom: bottomStr,
                mask: recommendData.mask || '선택 사항',
                pack: recommendData.pack || '불필요',
                time: date.toLocaleString('ko-KR', { hour: 'numeric', hour12: true })
            };
        });

    } catch (error) {
        console.error('데이터 호출 중 오류 발생:', error);
        errorMessage.value = '정보를 가져오는 중 오류가 발생했습니다.';
        currentWeather.value = null;
        currentOutfit.value = null;
        hourlyData.value = [];
        hourlyOutfitData.value = [];
    } finally {
        isLoading.value = false;
    }
};