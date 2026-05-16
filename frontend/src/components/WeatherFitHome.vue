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
                        <div v-for="(hour, index) in hourlyData" :key="index" class="card hourly-item">
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

        <section class="guide-container">
            <div class="guide-banner">
                <div class="banner-content">
                    <span class="guide-badge">🧥 복장 가이드라인</span>
                    <h1 class="banner-title">날씨별 범용 복장 가이드</h1>
                    <p class="banner-desc">
                        기온, 체감온도, 습도, 바람, 미세먼지, 강수확률을 종합 분석한 복장 기준입니다.<br>
                        외출 전 현재 날씨와 비교하여 쾌적한 옷차림을 준비하세요.
                    </p>
                    <div class="tag-group">
                        <span class="tag">🌡️ 기온</span>
                        <span class="tag">💧 습도</span>
                        <span class="tag">🌬️ 바람</span>
                        <span class="tag">😷 미세먼지</span>
                        <span class="tag">☔ 강수</span>
                    </div>
                </div>
                <div class="banner-icon-wrapper">
                    <div class="icon-circle">
                        <span class="main-icon">🧥</span>
                    </div>
                </div>
            </div>

            <div class="guide-content-grid">
                <article class="temp-guide-section">
                    <div class="section-header">
                        <h2>🌡️ 기온별 기준 복장</h2>
                    </div>
                    <div class="temp-table">
                        <div class="table-head">
                            <div class="col-state">상태</div>
                            <div class="col-temp">기온 구간</div>
                            <div class="col-clothes">추천 옷차림 및 아이템</div>
                        </div>
                        <div class="table-row" v-for="guide in tempGuides" :key="guide.id">
                            <div class="col-state">
                                <span class="state-circle" :style="{ backgroundColor: guide.color }">{{ guide.label }}</span>
                            </div>
                            <div class="col-temp">
                                <h3 class="temp-range">{{ guide.range }}</h3>
                                <span class="temp-sub">{{ guide.sub }}</span>
                            </div>
                            <div class="col-clothes">
                                <div class="clothes-tags">
                                    <span class="cloth-tag" v-for="cloth in guide.clothes" :key="cloth">{{ cloth }}</span>
                                </div>
                                <p class="clothes-desc">{{ guide.desc }}</p>
                            </div>
                        </div>
                    </div>
                </article>

                <aside class="condition-guide-section">
                    <div class="section-header">
                        <h2>💡 조건별 추가 가이드</h2>
                    </div>
                    <div class="condition-cards">
                        <div class="cond-card" v-for="cond in conditionGuides" :key="cond.title">
                            <h3 class="cond-title">{{ cond.icon }} {{ cond.title }}</h3>
                            <ul class="cond-list">
                                <li v-for="item in cond.items" :key="item.text">
                                    <span class="dot" :class="item.dotColor"></span>
                                    <span class="cond-text" v-html="item.text"></span>
                                </li>
                            </ul>
                        </div>
                    </div>
                </aside>
            </div>
        </section>
    </template>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { searchHistory } from '../stores/usehistory';
import { currentWeather, hourlyData, hourlyOutfitData, fetchWeatherData, isLoading } from '../stores/useWeather';

// ------------------------------------------------------------------------
// 1. 상태 변수 및 초기화 로직
// ------------------------------------------------------------------------
const isInitializing = ref(true);

onMounted(() => {
    fetchCurrentLocationWeather();
});

// 에러 발생 및 미지원 지역일 때 실행되는 폴백(대체) 함수
const fallbackToHistory = async () => {
    if (searchHistory.value.length > 0) {
        await fetchWeatherData(searchHistory.value[0]);
    } else {
        await fetchWeatherData('인천광역시 남동구 구월3동'); 
    }
    isInitializing.value = false;
};

// ------------------------------------------------------------------------
// 2. 카카오맵 및 위치 기반 로직 리팩터링
// ------------------------------------------------------------------------

