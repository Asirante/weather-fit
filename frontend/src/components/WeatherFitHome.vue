<template>
    <div v-if="isLoading || isInitializing" class="loading-screen">
        <div class="spinner"></div>
        <p>날씨 데이터를 분석하고 있습니다...</p>
    </div>

    <template v-else-if="currentWeather">
        <main class="main-content">      
            <div class="top-section">        
                <section class="card current-weather-card">
                    
                    <div class="weather-info-left">
                        <div class="icon-wrapper">
                            <span class="placeholder-text">{{ getWeatherIcon(currentWeather.rain, currentWeather.sky) }}</span>                        
                        </div>
                        <div class="weather-details">
                            <div class="location-header">
                                <h2>{{ currentWeather.location }}</h2>
                            </div>
                            <p class="temp-info">현재 기온 {{ currentWeather.temp }}°C</p>
                            <p class="dust-info">미세먼지 {{ currentWeather.pm10Status }} ({{ currentWeather.pm10 }}µg/m³)</p>
                            <p class="dust-info">초미세먼지 {{ currentWeather.pm25Status }} ({{ currentWeather.pm25 }}µg/m³)</p>                    
                        </div>
                    </div>
                    
                    <div class="weather-info-right">
                        <button class="current-loc-btn" @click="fetchCurrentLocationWeather" title="현재 위치 날씨 가져오기">
                            현재 위치 확인
                        </button>
                        <div class="update-time-box">
                            <span class="time-label">갱신 시각</span>
                            <span class="time-value">{{ currentWeather.updatedAt }}</span>
                        </div>
                    </div>
                </section>

                <section class="ootd-section">
                    <h3 class="section-title">OOTD ({{ hourlyData[0]?.time }} 기준)</h3>
                    
                    <p v-if="currentOutfit?.reason" class="ai-reason">
                        💡AI 한줄평 : {{ currentOutfit.reason }}
                    </p>

                    <div class="ootd-grid">
                        <div v-for="item in displayOotdItems" :key="item.id" class="card ootd-item">
                            <div class="item-icon-ph">{{ item.type }}</div>
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
                        <div v-for="hour in hourlyData" :key="hour.time" class="card hourly-item">
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
                    <div class="aqi-summary">
                        <p class="dust-info">PM10 : {{ currentWeather.pm10Status }} | PM2.5 : {{ currentWeather.pm25Status }} | O₃ : {{ currentWeather.o3 }}</p>
                    </div>
                </section>
            </div>
        </main>
    </template>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { searchHistory } from '../stores/usehistory';
import { currentWeather, currentOutfit, hourlyData, hourlyOutfitData, fetchWeatherData, isLoading } from '../stores/useWeather';

const route = useRoute();
const router = useRouter();
const isInitializing = ref(true);

onMounted(async () => {
    if (route.query.region) {
        await fetchWeatherData(route.query.region);
        isInitializing.value = false;
    } else {
        fetchCurrentLocationWeather();
    }
});

const fallbackToHistory = async () => {
    if (searchHistory.value.length > 0) {
        await fetchWeatherData(searchHistory.value[0]);
    } else {
        await fetchWeatherData('인천광역시 남동구 구월3동'); 
    }
    isInitializing.value = false;
};

const runKakaoMapGeocode = (lat, lon, retryCount = 0) => {
    if (window.kakao && window.kakao.maps && window.kakao.maps.services) {
        window.kakao.maps.load(() => {
            const geocoder = new window.kakao.maps.services.Geocoder();
            geocoder.coord2RegionCode(lon, lat, async (result, status) => {
                if (status === window.kakao.maps.services.Status.OK) {
                    const regionInfo = result.find(r => r.region_type === 'H') || result[0];
                    const currentRegionName = `${regionInfo.region_1depth_name} ${regionInfo.region_2depth_name} ${regionInfo.region_3depth_name}`.trim();
                    
                    await fetchWeatherData(currentRegionName);
                    
                    if (!currentWeather.value) {
                        fallbackToHistory();
                    } else {
                        isInitializing.value = false;
                    }
                } else {
                    fallbackToHistory();
                }
            });
        });
    } else {
        if (retryCount < 10) {
            setTimeout(() => runKakaoMapGeocode(lat, lon, retryCount + 1), 500);
        } else {
            fallbackToHistory();
        }
    }
};

const fetchCurrentLocationWeather = () => {
    isInitializing.value = true; 
    
    if (route.query.region) {
        router.replace({ path: route.path });
    }

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                runKakaoMapGeocode(lat, lon); 
            },
            (error) => {
                console.error('Geolocation error:', error);
                fallbackToHistory();
            },
            { timeout: 10000, enableHighAccuracy: false, maximumAge: 0 } 
        );
    } else {
        fallbackToHistory();
    }
};

