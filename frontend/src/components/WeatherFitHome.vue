<template>
    <main v-if="isLoading || isInitializing" class="main-content" aria-busy="true" aria-label="날씨 데이터를 불러오는 중">
        <div class="top-section">
            <div class="card skeleton-card sk-current">
                <div class="skeleton sk-circle"></div>
                <div class="sk-lines">
                    <div class="skeleton sk-line lg"></div>
                    <div class="skeleton sk-line md"></div>
                    <div class="skeleton sk-line sm"></div>
                </div>
            </div>
            <div class="sk-ootd">
                <div class="skeleton sk-line title"></div>
                <div class="ootd-grid">
                    <div v-for="n in 4" :key="n" class="card skeleton-card sk-ootd-item">
                        <div class="skeleton sk-circle sm"></div>
                        <div class="skeleton sk-line sm"></div>
                    </div>
                </div>
            </div>
        </div>
        <div class="bottom-section">
            <div class="sk-hourly">
                <div class="skeleton sk-line title"></div>
                <div class="hourly-flex">
                    <div v-for="n in 6" :key="n" class="card skeleton-card sk-hour-item">
                        <div class="skeleton sk-line xs"></div>
                        <div class="skeleton sk-circle sm"></div>
                        <div class="skeleton sk-line xs"></div>
                    </div>
                </div>
            </div>
            <div class="card skeleton-card sk-aqi">
                <div class="skeleton sk-line title"></div>
                <div class="skeleton sk-bar"></div>
                <div class="skeleton sk-bar"></div>
                <div class="skeleton sk-bar"></div>
            </div>
        </div>
    </main>

    <div v-else-if="!currentWeather" class="status-screen error">
        <p class="error-emoji" aria-hidden="true">🌫️</p>
        <p>날씨 정보를 불러오지 못했습니다.</p>
        <button class="retry-btn" @click="fetchCurrentLocationWeather">다시 시도</button>
    </div>

    <template v-else>
        <main class="main-content">
            <div class="top-section">
                <section class="card current-weather-card">

                    <div class="weather-info-left">
                        <div class="icon-wrapper">
                            <span class="weather-emoji" role="img" :aria-label="getWeatherLabel(currentWeather.rain, currentWeather.sky)">{{ getWeatherIcon(currentWeather.rain, currentWeather.sky) }}</span>
                        </div>
                        <div class="weather-details">
                            <div class="location-header">
                                <h2>{{ currentWeather.location }}</h2>
                            </div>
                            <p class="temp-info">
                                현재 기온 {{ currentWeather.temp }}°C
                                <span v-if="currentWeather.feelsLike != null" class="feels-like">체감 {{ currentWeather.feelsLike }}°C</span>
                            </p>
                            <p class="dust-info">미세먼지 {{ currentWeather.pm10Status }} ({{ currentWeather.pm10 }}µg/m³)</p>
                            <p class="dust-info">초미세먼지 {{ currentWeather.pm25Status }} ({{ currentWeather.pm25 }}µg/m³)</p>
                            <p v-if="currentWeather.uvLevel" class="dust-info">자외선 {{ currentWeather.uvLevel }} ({{ currentWeather.uv }})</p>
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
                    <h3 class="section-title">OOTD ({{ selectedHourlyWeather?.time }} 기준)</h3>

                    <p v-if="currentOutfit?.reason" class="ai-reason">
                        💡 {{ currentOutfit.reason }}
                    </p>

                    <div class="ootd-grid">
                        <template v-for="item in displayOotdItems" :key="item.id">
                            <!-- 마스크: 클릭/호버로 상세가 열리는 인터랙티브 카드 -->
                            <div
                                v-if="item.isMask"
                                class="card ootd-item mask-interactive"
                                :class="[{ expanded: maskExpanded }, getMaskBorderClass(selectedHourlyWeather?.pm25Status)]"
                                role="button"
                                tabindex="0"
                                :aria-expanded="maskExpanded"
                                aria-label="마스크 추천 상세 보기"
                                @click="maskExpanded = !maskExpanded"
                                @keydown.enter.prevent="maskExpanded = !maskExpanded"
                                @keydown.space.prevent="maskExpanded = !maskExpanded"
                            >
                                <div class="mask-front">
                                    <div class="item-icon-ph" role="img" aria-label="마스크 추천">😷</div>
                                    <div class="item-desc">마스크 추천</div>
                                    <div class="item-name">{{ item.name }}</div>
                                    <div class="mask-hint">자세히 보기 ▾</div>
                                </div>
                                <div class="mask-detail" :class="getMaskBorderClass(selectedHourlyWeather?.pm25Status)">
                                    <div class="mask-detail-header" :class="getMaskBgClass(selectedHourlyWeather?.pm25Status)">😷 마스크 추천</div>
                                    <div class="mask-detail-body">
                                        <p class="mask-grade">
                                            PM2.5 {{ selectedHourlyWeather?.pm25 }}㎍/㎥ →
                                            <strong :class="getDustTextClass(selectedHourlyWeather?.pm25Status)">{{ selectedHourlyWeather?.pm25Status }}</strong>
                                        </p>
                                        <p class="mask-rec">{{ item.name }}</p>
                                        <div class="badge-group">
                                            <span class="badge">KF-AD</span>
                                            <span class="badge">KF-80</span>
                                            <span class="badge">KF-94</span>
                                            <span class="badge">KF-99</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- 일반 OOTD 카드 -->
                            <div v-else class="card ootd-item">
                                <div class="item-icon-ph" role="img" :aria-label="item.description">{{ item.type }}</div>
                                <div class="item-desc">{{ item.description }}</div>
                                <div class="item-name">{{ item.name }}</div>
                            </div>
                        </template>
                    </div>
                </section>
            </div>

            <div class="bottom-section">
                <section class="hourly-section">
                    <h3 class="section-title">시간별 예보 (클릭하여 복장 확인)</h3>
                    <div class="hourly-flex">
                        <div
                            v-for="(hour, index) in hourlyData"
                            :key="hour.time"
                            class="card hourly-item"
                            :class="{ 'active-now': selectedHourIndex === index }"
                            role="button"
                            tabindex="0"
                            :aria-pressed="selectedHourIndex === index"
                            @click="selectHour(index)"
                            @keydown.enter.prevent="selectHour(index)"
                            @keydown.space.prevent="selectHour(index)"
                        >
                            <div class="hour-time">{{ hour.time }} {{ index === 0 ? '(지금)' : '' }}</div>
                            <div class="hour-icon-ph" role="img" :aria-label="getWeatherLabel(hour.rain, hour.sky)">{{ getWeatherIcon(hour.rain, hour.sky) }}</div>
                            <div class="hour-temp">{{ hour.temp }}°C</div>
                            <div v-if="hour.feelsLike != null" class="hour-feels">체감 {{ hour.feelsLike }}°C</div>
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
import { getWeatherIcon, getWeatherLabel, getTopIcon, getBottomIcon, getPackIcon } from '../utils/weather';