// 카카오맵 스크립트가 완전히 로드되었는지 확인 후 실행하는 헬퍼 함수
const runKakaoMapGeocode = (lat, lon, retryCount = 0) => {
    if (window.kakao && window.kakao.maps && window.kakao.maps.services) {
        window.kakao.maps.load(() => {
            const geocoder = new window.kakao.maps.services.Geocoder();
            geocoder.coord2RegionCode(lon, lat, async (result, status) => {
                if (status === window.kakao.maps.services.Status.OK) {
                    const regionInfo = result.find(r => r.region_type === 'H') || result[0];
                    const currentRegionName = `${regionInfo.region_1depth_name} ${regionInfo.region_2depth_name} ${regionInfo.region_3depth_name}`.trim();
                    
                    console.log("📍 [현재 좌표 기반 행정동명]:", currentRegionName);
                    
                    await fetchWeatherData(currentRegionName);
                    
                    if (!currentWeather.value) {
                        console.warn("지원하지 않는 지역입니다. 이전 기록으로 돌아갑니다.");
                        fallbackToHistory();
                    } else {
                        isInitializing.value = false;
                    }
                } else {
                    console.error("행정동 변환 실패 상태:", status);
                    fallbackToHistory();
                }
            });
        });
    } else {
        // 스크립트 로드 지연 시 최대 10번(5초) 재시도
        if (retryCount < 10) {
            console.warn(`카카오 API 로딩 대기 중... (${retryCount + 1}/10)`);
            setTimeout(() => runKakaoMapGeocode(lat, lon, retryCount + 1), 500);
        } else {
            console.error("카카오맵 API 로드 최종 실패");
            fallbackToHistory();
        }
    }
};

// 위치 권한 요청 및 좌표 획득 메인 함수
const fetchCurrentLocationWeather = () => {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                runKakaoMapGeocode(lat, lon); // 분리한 카카오 로직 실행
            },
            (error) => {
                console.warn("위치 권한을 거부했거나 시간 초과 발생:", error);
                fallbackToHistory();
            },
            // 권한 대기 시간을 넉넉히 10초로 늘리고, 캐시된 위치는 무시하도록 설정
            { timeout: 10000, enableHighAccuracy: false, maximumAge: 0 } 
        );
    } else {
        console.warn("이 브라우저에서는 위치 기반 서비스를 지원하지 않습니다.");
        fallbackToHistory();
    }
};

// ------------------------------------------------------------------------
// 3. UI 및 데이터 매핑 로직
// ------------------------------------------------------------------------

