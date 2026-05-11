<template>
    <main v-if="currentWeather" class="main-content">      
        <div class="top-section">        
            <section class="card current-weather-card">
                <div class="weather-info-left">
                    <div>
                        <span class="placeholder-text">{{ getWeatherIcon(currentWeather.rain, currentWeather.sky) }}</span>                        
                    </div>
                    <div class="weather-details">
                        <h2 v-html="currentWeather.location.replace(' ', '<br>')"></h2>
                        <p class="temp-info">현재 기온 {{ currentWeather.temp }}°C</p>
                        <p class="dust-info">미세먼지 {{ currentWeather.pm10Status }} ({{ currentWeather.pm10 }}µg/m³)</p>
                        <p class="dust-info">초미세먼지 {{ currentWeather.pm25Status }} ({{ currentWeather.pm25 }}µg/m³)</p>                    
                    </div>
                </div>
                <div class="update-time-box">
                    <span class="time-label">갱신 시각</span>
                    <span class="time-value">{{ currentWeather.updatedAt }}</span>
                </div>
            </section>

            <section class="ootd-section">
                <h3 class="section-title">OOTD(오늘의 복장 추천)</h3>
                <div class="ootd-grid">
                    <div v-for="item in displayOotdItems" :key="item.id" class="card ootd-item">
                        <div class="item-icon-ph" style="font-size: 3rem; margin-bottom: 1.5rem;">{{ item.type }}</div>
                        <div class="item-desc">{{ item.description }}</div>
                        <div class="item-name">{{ item.name }}</div>
                    </div>
                </div>
            </section>
        </div>

        <div class="bottom-section">
            <section class="hourly-section">
                <h3 class="section-title">시간별 예보</h3>
                <div class="hourly-flex">
                    <div 
                        v-for="(hour, index) in hourlyData" 
                        :key="index" 
                        class="card hourly-item"
                    >
                        <div class="hour-time">{{ hour.time }}</div>
                        <div class="hour-icon-ph">{{ getWeatherIcon(hour.rain, hour.sky) }}</div>
                        <div class="hour-temp">{{ hour.temp }}°C</div>
                    </div>
                </div>
            </section>

            <section class="card air-quality-card">
                <h3 class="section-title">대기질 현황</h3>
                <div class="aqi-bars">
                    <div v-for="aqi in aqiList" :key="aqi.label" class="aqi-row">
                        <span class="aqi-label">{{ aqi.label }}</span>
                        <div class="progress-bg">
                            <div class="progress-fill" :class="aqi.class" :style="{ width: aqi.width }"></div>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    </main>  
</template>