const getAqiStyle = (type, value, status) => {
    let max = 100, good = 0, warning = 0, danger = 0;

    if (type === 'PM2.5') { max = 76; }
    else if (type === 'PM10') { max = 151; }
    else if (type === 'O3') { 
        max = 0.15; good = 0.031; warning = 0.091; danger = 0.150; 
    }

    const percentage = Math.min((value / max) * 100, 100);
    let colorClass = 'excellent'; 

    if (status === '매우나쁨' || status === '나쁨') colorClass = 'danger';
    else if (status === '보통' || status === '정보없음') colorClass = 'warning';
    else if (status === '좋음') colorClass = 'good';
    else if (value != null) {
        if (value >= danger) colorClass = 'danger'; 
        else if (value >= warning) colorClass = 'warning'; 
        else if (value >= good) colorClass = 'good'; 
    }

    return { width: `${percentage}%`, class: colorClass };
};

const aqiList = computed(() => {
    if (!currentWeather.value) return [];
    return [
        { label: 'PM2.5', ...getAqiStyle('PM2.5', currentWeather.value.pm25, currentWeather.value.pm25Status) },
        { label: 'PM10', ...getAqiStyle('PM10', currentWeather.value.pm10, currentWeather.value.pm10Status) },
        { label: 'O₃', ...getAqiStyle('O3', currentWeather.value.o3, null) }
    ]
});

// 🌟 쓸데없는 index 의존성 완전히 제거 (무조건 [0] 사용)
const displayOotdItems = computed(() => {
    const weather = hourlyData.value[0] || null;
    const outfit = hourlyOutfitData.value?.length > 0 ? hourlyOutfitData.value[0] : null;

    if (!weather || !outfit) return [];

    let topIcon = '👕';
    if (outfit.top.includes('긴팔')) topIcon = '👔';
    else if (outfit.top.includes('재킷') || outfit.top.includes('가죽') || outfit.top.includes('야상')) topIcon = '🧥';
    else if (outfit.top.includes('패딩') || outfit.top.includes('코트')) topIcon = '🧣';

    let bottomIcon = outfit.bottom.includes('반바지') || outfit.bottom.includes('치마') ? '🩳' : '👖';

    let packIcon = '✋';
    if (outfit.pack.includes('우산')) packIcon = '☔';
    else if (weather.sky?.includes('눈')) packIcon = '🌨️';

    return [
        { id: 1, type: topIcon, name: outfit.top, description: '추천 상의' },
        { id: 2, type: bottomIcon, name: outfit.bottom, description: '추천 하의' },
        { id: 3, type: packIcon, name: outfit.pack === '불필요' ? '없음' : outfit.pack, description: '추천 소지품' },
        { id: 4, type: '😷', name: outfit.mask === '마스크 선택' ? '자유' : outfit.mask, description: '마스크 추천' }
    ];
});

const getWeatherIcon = (rain, sky) => {
    if(!sky) return '🌤️'; 
    if (rain === '강수없음') {
        if (sky === '맑음') return '☀️';
        if (sky === '흐림') return '⛅';
    } else {
        if (sky.includes('비')) return '🌧️';
        if (sky.includes('눈')) return '🌨️';
        if (sky.includes('흐림')) return '⛅';
    }
    return '🌤️';
};
</script>

<style scoped>
/* 🌟 우측 삐져나가는 여백 원천 차단 */
.main-content {
    max-width: 1200px !important;
    width: 100% !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    box-sizing: border-box !important;
    margin-top: 3rem !important;
    margin-bottom: 2rem !important;
    display: flex;
    flex-direction: column;
    gap: 2rem;
    overflow-x: hidden; /* 가로 스크롤 바 완벽 제거 */
}

.card { 
    background-color: #FFFFFF; 
    border-radius: 12px; 
    border: 1px solid var(--color-neutral-200); 
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); 
    box-sizing: border-box; /* 패딩 삐져나옴 방지 */
}

.section-title { 
    font-size: 1.25rem; 
    font-weight: 700; 
    margin: 0 0 1rem 0; 
    color: var(--color-text-900); 
}

.ai-reason {
    font-size: 1.05rem;
    color: var(--color-amber-600);
    background: #FFFBEB;
    padding: 0.8rem 1.2rem;
    border-radius: 8px;
    margin-top: 0;
    margin-bottom: 1.5rem;
    font-weight: 600;
    display: inline-block;
}

.top-section { 
    display: grid; 
    grid-template-columns: 1fr 1.3fr; 
    gap: 2rem; 
}

.current-weather-card { 
    display: flex; 
    justify-content: space-between; 
    align-items: center; 
    padding: 2rem; 
    gap: 1rem; 
}

.weather-info-left { 
    display: flex; 
    align-items: center; 
    gap: 1.5rem; 
    flex: 1; 
    min-width: 0; 
}

.icon-wrapper {
    flex-shrink: 0; 
}

.weather-details {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0; 
    width: 100%;
}

.location-header {
    margin-bottom: 0.75rem;
}

.weather-details h2 { 
    font-size: 1.35rem; 
    margin: 0; 
    color: var(--color-text-900); 
    word-break: break-all; /* 단어가 길어도 화면 밖으로 삐져나가지 않도록 강제 줄바꿈 */
    line-height: 1.3;
}   

.weather-info-right {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
}