// 대기질 현황 계산 함수
const getAqiStyle = (type, value, status) => {
    let max = 100, good = 0, warning = 0, danger = 0;

    if (type === 'PM2.5') { max = 76; }
    else if (type === 'PM10') { max = 151; }
    else if (type === 'O3') { 
        max = 0.15; good = 0.031; warning = 0.091; danger = 0.150; 
    }

    const percentage = Math.min((value / max) * 100, 100);
    let colorClass = 'excellent'; 

    if(status == null) {
        if (value >= danger) colorClass = 'danger'; 
        else if (value >= warning) colorClass = 'warning'; 
        else if (value >= good) colorClass = 'good'; 
    } else {
        if (status == 4) colorClass = 'danger';
        else if (status == 3) colorClass = 'warning'; 
        else if (status == 2) colorClass = 'good'; 
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

// OOTD 추천 리스트 동적 생성
const displayOotdItems = computed(() => {
    const weather = hourlyData.value[0] || null;
    const outfit = hourlyOutfitData.value?.length > 0 ? hourlyOutfitData.value[0] : null;
    const items = [];

    if (!weather || !outfit) return items;

    // 상의
    let topIcon = '👕';
    if (outfit.top.includes('긴팔')) topIcon = '👔';
    else if (outfit.top.includes('재킷') || outfit.top.includes('가죽')) topIcon = '🧥';
    else if (outfit.top.includes('패딩')) topIcon = '🧣';
    items.push({ id: 1, type: topIcon, name: outfit.top, description: '추천 상의' });

    // 하의
    let bottomIcon = outfit.bottom.includes('반바지') ? '🩳' : '👖';
    items.push({ id: 2, type: bottomIcon, name: outfit.bottom, description: '추천 하의' });

    // 소지품
    let packIcon = '✋';
    if (outfit.pack.includes('우산')) packIcon = '☔';
    else if (weather.sky?.includes('눈')) packIcon = '🌨️';
    items.push({ id: 3, type: packIcon, name: outfit.pack === '불필요' ? '없음' : outfit.pack, description: '추천 소지품' });

    // 마스크
    items.push({ id: 4, type: '😷', name: outfit.mask === '마스트 선택' ? '자유' : outfit.mask, description: '마스크 추천' });

    return items;
});

// 날씨 아이콘 계산
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

// ------------------------------------------------------------------------
// 4. 정적 가이드 데이터
// ------------------------------------------------------------------------
const tempGuides = ref([
    { id: 1, label: 'H', color: 'var(--color-red-500)', range: '28°C 이상', sub: '무더위', clothes: ['민소매', '반팔', '반바지', '짧은 치마', '린넨 소재'], desc: '자외선 차단제 필수, 통기성 좋은 옷 추천' },
    { id: 2, label: 'W', color: 'var(--color-amber-600)', range: '23 ~ 27°C', sub: '따뜻함', clothes: ['반팔', '얇은 셔츠', '반바지', '면바지'], desc: '에어컨 실내용 얇은 겉옷 지참 추천' },
    { id: 3, label: 'M', color: 'var(--color-amber-500)', range: '17 ~ 22°C', sub: '선선함', clothes: ['긴팔 티셔츠', '가디건', '후드티', '맨투맨', '청바지'], desc: '일교차 주의, 입고 벗기 편한 겉옷 준비' },
    { id: 4, label: 'C', color: '#06B6D4', range: '12 ~ 16°C', sub: '쌀쌀함', clothes: ['가디건', '야상', '재킷', '니트', '두꺼운 긴바지'], desc: '바람이 불면 체감온도가 급격히 떨어짐' },
    { id: 5, label: 'F', color: '#3B82F6', range: '5 ~ 11°C', sub: '추움', clothes: ['코트', '가죽재킷', '두꺼운 니트', '스카프', '기모 바지'], desc: '목도리나 가벼운 장갑 착용 권장' },
    { id: 6, label: 'S', color: '#8B5CF6', range: '4°C 이하', sub: '한파', clothes: ['패딩', '두꺼운 롱코트', '방한복', '기모 이너', '목도리', '장갑'], desc: '방한 용품 필수, 동상 및 빙판길 주의' }
]);

const conditionGuides = ref([
    { title: '바람 (풍속)', icon: '🌬️', items: [{ dotColor: 'dot-green', text: '<strong>약풍</strong> — 복장 변화 없음' }, { dotColor: 'dot-yellow', text: '<strong>보통</strong> — 한 단계 두껍게' }, { dotColor: 'dot-red', text: '<strong>강풍</strong> — 방풍 재킷 필수' }] },
    { title: '체감 습도', icon: '💧', items: [{ dotColor: 'dot-green', text: '<strong>30% ↓</strong> — 보습·정전기 주의' }, { dotColor: 'dot-green', text: '<strong>40~70%</strong> — 가장 쾌적함' }, { dotColor: 'dot-yellow', text: '<strong>80% ↑</strong> — 통기성 소재 추천' }] },
    { title: '미세먼지', icon: '😷', items: [{ dotColor: 'dot-green', text: '<strong>좋음</strong> — 마스크 선택' }, { dotColor: 'dot-yellow', text: '<strong>보통</strong> — KF80 권장' }, { dotColor: 'dot-red', text: '<strong>나쁨 ↑</strong> — KF94 필수 착용' }] },
    { title: '강수 확률', icon: '☔', items: [{ dotColor: 'dot-green', text: '<strong>30% ↓</strong> — 우산 불필요' }, { dotColor: 'dot-yellow', text: '<strong>30~60%</strong> — 접이식 우산 지참' }, { dotColor: 'dot-red', text: '<strong>60% ↑</strong> — 큰 우산, 레인부츠' }] }
]);
</script>

<style scoped>
/* --------------------------------------------------------------------------
   전체 공통 레이아웃 (정렬 강제 동기화)
-------------------------------------------------------------------------- */
.main-content, 
.guide-container {
    max-width: 1200px !important;
    width: 100% !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    box-sizing: border-box !important;
}

.main-content {
    margin-top: 3rem !important;
    margin-bottom: 2rem !important;
    display: flex;
    flex-direction: column;
    gap: 2rem;
}

.guide-container {
    margin-top: 0 !important;
    margin-bottom: 4rem !important;
    font-family: 'Pretendard', sans-serif; 
}

.card { 
    background-color: #FFFFFF; 
    border-radius: 12px; 
    border: 1px solid var(--color-neutral-200); 
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); 
}

.section-title { 
    font-size: 1.25rem; 
    font-weight: 700; 
    margin: 0 0 1rem 0; 
    color: var(--color-text-900); 
}

/* --------------------------------------------------------------------------
   로딩 스피너
-------------------------------------------------------------------------- */
.loading-screen {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 60vh;
    color: var(--color-text-600);
    font-weight: 600;
    font-size: 1.1rem;
    gap: 1.5rem;
}

.spinner {
    width: 50px;
    height: 50px;
    border: 5px solid var(--color-neutral-200);
    border-top: 5px solid var(--color-amber-500);
    border-radius: 50%;
    animation: spin 1s cubic-bezier(0.55, 0.15, 0.45, 0.85) infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* --------------------------------------------------------------------------
   상단 날씨 영역 (Top Section)
-------------------------------------------------------------------------- */
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
}

.weather-info-left { 
    display: flex; 
    align-items: center; 
    gap: 1.5rem; 
}

.placeholder-text { 
    color: var(--color-text-400); 
    font-size: 5rem; 
}

.weather-details h2 { 
    font-size: 1.35rem; 
    margin: 0 0 0.75rem 0; 
    color: var(--color-text-900); 
    white-space: pre-wrap; 
}   

.temp-info { 
    color: var(--color-text-600); 
    margin: 0 0 0.5rem 0; 
}

.dust-info { 
    color: var(--color-text-600); 
    margin: 0 0 0.25rem 0; 
    font-size: 0.9rem; 
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
}

.time-label { 
    color: var(--color-text-600); 
    font-size: 0.75rem; 
    margin-bottom: 0.5rem; 
    text-align: center; 
    white-space: nowrap;
}

.time-value { 
    color: var(--color-text-600); 
    font-size: 0.75rem; 
    text-align: center; 
    white-space: nowrap; 
}

/* --------------------------------------------------------------------------
   OOTD 영역
-------------------------------------------------------------------------- */
.ootd-section { display: flex; flex-direction: column; }
.ootd-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; flex: 1; }
.ootd-item { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 1.5rem 1rem; }