<script setup>
    import { computed, onMounted } from 'vue';
    import { searchHistory } from '../stores/usehistory';
    import { currentWeather, hourlyData, hourlyOutfitData, fetchWeatherData } from '../stores/useWeather';

    // 화면 진입 시 최우선 실행 로직
    onMounted(() => {
        if (searchHistory.value.length > 0) {
            fetchWeatherData(searchHistory.value[0]);
        } else {
            fetchCurrentLocationWeather();
        }
    });

    const fetchCurrentLocationWeather = () => {
        const fallbackToHistory = () => {
            if (searchHistory.value.length > 0) {
                fetchWeatherData(searchHistory.value[0]);
            } else {
                fetchWeatherData('인천광역시 남동구 구월3동'); // 기본 지역 설정 (인천 시청)
            }
        };

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;

                    if (window.kakao && window.kakao.maps && window.kakao.maps.services) {
                        window.kakao.maps.load(() => {
                            const geocoder = new window.kakao.maps.services.Geocoder();
                            geocoder.coord2RegionCode(lon, lat, (result, status) => {
                                if (status === window.kakao.maps.services.Status.OK) {
                                    const regionInfo = result.find(r => r.region_type === 'H') || result[0];
                                    const currentRegionName = `${regionInfo.region_1depth_name} ${regionInfo.region_2depth_name}`;
                                    fetchWeatherData(currentRegionName);
                                } else {
                                    fallbackToHistory();
                                }
                            });
                        });
                    } else {
                        fallbackToHistory();
                    }
                },
                (error) => {
                    console.warn("위치 권한 에러:", error);
                    fallbackToHistory();
                },
                { timeout: 5000 }
            );
        } else {
            fallbackToHistory();
        }
    };

    // 대기질 현황 계산 (currentWeather 전역 상태 참조)
    const getAqiStyle = (type, value, status) => {
        let max, excellent, good, warning, danger;
  
        if (type === 'PM2.5') { max = 76; }
        else if (type === 'PM10') { max = 151;}
        else if (type === 'O3') { max = 0.15; excellent = 0.000; good = 0.031; warning = 0.091; danger = 0.150; }

        const percentage = Math.min((value / max) * 100, 100);

        let colorClass = 'excellent'; 
        if(status == null) {
            if (value >= danger) colorClass = 'danger'; 
            else if (value >= warning) colorClass = 'warning'; 
            else if (value >= good) colorClass = 'good'; 
            else if (value >= excellent) colorClass = 'excellent';
        } else {
            if (status == 4) colorClass = 'danger';
            else if (status == 3) colorClass = 'warning'; 
            else if (status == 2) colorClass = 'good'; 
            else if (status == 1) colorClass = 'excellent'; 
        }
        return {
            width: `${percentage}%`,
            class: colorClass
        };
    };

    const aqiList = computed(() => {
        if (!currentWeather.value) return [];
        return [
            { label: 'PM2.5', ...getAqiStyle('PM2.5', currentWeather.value.pm25, currentWeather.value.pm25Status) },
            { label: 'PM10', ...getAqiStyle('PM10', currentWeather.value.pm10, currentWeather.value.pm10Status) },
            { label: 'O₃', ...getAqiStyle('O3', currentWeather.value.o3, null) }
        ]
    });

    // OOTD 아이템 동적 계산 (하드코딩 제거 후 백엔드 데이터 매핑)
    const displayOotdItems = computed(() => {
        const weather = hourlyData.value[0] || null;
        // 백엔드에서 받아온 첫 번째 시간대의 옷차림 데이터
        const outfit = hourlyOutfitData.value && hourlyOutfitData.value.length > 0 ? hourlyOutfitData.value[0] : null;
        const items = [];

        // 날씨나 옷차림 데이터가 아직 없으면 빈 배열 반환
        if (!weather || !outfit) return items;


        // 1. 상의 - 내용에 따라 아이콘 동적 변경
        if (outfit.top.includes('반팔')){
            items.push({ 
                id: 1, 
                type: '👕', 
                name: outfit.top, 
                description: '추천 상의' 
            });
        } else if (outfit.top.includes('긴팔')){
            items.push({ 
                id: 1, 
                type: '👔', 
                name: outfit.top, 
                description: '추천 상의' 
            });
        } else if (outfit.top.includes('재킷')){
            items.push({ 
                id: 1, 
                type: '🧥', 
                name: outfit.top, 
                description: '추천 상의' 
            });
        } else if (outfit.top.includes('가죽')){
            items.push({ 
                id: 1, 
                type: '🧥', 
                name: outfit.top, 
                description: '추천 상의' 
            });
        } else if (outfit.top.includes('패딩')){
            items.push({ 
                id: 1, 
                type: '🧣', 
                name: outfit.top, 
                description: '추천 상의' 
            });
        }

        // 2. 하의
        if (outfit.bottom.includes('반바지')){
            items.push({ 
                id: 2, 
                type: '🩳', 
                name: outfit.bottom, 
                description: '추천 하의' 
            });
        } else {
            items.push({ 
                id: 2, 
                type: '👖', 
                name: outfit.bottom, 
                description: '추천 하의' 
            });
        }

        // 3. 준비물 (pack) - 내용에 따라 아이콘 동적 변경
        let packIcon = '✋';
        if (outfit.pack.includes('우산')) packIcon = '☔';
        else if (weather.sky.includes('눈')) packIcon = '🌨️';

        items.push({ 
            id: 3, 
            type: packIcon, 
            name: outfit.pack === '불필요' ? '없음' : outfit.pack, 
            description: '추천 소지품'
        });

        // 4. 마스크
        items.push({ 
            id: 4, 
            type: '😷', 
            name: outfit.mask ===  '마스트 선택' ? '자유' : outfit.mask,  
            description: '마스크 추천' 
        });

        return items;
    });

    const getWeatherIcon = (rain, sky) => {
        switch (rain) {
            case '강수없음': 
                if (sky === '맑음') return '☀️';
                if (sky === '흐림') return '⛅';
                break;
            default:
                if (sky.includes('비')) return '🌧️';
                if (sky.includes('눈')) return '🌨️';
                if (sky.includes('흐림')) return '⛅';
                break;
        }
    };

