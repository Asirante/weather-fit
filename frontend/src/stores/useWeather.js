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

        // 🌟 백엔드에서 받은 배열 데이터 추출 (안전하게 빈 배열 폴백 추가)
        const tempArray = weatherData.temp || [];
        const rainArray = weatherData.rain || [];

        // 1. 현재 날씨 데이터 매핑 (배열의 첫 번째 값을 현재 날씨로 사용)
        currentWeather.value = {
            location: regionName,
            temp: tempArray.length > 0 ? Math.round(Number(tempArray[0])) : 15,
            pm10Status: getDustStatusText(weatherData.pm10Status),
            pm10: weatherData.pm10 || 0,
            pm25Status: getDustStatusText(weatherData.pm25Status),
            pm25: weatherData.pm25 || 0,
            o3: weatherData.o3 || 0,
            rain: rainArray.length > 0 ? rainArray[0] : '강수없음', // pop, popform을 rain으로 통합
            updatedAt: new Date().toLocaleTimeString('ko-KR', { hour: 'numeric', minute: 'numeric', hour12: true })
        };

        // 2. 현재 옷차림 추천 데이터 매핑
        currentOutfit.value = {
            top: recommendData.top || '데이터 없음',
            bottom: recommendData.bottom || '데이터 없음',
            mask: recommendData.mask || '선택 사항',
            pack: recommendData.pack || '불필요'
        };

        const today = new Date();
        today.setMinutes(0, 0, 0);

        // 시간별 예보 데이터 동적 매핑 (temp 배열 길이만큼 생성)
        hourlyData.value = tempArray.map((tempStr, index) => {
            const date = new Date(today);
            date.setHours(today.getHours() + index);
            
            return {
                time: date.toLocaleString('ko-KR', { hour: 'numeric', hour12: true }),
                temp: Math.round(Number(tempStr)), // 시간별 기온 (배열에서 추출)
                rain: rainArray[index] || '강수없음', // 시간별 강수 (배열에서 추출)
                pm25: weatherData.pm25 || 0, // 하루 단위 동일 데이터
                pm25Status: getDustStatusText(weatherData.pm25Status) // 하루 단위 동일 데이터
            };
        });

        // 4. 시간별 옷차림 임시 데이터 (시간별 날씨 상황에 맞춰 구성)
        const mockOutfits = [
            { top: currentOutfit.value.top, bottom: currentOutfit.value.bottom, mask: currentOutfit.value.mask, pack: currentOutfit.value.pack }, // 첫 시간은 현재 옷차림
            { top: "민소매, 반팔 린넨소재", bottom: "반바지, 짧은 치마, 린넨 소재", mask: "마스크 선택", pack: "불필요" },
            { top: "코트, 가죽재킷, 두꺼운 니트", bottom: "반바지, 면바지", mask: "마스크 선택", pack: "장 우산" },
            { top: "긴팔 티셔츠, 가디건 후드티, 맨투맨", bottom: "청바지, 두꺼운 긴바지, 기모바지", mask: "kf80 권장", pack: "장 우산, 레인부츠" },
            { top: "가디건, 야상, 재킷, 니트", bottom: "방한복, 기모 이너", mask: "kf94 필수", pack: "장 우산" },
            { top: "패딩, 두꺼운 롱코트, 방한복, 기모 이너", bottom: "반바지, 면바지", mask: "kf80 권장", pack: "불필요" }
        ];

        hourlyOutfitData.value = mockOutfits.slice(0, tempArray.length).map((item, index) => {
            const date = new Date(today);
            date.setHours(today.getHours() + index);
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
        hourlyOutfitData.value = []; 
    } finally {
        isLoading.value = false;
    }
};