.item-icon-ph { 
    font-size: 3rem; 
    margin-bottom: 1.5rem; 
    height: 40px; 
    line-height: 1.4; 
    text-align: center; 
}

.item-desc { 
    font-weight: 600; 
    font-size: 1.1rem; 
    margin-bottom: 0.5rem; 
    color: var(--color-text-900); 
    text-align: center;
}

.item-name { 
    color: var(--color-text-600); 
    font-size: 0.85rem; 
    text-align: center;
}

/* --------------------------------------------------------------------------
   하단 영역 (Bottom Section)
-------------------------------------------------------------------------- */
.bottom-section { 
    display: grid; 
    grid-template-columns: 1fr 320px; 
    gap: 2rem; 
}

.hourly-section { display: flex; flex-direction: column; }
.hourly-flex { display: flex; gap: 1rem; }

.hourly-item { 
    flex: 1; 
    display: flex; 
    flex-direction: column; 
    align-items: center; 
    padding: 1.5rem 0.5rem; 
}

.hour-time { font-size: 0.9rem; color: var(--color-text-900); margin-bottom: 1.5rem; }
.hour-icon-ph { color: var(--color-text-400); font-size: 2.5rem; margin-bottom: 1.5rem; }
.hour-temp { font-weight: 600; font-size: 1.1rem; color: var(--color-text-900); }

/* 대기질 현황 */
.air-quality-card { padding: 2rem; }
.aqi-bars { display: flex; flex-direction: column; gap: 1.25rem; }
.aqi-row { display: flex; align-items: center; }
.aqi-label { width: 60px; font-size: 0.9rem; color: var(--color-text-600); }   

.progress-bg { 
    flex: 1; 
    height: 14px; 
    background-color: var(--color-neutral-200); 
    border-radius: 8px; 
    overflow: hidden; 
}

.progress-fill { 
    height: 100%; 
    border-radius: 8px; 
    transition: width 0.8s ease-in-out, background-color 0.8s ease; 
}