</script>
<style scoped>
    /* ---------------- 공통 요소 ---------------- */
    .card { background-color: #FFFFFF; border-radius: 12px; border: 1px solid var(--color-neutral-200); box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); }
    .section-title { font-size: 1.25rem; font-weight: 700; margin: 0 0 1rem 0; color: var(--color-text-900); }
    .placeholder-text { color: var(--color-text-400); font-size: 5rem; }
    .item-icon-ph { color: var(--color-text-400); font-size: 0.85rem; text-align: center; line-height: 1.4; }
    .hour-icon-ph { color: var(--color-text-400); font-size: 2.5rem; }
    .main-content{ max-width: 1200px; width: 100%; margin-left: auto; margin-right: auto; padding: 0 1rem; box-sizing: border-box; }
    .main-content { margin-top: 5rem; margin-bottom: 5rem; display: flex; flex-direction: column; gap: 2rem; }

    /* --- 상단 영역 --- */
    .top-section { display: grid; grid-template-columns: 1fr 1.3fr; gap: 2rem; }
    .current-weather-card { display: flex; justify-content: space-between; align-items: center; padding: 2rem; }
    .weather-info-left { display: flex; align-items: center; gap: 1.5rem; }
    .weather-details h2 { font-size: 1.35rem; margin: 0 0 0.75rem 0; color: var(--color-text-900); white-space: pre-wrap; }   
    .temp-info { color: var(--color-text-600); margin: 0 0 0.5rem 0; }
    .dust-info { color: var(--color-text-600); margin: 0 0 0.25rem 0; font-size: 0.9rem; }
    .update-time-box { background-color: var(--color-neutral-50); border: 1px solid var(--color-neutral-200); border-radius: 12px; padding: 1.5rem 1.2rem; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .time-label { color: var(--color-text-600); font-size: 0.75rem; margin-bottom: 0.5rem; text-align: center; white-space: nowrap;}
    .time-value { color: var(--color-text-600); font-size: 0.75rem; text-align: center; white-space: nowrap; }

    /* OOTD 영역 */
    .ootd-section { display: flex; flex-direction: column; }
    .ootd-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; flex: 1; }
    .ootd-item { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 1.5rem 1rem; }
    .item-icon-ph { margin-bottom: 1.5rem; height: 40px; }
    .item-desc { font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--color-text-900); text-align: center;}
    .item-name { color: var(--color-text-600); font-size: 0.85rem; text-align: center;}

    /* --- 하단 영역 --- */
    .bottom-section { display: grid; grid-template-columns: 1fr 320px; gap: 2rem; }
    .hourly-section { display: flex; flex-direction: column; }
    .hourly-flex { display: flex; gap: 1rem; }
    .hourly-item { flex: 1; display: flex; flex-direction: column; align-items: center; padding: 1.5rem 0.5rem; }
    .hour-time { font-size: 0.9rem; color: var(--color-text-900); margin-bottom: 1.5rem; }
    .hour-icon-ph { margin-bottom: 1.5rem; }
    .hour-temp { font-weight: 600; font-size: 1.1rem; color: var(--color-text-900); }

    /* 대기질 현황 */
    .air-quality-card { padding: 2rem; }
    .aqi-bars { display: flex; flex-direction: column; gap: 1.25rem; }
    .aqi-row { display: flex; align-items: center; }
    .aqi-label { width: 60px; font-size: 0.9rem; color: var(--color-text-600); }   
    .progress-bg { flex: 1; height: 14px; background-color: var(--color-neutral-200); border-radius: 8px; overflow: hidden; }
    .progress-fill { height: 100%; border-radius: 8px; transition: width 0.8s ease-in-out, background-color 0.8s ease; }
    .progress-fill.excellent { background-color: #3B82F6; } 
    .progress-fill.good { background-color: #10B981; }      
    .progress-fill.warning { background-color: var(--color-amber-500); } 
    .progress-fill.danger { background-color: var(--color-red-500); }    
</style>