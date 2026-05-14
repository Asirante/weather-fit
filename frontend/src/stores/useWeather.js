import { defineStore } from 'pinia';

// 상태 코드를 한글로 변환하는 함수
const getDustStatusText = (statusCode) => {
    const code = String(statusCode);
    if (code === "1") return "좋음";
    if (code === "2") return "보통";
    if (code === "3") return "나쁨";
    if (code === "4") return "매우나쁨";
    return "보통";
};

export const useWeatherStore = defineStore('weather', {
    state: () => ({
        weatherData: null,
        recommendData: null,
        currentWeather: null,
        hourlyData: [],
        isLoading: false,
        errorMessage: '',
        currentRegion: ''
    }),
    actions: {
        async fetchWeatherData(regionName) {
            if (this.currentRegion === regionName && this.currentWeather) return;

            this.isLoading = true;
            this.errorMessage = '';
            this.currentRegion = regionName;

            try {
                const encodedRegion = encodeURIComponent(regionName);
                
                // 실제 AWS Lambda API 엔드포인트 적용
                const weatherApiUrl = `https://ldotjyg6azeu5pjitdud2bpdey0xgkit.lambda-url.us-east-1.on.aws/weather?region=${encodedRegion}`;
                const recommendApiUrl = `https://ldotjyg6azeu5pjitdud2bpdey0xgkit.lambda-url.us-east-1.on.aws/recommend?region=${encodedRegion}`;

                const [weatherRes, recommendRes] = await Promise.all([
                    fetch(weatherApiUrl),
                    fetch(recommendApiUrl)
                ]);

                if (!weatherRes.ok || !recommendRes.ok) {
                    throw new Error('데이터를 가져오는데 실패했습니다.');
                }

                const wData = await weatherRes.json();
                const rData = await recommendRes.json(); // { top: [], bottom: [], mask: '', pack: '' }

                this.weatherData = wData;
                this.recommendData = rData;

                // 1. 현재 날씨 세팅
                const now = new Date();
                const hours = now.getHours();
                const minutes = now.getMinutes();
                const formattedTime = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;

                this.currentWeather = {
                    location: regionName,
                    temp: wData.temp[0],
                    rain: wData.rain[0],
                    sky: wData.sky[0],
                    pm10: wData.pm10,
                    pm10Status: getDustStatusText(wData.pm10Status),
                    pm25: wData.pm25,
                    pm25Status: getDustStatusText(wData.pm25Status),
                    o3: wData.o3,
                    updatedAt: formattedTime
                };

                // 2. 시간별 날씨 세팅
                this.hourlyData = wData.temp.slice(0, 6).map((temp, index) => {
                    const futureTime = new Date(now.getTime() + index * 60 * 60 * 1000);
                    const formattedHour = `${futureTime.getHours()}시`;

                    return {
                        time: index === 0 ? '현재' : formattedHour,
                        temp: temp,
                        rain: wData.rain[index],
                        sky: wData.sky[index],
                        pm10Status: this.currentWeather.pm10Status 
                    };
                });

                // 기존 하드코딩되었던 mockOutfits 로직 제거됨 (백엔드 recommendData 대체)

            } catch (err) {
                console.error('API 연동 중 에러 발생:', err);
                this.errorMessage = err.message || '날씨 정보를 불러올 수 없습니다.';
            } finally {
                this.isLoading = false;
            }
        }
    }
});