.progress-fill.excellent { background-color: #3B82F6; } 
.progress-fill.good { background-color: #10B981; }      
.progress-fill.warning { background-color: var(--color-amber-500); } 
.progress-fill.danger { background-color: var(--color-red-500); }  

.aqi-summary { margin-top: 1rem; }

/* --------------------------------------------------------------------------
   가이드 섹션
-------------------------------------------------------------------------- */
.guide-banner { 
    background-color: var(--color-navy-800); 
    border-radius: 20px; 
    padding: 3rem; 
    display: flex; 
    justify-content: space-between; 
    align-items: center; 
    margin-top: 0 !important; 
    margin-bottom: 2rem !important;
    color: #FFFFFF; 
    box-shadow: 0 10px 25px rgba(0,0,0,0.1); 
    box-sizing: border-box !important;
}

.banner-content { flex: 1; }

.guide-badge { 
    background: rgba(255, 255, 255, 0.1); 
    border: 1px solid rgba(255, 255, 255, 0.2); 
    color: var(--color-amber-500); 
    padding: 0.4rem 0.8rem; 
    border-radius: 8px; 
    font-size: 0.85rem; 
    font-weight: 700; 
}

.banner-title { font-size: 2.2rem; font-weight: 800; margin: 1.5rem 0 1rem 0; }
.banner-desc { color: var(--color-text-400); font-size: 1rem; line-height: 1.6; margin-bottom: 1.5rem; }

.tag-group { display: flex; gap: 0.8rem; flex-wrap: wrap; }
.tag { 
    background: rgba(255, 255, 255, 0.08); 
    padding: 0.5rem 1rem; 
    border-radius: 20px; 
    font-size: 0.9rem; 
    color: var(--color-neutral-100); 
}

.banner-icon-wrapper { margin-left: 2rem; }
.icon-circle { 
    width: 160px; 
    height: 160px; 
    background: rgba(255, 255, 255, 0.05); 
    border-radius: 50%; 
    display: flex; 
    justify-content: center; 
    align-items: center; 
    font-size: 5rem; 
}

.guide-content-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 2rem; }
.section-header h2 { font-size: 1.4rem; font-weight: 800; color: var(--color-text-900); margin-bottom: 1.5rem; }

.temp-guide-section { 
    background: #FFFFFF; 
    border: 1px solid var(--color-neutral-200); 
    border-radius: 16px; 
    padding: 2rem; 
    box-shadow: 0 4px 12px rgba(0,0,0,0.02); 
}

.temp-table { display: flex; flex-direction: column; }
.table-head { 
    display: flex; 
    padding-bottom: 1rem; 
    border-bottom: 1px solid var(--color-neutral-200); 
    color: var(--color-text-600); 
    font-size: 0.9rem; 
    font-weight: 600; 
}   
.table-row { 
    display: flex; 
    padding: 1.5rem 0; 
    border-bottom: 1px solid var(--color-neutral-100); 
    align-items: center; 
}
.table-row:last-child { border-bottom: none; padding-bottom: 0; }

.col-state { width: 80px; display: flex; justify-content: center; }
.col-temp { width: 140px; }
.col-clothes { flex: 1; }

.state-circle { 
    width: 44px; 
    height: 44px; 
    border-radius: 50%; 
    display: flex; 
    justify-content: center; 
    align-items: center; 
    color: #FFFFFF; 
    font-weight: 800; 
    font-size: 1.2rem; 
}

.temp-range { font-size: 1.15rem; font-weight: 700; color: var(--color-text-900); margin: 0 0 0.3rem 0; }
.temp-sub { font-size: 0.85rem; color: var(--color-text-400); }

.clothes-tags { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.8rem; }
.cloth-tag { 
    background: var(--color-neutral-50); 
    border: 1px solid var(--color-neutral-200); 
    color: var(--color-text-600); 
    padding: 0.4rem 0.8rem; 
    border-radius: 20px; 
    font-size: 0.85rem; 
    font-weight: 600; 
}

.clothes-desc { font-size: 0.85rem; color: var(--color-text-400); margin: 0; }

.condition-guide-section { display: flex; flex-direction: column; }
.condition-cards { display: flex; flex-direction: column; gap: 1.2rem; }

.cond-card { 
    background: #FFFFFF; 
    border: 1px solid var(--color-neutral-200); 
    border-radius: 16px; 
    padding: 1.5rem; 
    box-shadow: 0 4px 12px rgba(0,0,0,0.02); 
}

.cond-title { 
    font-size: 1.1rem; 
    font-weight: 700; 
    color: var(--color-navy-800); 
    margin: 0 0 1.2rem 0; 
    display: flex; 
    align-items: center; 
    gap: 0.5rem; 
}

.cond-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.8rem; }
.cond-list li { display: flex; align-items: center; gap: 0.8rem; font-size: 0.95rem; color: var(--color-text-600); }

.dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-green { background-color: #10B981; } 
.dot-yellow { background-color: var(--color-amber-500); } 
.dot-red { background-color: var(--color-red-500); }
</style>