const route = useRoute();
const router = useRouter();
const isInitializing = ref(true);

// 시간별 선택 + 마스크 카드 인터랙션 상태
const selectedHourIndex = ref(0);
const maskExpanded = ref(false);

const selectHour = (index) => {
    selectedHourIndex.value = index;
};

const selectedHourlyWeather = computed(() => {
    return hourlyData.value.length > 0 ? hourlyData.value[selectedHourIndex.value] : null;
});

// 마스크 카드 색상 (PM2.5 단계별)
const getMaskBorderClass = (status) => {
    if (status === '좋음') return 'border-good';
    if (status === '보통' || status === '정보없음') return 'border-normal';
    return 'border-bad';
};
const getMaskBgClass = (status) => {
    if (status === '좋음') return 'bg-good';
    if (status === '보통' || status === '정보없음') return 'bg-normal';
    return 'bg-bad';
};
const getDustTextClass = (status) => {
    if (status === '좋음') return 'text-good';
    if (status === '보통' || status === '정보없음') return 'text-normal';
    return 'text-bad';
};

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

// 선택된 시간대 기준 OOTD (시간별 예보 클릭 시 함께 갱신)
const displayOotdItems = computed(() => {
    const weather = selectedHourlyWeather.value;
    const outfit = hourlyOutfitData.value?.length > 0 ? hourlyOutfitData.value[selectedHourIndex.value] : null;

    if (!weather || !outfit) return [];

    // 소지품: pack(우산 등) + acc(액세서리) 합쳐서 표시
    const acc = currentOutfit.value?.acc || [];
    const packParts = [];
    if (outfit.pack && outfit.pack !== '불필요') packParts.push(outfit.pack);
    packParts.push(...acc);
    const packName = packParts.length > 0 ? packParts.join(', ') : '없음';

    return [
        { id: 1, type: getTopIcon(outfit.top), name: outfit.top, description: '추천 상의' },
        { id: 2, type: getBottomIcon(outfit.bottom), name: outfit.bottom, description: '추천 하의' },
        { id: 3, type: getPackIcon(outfit.pack, weather.sky), name: packName, description: '추천 소지품' },
        { id: 4, isMask: true, name: outfit.mask === '마스크 선택' ? '자유' : outfit.mask, description: '마스크 추천' }
    ];
});
</script>