.current-loc-btn {
    width: 100%; 
    background-color: var(--color-neutral-100);
    border: 1px solid var(--color-neutral-200);
    color: var(--color-text-600);
    padding: 0.4rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap; 
    display: flex;
    justify-content: center;
    align-items: center;
}

.current-loc-btn:hover {
    background-color: var(--color-neutral-200);
    color: var(--color-text-900);
}

.update-time-box { 
    background-color: var(--color-neutral-50); 
    border: 1px solid var(--color-neutral-200); 
    border-radius: 12px; 
    padding: 1.5rem 1.2rem; 
    display: flex; 
    flex-direction: column; 
    align-items: center; 
    justify-content: center; 
    flex-shrink: 0; 
    min-width: 80px;
    width: 100%; 
    box-sizing: border-box;
}

.placeholder-text { color: var(--color-text-400); font-size: 5rem; }
.temp-info { color: var(--color-text-600); margin: 0 0 0.5rem 0; }
.dust-info { color: var(--color-text-600); margin: 0 0 0.25rem 0; font-size: 0.9rem; }
.time-label { color: var(--color-text-600); font-size: 0.75rem; margin-bottom: 0.5rem; text-align: center; white-space: nowrap;}
.time-value { color: var(--color-text-600); font-size: 0.75rem; text-align: center; white-space: nowrap; }

.loading-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60vh; color: var(--color-text-600); font-weight: 600; font-size: 1.1rem; gap: 1.5rem; }
.spinner { width: 50px; height: 50px; border: 5px solid var(--color-neutral-200); border-top: 5px solid var(--color-amber-500); border-radius: 50%; animation: spin 1s cubic-bezier(0.55, 0.15, 0.45, 0.85) infinite; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

.ootd-section { display: flex; flex-direction: column; }
.ootd-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; width: 100%; }
.ootd-item { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 1.5rem 1rem; width: 100%; box-sizing: border-box; }
.item-icon-ph { font-size: 3rem; margin-bottom: 1.5rem; height: 40px; line-height: 1.4; text-align: center; }
.item-desc { font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--color-text-900); text-align: center; }
.item-name { color: var(--color-text-600); font-size: 0.85rem; text-align: center; }

.bottom-section { display: grid; grid-template-columns: 1fr 320px; gap: 2rem; width: 100%; box-sizing: border-box; }
.hourly-section { display: flex; flex-direction: column; min-width: 0; }
.hourly-flex { display: flex; gap: 1rem; width: 100%; }
.hourly-item { flex: 1; display: flex; flex-direction: column; align-items: center; padding: 1.5rem 0.5rem; box-sizing: border-box; min-width: 0; }
.hour-time { font-size: 0.9rem; color: var(--color-text-900); margin-bottom: 1.5rem; }
.hour-icon-ph { color: var(--color-text-400); font-size: 2.5rem; margin-bottom: 1.5rem; }
.hour-temp { font-weight: 600; font-size: 1.1rem; color: var(--color-text-900); }

.air-quality-card { padding: 2rem; box-sizing: border-box; }
.aqi-bars { display: flex; flex-direction: column; gap: 1.25rem; }
.aqi-row { display: flex; align-items: center; }
.aqi-label { width: 60px; font-size: 0.9rem; color: var(--color-text-600); }   
.progress-bg { flex: 1; height: 14px; background-color: var(--color-neutral-200); border-radius: 8px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 8px; transition: width 0.8s ease-in-out, background-color 0.8s ease; }
.progress-fill.excellent { background-color: #3B82F6; } 
.progress-fill.good { background-color: #10B981; }      
.progress-fill.warning { background-color: var(--color-amber-500); } 
.progress-fill.danger { background-color: var(--color-red-500); }  
.aqi-summary { margin-top: 1rem; }

/* --------------------------------------------------------------------------
   📱 모바일 화면 대응 (768px 이하)
-------------------------------------------------------------------------- */
@media screen and (max-width: 768px) {
    .top-section, 
    .bottom-section {
        grid-template-columns: 1fr;
    }

    .current-weather-card {
        flex-direction: column;
        text-align: center;
        gap: 1.5rem;
    }

    .weather-info-left {
        flex-direction: column;
        gap: 1rem;
    }

    .location-header {
        justify-content: center;
    }

    .weather-info-right {
        flex-direction: column; 
        width: 50%;
        justify-content: center;
        gap: 1rem;
    }

    .current-loc-btn, 
    .update-time-box {
        flex: 1; 
        min-width: 0;
        padding: 1rem; 
    }

    .ootd-grid {
        grid-template-columns: repeat(2, 1fr);
    }

    /* 시간별 날씨 모바일 스와이프 활성화 및 삐져나감 방지 */
    .hourly-flex {
        overflow-x: auto;
        scroll-snap-type: x mandatory;
        -webkit-overflow-scrolling: touch;
        padding-bottom: 0.5rem; 
    }

    .hourly-item {
        flex: 0 0 auto;
        min-width: 120px;
        scroll-snap-align: start;
    }
}
</style>