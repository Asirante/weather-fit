import { ref } from 'vue';

export const currentWeather = ref(null);
export const currentOutfit = ref(null);
export const hourlyData = ref([]);
export const hourlyOutfitData = ref([]);
export const isLoading = ref(false);
export const errorMessage = ref('');

// 상태 코드를 한글로 변환하는 함수
const getDustStatusText = (statusCode) => {
    const code = String(statusCode);
    if (code === "1") return "좋음";
    if (code === "2") return "보통";
    if (code === "3") return "나쁨";
    if (code === "4") return "매우나쁨";
    return "보통";
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

        const weatherData = await weatherRes.json();
        // ✅ 수정: /recommend는 배열을 반환하므로 배열로 받음
        const recommendList = await recommendRes.json();

        // 백엔드에서 받은 배열 데이터 추출
        const tempArray = weatherData.temp || [];
        const rainArray = weatherData.rain || [];
        const skyArray = weatherData.sky || [];
        const updateTime = new Date();

        updateTime.setMinutes(Math.floor(updateTime.getMinutes() / 30) * 30);

        // 1. 현재 날씨 데이터 매핑 (배열의 첫 번째 값을 현재 날씨로 사용)
        currentWeather.value = {
            location: regionName,
            temp: tempArray.length > 0 ? Math.round(Number(tempArray[0])) : 15,
            pm10Status: getDustStatusText(weatherData.pm10Status),
            pm10: weatherData.pm10 || 0,
            pm25Status: getDustStatusText(weatherData.pm25Status),
            pm25: weatherData.pm25 || 0,
            o3: weatherData.o3 || 0,
            rain: rainArray.length > 0 ? rainArray[0] : '강수없음',
            sky: skyArray.length > 0 ? skyArray[0] : '맑음',
            updatedAt: updateTime.toLocaleTimeString('ko-KR', { hour: 'numeric', minute: 'numeric', hour12: true })
        };

        // 2. 현재 옷차림 추천 데이터 매핑 (배열의 첫 번째 항목)
        const firstOutfit = Array.isArray(recommendList) && recommendList.length > 0 ? recommendList[0] : {};
        currentOutfit.value = {
            top: firstOutfit.top || '데이터 없음',
            bottom: firstOutfit.bottom || '데이터 없음',
            mask: firstOutfit.mask || '선택 사항',
            pack: firstOutfit.pack || '불필요'
        };

        const today = new Date();
        today.setMinutes(0, 0, 0);

        // 3. 시간별 예보 데이터 동적 매핑
        hourlyData.value = tempArray.map((tempStr, index) => {
            const date = new Date(today);
            date.setHours(today.getHours() + index);
            
            return {
                time: date.toLocaleString('ko-KR', { hour: 'numeric', hour12: true }),
                temp: Math.round(Number(tempStr)),
                rain: rainArray[index] || '강수없음',
                sky: skyArray[index] || '맑음',
                pm25: weatherData.pm25 || 0,
                pm25Status: getDustStatusText(weatherData.pm25Status)
            };
        });

        // ✅ 수정: mockOutfits 제거 → 백엔드의 실제 시간별 추천 데이터를 그대로 사용
        hourlyOutfitData.value = tempArray.map((_, index) => {
            const date = new Date(today);
            date.setHours(today.getHours() + index);

            // 백엔드 배열에 해당 인덱스가 있으면 사용, 없으면 첫 번째 항목으로 폴백
            const outfit = (Array.isArray(recommendList) && recommendList[index]) 
                ? recommendList[index] 
                : firstOutfit;

            return {
                top: outfit.top || '데이터 없음',
                bottom: outfit.bottom || '데이터 없음',
                mask: outfit.mask || '선택 사항',
                pack: outfit.pack || '불필요',
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