<style scoped>
.main-content {
    max-width: 1200px;
    width: 100%;
    margin: 3rem auto 2rem auto;
    padding-left: 1rem;
    padding-right: 1rem;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    gap: 2rem;
    overflow-x: hidden; /* 가로 스크롤 바 제거 */
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

.weather-emoji { font-size: 5rem; line-height: 1; }
.temp-info { color: var(--color-text-600); margin: 0 0 0.5rem 0; }
.feels-like { display: inline-block; margin-left: 0.5rem; padding: 0.1rem 0.5rem; background: var(--color-neutral-100); border-radius: 6px; font-size: 0.85rem; font-weight: 600; color: var(--color-amber-600); }
.dust-info { color: var(--color-text-600); margin: 0 0 0.25rem 0; font-size: 0.9rem; }
.time-label { color: var(--color-text-600); font-size: 0.75rem; margin-bottom: 0.5rem; text-align: center; white-space: nowrap;}
.time-value { color: var(--color-text-600); font-size: 0.75rem; text-align: center; white-space: nowrap; }

.loading-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 60vh; color: var(--color-text-600); font-weight: 600; font-size: 1.1rem; gap: 1.5rem; }

/* 에러 / 데이터 없음 상태 */
.status-screen.error { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 60vh; gap: 1rem; color: var(--color-text-600); font-weight: 600; font-size: 1.1rem; text-align: center; padding: 1rem; }
.status-screen.error .error-emoji { font-size: 3.5rem; margin: 0; }
.retry-btn { margin-top: 0.5rem; background-color: var(--color-amber-600); color: #fff; border: none; padding: 0.7rem 1.8rem; border-radius: 2rem; font-weight: 700; font-size: 1rem; cursor: pointer; transition: background-color 0.2s; min-height: 44px; }
.retry-btn:hover { background-color: var(--color-amber-500); }

/* --------------------------------------------------------------------------
   ✨ 스켈레톤 로딩 (스피너 대신 레이아웃 형태를 미리 보여줘 체감 대기 단축)
-------------------------------------------------------------------------- */
.skeleton {
    background: linear-gradient(90deg, var(--color-neutral-200) 25%, var(--color-neutral-100) 37%, var(--color-neutral-200) 63%);
    background-size: 400% 100%;
    animation: skeleton-shimmer 1.4s ease infinite;
    border-radius: 8px;
}
@keyframes skeleton-shimmer {
    0% { background-position: 100% 50%; }
    100% { background-position: 0 50%; }
}
@media (prefers-reduced-motion: reduce) {
    .skeleton { animation: none; }
}

.skeleton-card { padding: 1.5rem; }
.sk-current { display: flex; align-items: center; gap: 1.5rem; }
.sk-lines { flex: 1; display: flex; flex-direction: column; gap: 0.75rem; }
.sk-circle { width: 80px; height: 80px; border-radius: 50%; flex-shrink: 0; }
.sk-circle.sm { width: 48px; height: 48px; }
.sk-line { height: 14px; width: 100%; }
.sk-line.title { height: 22px; width: 180px; margin-bottom: 1rem; }
.sk-line.lg { height: 22px; width: 70%; }
.sk-line.md { width: 55%; }
.sk-line.sm { width: 40%; }
.sk-line.xs { height: 12px; width: 60%; }
.sk-ootd, .sk-hourly { display: flex; flex-direction: column; }
.sk-ootd-item { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 1.5rem 1rem; }
.sk-hour-item { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 1.5rem 0.5rem; flex: 1; min-width: 0; }
.sk-aqi { display: flex; flex-direction: column; gap: 1rem; }
.sk-bar { height: 14px; width: 100%; }
.spinner { width: 50px; height: 50px; border: 5px solid var(--color-neutral-200); border-top: 5px solid var(--color-amber-500); border-radius: 50%; animation: spin 1s cubic-bezier(0.55, 0.15, 0.45, 0.85) infinite; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

.ootd-section { display: flex; flex-direction: column; }
.ootd-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; width: 100%; }
.ootd-item { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 1.5rem 1rem; width: 100%; min-height: 175px; box-sizing: border-box; }
.item-icon-ph { font-size: 3rem; margin-bottom: 1.5rem; height: 40px; line-height: 1.4; text-align: center; }
.item-desc { font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem; color: var(--color-text-900); text-align: center; }
.item-name { color: var(--color-text-600); font-size: 0.85rem; text-align: center; }

/* 인터랙티브 마스크 카드 (호버/클릭 시 상세 노출) */
.mask-interactive { position: relative; cursor: pointer; overflow: hidden; border-width: 2px; transition: box-shadow 0.2s; }
.mask-interactive:focus-visible { outline: 2px solid var(--color-amber-500); outline-offset: 2px; }
.mask-interactive.border-good { border-color: #10B981; }
.mask-interactive.border-normal { border-color: var(--color-amber-500); }
.mask-interactive.border-bad { border-color: var(--color-red-500); }
.mask-front { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; }
.mask-hint { margin-top: 0.5rem; font-size: 0.72rem; font-weight: 700; color: var(--color-text-400); }

.mask-detail {
    position: absolute; inset: 0; background: #fff; border-radius: inherit;
    display: flex; flex-direction: column; text-align: left;
    opacity: 0; visibility: hidden; transform: translateY(8px); overflow-y: auto;
    transition: opacity 0.2s ease, transform 0.2s ease, visibility 0.2s;
}
.mask-interactive:hover .mask-detail,
.mask-interactive.expanded .mask-detail { opacity: 1; visibility: visible; transform: translateY(0); }
.mask-detail-header { color: #fff; font-weight: 700; padding: 0.6rem 0.8rem; font-size: 0.9rem; }
.mask-detail-header.bg-good { background: #10B981; }
.mask-detail-header.bg-normal { background: var(--color-amber-500); }
.mask-detail-header.bg-bad { background: var(--color-red-500); }
.mask-detail-body { padding: 0.8rem; display: flex; flex-direction: column; gap: 0.4rem; }
.mask-grade { margin: 0; font-size: 0.8rem; color: var(--color-text-600); }
.mask-rec { margin: 0; font-weight: 700; font-size: 0.95rem; color: var(--color-text-900); }
.text-good { color: #10B981; }
.text-normal { color: var(--color-amber-500); }
.text-bad { color: var(--color-red-500); }
.badge-group { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.2rem; }
.badge { background: var(--color-neutral-100); color: var(--color-text-600); font-weight: 700; font-size: 0.65rem; padding: 0.25rem 0.5rem; border-radius: 6px; }

.bottom-section { display: grid; grid-template-columns: 1fr 320px; gap: 2rem; width: 100%; box-sizing: border-box; }
.hourly-section { display: flex; flex-direction: column; min-width: 0; }
.hourly-flex { display: flex; gap: 1rem; width: 100%; }
.hourly-item { flex: 1; display: flex; flex-direction: column; align-items: center; padding: 1.5rem 0.5rem; box-sizing: border-box; min-width: 0; }
.hour-time { font-size: 0.9rem; color: var(--color-text-900); margin-bottom: 1.5rem; }
.hour-icon-ph { color: var(--color-text-400); font-size: 2.5rem; margin-bottom: 1.5rem; }
.hour-temp { font-weight: 600; font-size: 1.1rem; color: var(--color-text-900); }
.hour-feels { font-size: 0.75rem; color: var(--color-amber-600); margin-top: 0.35rem; }

/* 클릭 가능한 시간별 카드 */
.hourly-item { cursor: pointer; transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s; }
.hourly-item:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,0.06); }
.hourly-item:focus-visible { outline: 2px solid var(--color-amber-500); outline-offset: 2px; }
.hourly-item.active-now { background-color: #FFFBEB; border-color: var(--color-amber-500); }
.hourly-item.active-now .hour-time, .hourly-item.active-now .hour-temp { color: var(--color-amber-600); font-weight: 700; }

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