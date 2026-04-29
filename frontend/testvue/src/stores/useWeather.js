import { ref } from 'vue';

export const currentWeather = ref(null);
export const currentOutfit = ref(null);
export const hourlyData = ref([]);
export const hourlyOutfitData = ref([]); // 🌟 시간별 옷차림 데이터를 담을 ref 추가
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
        const recommendData = await recommendRes.json();

        // 1. 날씨 데이터 매핑
        currentWeather.value = {
            location: regionName,
            temp: Math.round(weatherData.temp) || 15,
            pm10Status: getDustStatusText(weatherData.pm10Status),
            pm10: weatherData.pm10 || 0,
            pm25Status: getDustStatusText(weatherData.pm25Status),
            pm25: weatherData.pm25 || 0,
            o3: weatherData.o3 || 0,
            pop: weatherData.pop || 0,
            popform: weatherData.popform || '맑음',
            updatedAt: new Date().toLocaleTimeString('ko-KR', { hour: 'numeric', minute: 'numeric', hour12: true })
        };

        // 2. 현재 옷차림 추천 데이터 매핑
        currentOutfit.value = {
            top: recommendData.top || '데이터 없음',
            bottom: recommendData.bottom || '데이터 없음',
            mask: recommendData.mask || '선택 사항',
            pack: recommendData.pack || '불필요'
        };

        // 3. 시간별 예보 임시 데이터
        const today = new Date();
        hourlyData.value = (weatherData.hourlyData || [
            { time: 0, temp: currentWeather.value.temp, pop: currentWeather.value.pop, popform: currentWeather.value.popform, pm25: currentWeather.value.pm25, pm25Status: currentWeather.value.pm25Status }, 
            { time: 0, temp: 15, pop: 0, popform: '맑음', pm25: 35, pm25Status: '보통' },
            { time: 0, temp: 15, pop: 40, popform: '비', pm25: 25, pm25Status: '좋음' },
            { time: 0, temp: 14, pop: 90, popform: '눈', pm25: 20, pm25Status: '좋음' },
            { time: 0, temp: 12, pop: 20, popform: '눈', pm25: 45, pm25Status: '나쁨' },
            { time: 0, temp: 10, pop: 0, popform: '맑음', pm25: 60, pm25Status: '매우나쁨' }
        ]).map((item, index) => {
            const date = new Date(today);
            date.setHours(today.getHours() + index + 1);
            return { 
                ...item, 
                time: date.toLocaleString('ko-KR', { hour: 'numeric', hour12: true }) 
            };
        });

        // 4.시간별 옷차림 임시 데이터 (시간별 날씨 상황에 맞춰 구성)
        // 백엔드에서 나중에 이 데이터를 제공하면 recommendData.hourlyOutfitData 등으로 교체하면 됩니다.
        hourlyOutfitData.value = [
            { time: 0, top: currentOutfit.value.top, bottom: currentOutfit.value.bottom, mask: currentOutfit.value.mask, pack: currentOutfit.value.pack }, // 첫 시간은 현재 옷차림
            { time: 0, top: "민소매, 반팔 린넨소재", bottom: "반바지, 짧은 치마, 린넨 소재", mask: "마스크 선택", pack: "불필요" },           // 기온 15도, 맑음
            { time: 0, top: "코트, 가죽재킷, 두꺼운 니트", bottom: "반바지, 면바지", mask: "마스크 선택", pack: "장 우산" },           // 기온 15도, 비
            { time: 0, top: "긴팔 티셔츠, 가디건 후드티, 맨투맨", bottom: "청바지, 두꺼운 긴바지, 기모바지", mask: "kf80 권장", pack: "장 우산, 레인부츠" },                 // 기온 14도, 눈
            { time: 0, top: "가디건, 야상, 재킷, 니트", bottom: "방한복, 기모 이너", mask: "kf94 필수", pack: "장 우산" },                 // 기온 12도, 눈, 미세먼지 나쁨
            { time: 0, top: "패팅, 두꺼운 롱코트, 방한복, 기모 이너", bottom: "반바지, 면바지", mask: "kf80 권장", pack: "불필요" }               // 기온 10도, 맑음, 미세먼지 매우나쁨
        ].map((item, index) => {
            const date = new Date(today);
            date.setHours(today.getHours() + index + 1); // 시간별 예보와 동일하게 시간 세팅
            return { 
                ...item, 
                time: date.toLocaleString('ko-KR', { hour: 'numeric', hour12: true }) 
            };
        });

    } catch (error) {
        console.error('데이터 호출 중 오류 발생:', error);
        errorMessage.value = '정보를 가져오는 중 오류가 발생했습니다.';
        currentWeather.value = null;
        currentOutfit.value = null;
        hourlyData.value = [];
        hourlyOutfitData.value = []; // 🌟 에러 시 초기화
    } finally {
        isLoading.value = false;
    }
};