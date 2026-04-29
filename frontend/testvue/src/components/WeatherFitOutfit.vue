<template>
    <main class="outfit-main-content">
        
        <div v-if="isLoading" class="status-screen">
            <h2>날씨 데이터를 분석하고 있습니다... ⏳</h2>
            <p>잠시만 기다려주세요.</p>
        </div>

        <div v-else-if="errorMessage" class="status-screen error">
            <p>{{ errorMessage }}</p>
        </div>

        <div v-else-if="currentWeather">
            <div class="weather-summary-bar">
                <div class="summary-inner">
                    <span class="location">📍 {{ currentWeather.location }}</span>
                    <div class="divider"></div>
                    <span class="info-item">🌡️ 기온 <strong>{{ currentWeather.temp }}°C</strong></span>
                    <span class="info-item">💧 미세먼지 <strong>{{ currentWeather.pm10Status }}</strong></span>
                    <span class="info-item">💨 초미세먼지 <strong>{{ currentWeather.pm25Status }}</strong></span>
                </div>
            </div>

            <div class="content-wrapper">
                <section class="ootd-section">
                    <h2 class="section-title">OOTD ({{ selectedHourlyWeather?.time }} 기준)</h2>
                    
                    <div class="ootd-grid">
                        <div 
                            v-for="item in displayOotdItems" 
                            :key="item.id" 
                            class="ootd-card"
                            :class="{ 'mask-card': item.type === '마스크' }"
                        >
                            <template v-if="item.type === '마스크'">
                                <div class="mask-header">
                                    😷 마스크 추천
                                </div>
                                <div class="mask-body">
                                    <p class="dust-info">
                                        PM2.5 : {{ selectedHourlyWeather?.pm25 }}μg/m³ → 
                                        <strong class="danger" :class="getDustTextClass(selectedHourlyWeather?.pm25Status)">
                                            {{ selectedHourlyWeather?.pm25Status }} 단계
                                        </strong>
                                    </p>
                                    <p class="recommend-text">
                                        <strong>{{ item.name }}</strong>
                                    </p>
                                    <p class="desc-text">{{ item.description }}</p>
                                    <div class="badge-group">
                                        <span class="badge">KF-AD</span>
                                        <span class="badge">KF-80</span>
                                        <span class="badge">KF-94</span>
                                        <span class="badge">KF-99</span>
                                    </div>
                                </div>
                            </template>

                            <template v-else>
                                <div class="icon-placeholder">
                                    {{ item.icon }}
                                </div>
                                <p class="item-desc">{{ item.description }}</p>
                                <h3 class="item-name">{{ item.name }}</h3>
                            </template>
                        </div>
                    </div>
                </section>

                <section class="hourly-section">
                    <h2 class="section-title">시간별 예보 (클릭하여 복장 확인)</h2>
                    
                    <div class="hourly-grid">
                        <div 
                            v-for="(data, index) in hourlyData" 
                            :key="index" 
                            class="hourly-card"
                            :class="{ 'active-now': selectedHourIndex === index }"
                            @click="selectHour(index)"
                        >
                            <div class="time">{{ data.time }} {{ index === 0 ? '(지금)' : '' }}</div>
                            <div class="icon-placeholder small">{{ getWeatherIcon(data.pop, data.popform) }}</div>
                            <div class="temp">{{ data.temp }}°C</div>
                        </div>
                    </div>
                </section>
            </div>
        </div>

    </main>
</template>

<script setup>
    import { ref, computed, onMounted } from 'vue';
    import { useRoute } from 'vue-router'; 
    import { searchHistory } from '../stores/usehistory'; 
    import { currentWeather, hourlyData, hourlyOutfitData, isLoading, errorMessage, fetchWeatherData } from '../stores/useWeather';

    const route = useRoute();

    const lastSearchedLocation = computed(() => {
        if (searchHistory.value.length > 0) {
            return searchHistory.value[0]; 
        } else {
            return '지역을 검색해주세요'; 
        }
    });

    const regionName = route.query.region || lastSearchedLocation.value;

    onMounted(() => {
        if (regionName !== '지역을 검색해주세요') {
            fetchWeatherData(regionName);
        }
    });

    const selectedHourIndex = ref(0);

    const selectHour = (index) => {
        selectedHourIndex.value = index;
    };

    const selectedHourlyWeather = computed(() => {
        return hourlyData.value.length > 0 ? hourlyData.value[selectedHourIndex.value] : null;
    });

    const displayOotdItems = computed(() => {
        const weather = selectedHourlyWeather.value;
        const outfit = hourlyOutfitData.value.length > 0 ? hourlyOutfitData.value[selectedHourIndex.value] : null;
        const items = [];

        if (!weather || !outfit) return items;

        // 상의 처리
        items.push({ 
            id: 1, 
            type: '일반', 
            icon: '👕', 
            name: outfit.top, 
            description: '추천 상의'
        });

        // 하의 처리
        items.push({ 
            id: 2, 
            type: '일반', 
            icon: '👖', 
            name: outfit.bottom, 
            description: '추천 하의' 
        });

        // 챙길 물건(pack) 처리: 문자열에 우산이 포함되면 우산 아이콘, 아니면 상황에 맞게 렌더링
        let packIcon = '✋';
        if (outfit.pack.includes('우산')) packIcon = '☔';
        else if (weather.popform === '맑음' && outfit.pack === '불필요') packIcon = '✋';
        else if (weather.popform === '눈') packIcon = '🌨️';

        items.push({ 
            id: 3, 
            type: '일반', 
            icon: packIcon, 
            name: outfit.pack === '불필요' ? '없음' : outfit.pack, 
            description: '추천 소지품'
        });

        // 마스크 처리
        items.push({ 
            id: 4, 
            type: '마스크', 
            name: outfit.mask, // 백엔드 값: "마스크 선택" 또는 "마스크 필수"
            description: '식약처 인증 마스크' 
        });

        return items;
    });

    const getDustTextClass = (status) => {
        if (status === '좋음') return 'text-good';
        if (status === '보통') return 'text-normal';
        return 'text-bad'; 
    };

    const getWeatherIcon = (pop, popform) => {
        switch (popform) {
            case '맑음': return '☀️';
            case '비': 
                if(pop > 30) return '🌧️';
                return '🌤️';
            case '눈': 
                if(pop > 30) return '🌨️';
                return '🌥️';
            case '흐림': return '☁️';
            default: return '🌤️'; 
        }
    };
</script>

<style scoped>
    /* 추가된 스타일: 로딩 및 에러 상태 화면 */
    .status-screen {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 60vh;
        color: var(--color-text-900);
        text-align: center;
    }
    
    .status-screen.error {
        color: var(--color-red-500);
    }
    
    .status-screen h2 {
        font-size: 1.8rem;
        margin-bottom: 1rem;
    }
    
    .status-screen p {
        font-size: 1.1rem;
        color: var(--color-text-600);
    }

    /* 전체 레이아웃 */
    .outfit-main-content {
        background-color: var(--color-neutral-50);
        min-height: calc(100vh - 60px); 
        padding-bottom: 4rem;
    }

    /* 상단 날씨 요약 바 */
    .weather-summary-bar {
        background-color: var(--color-navy-800);
        color: var(--color-neutral-50);
        padding: 0.8rem 0;
        font-size: 0.95rem;
    }

    .summary-inner {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .location { font-weight: 700; }
    .divider { width: 1px; height: 14px; background-color: var(--color-text-600); }
    .info-item { color: var(--color-neutral-200); }
    .info-item strong { color: #FFFFFF; font-weight: 600; }

    /* 메인 컨텐츠 래퍼 */
    .content-wrapper { max-width: 1200px; margin: 0 auto; padding: 2rem 1rem; }
    .section-title { font-size: 1.4rem; font-weight: 800; color: var(--color-text-900); margin-bottom: 1.5rem; }

    /* OOTD 그리드 */
    .ootd-section { margin-bottom: 3rem; }
    .ootd-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; }

    /* 공통 카드 스타일 */
    .ootd-card {
        background: #FFFFFF;
        border: 1px solid var(--color-neutral-200);
        border-radius: 12px;
        padding: 2rem 1rem;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }

    .icon-placeholder {
        width: 80px;
        height: 80px;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3.5rem;
        font-weight: 600;
        color: var(--color-text-600);
    }

    .item-desc { font-size: 1.1rem; font-weight: 700; color: var(--color-text-900); margin: 0 0 0.5rem 0; }
    .item-name { font-size: 0.9rem; color: var(--color-text-600); margin: 0; }

    /* 마스크 전용 카드 스타일 */
    .mask-card {
        padding: 0;
        border: 2px solid var(--color-red-500);
        overflow: hidden;
        text-align: left;
        align-items: stretch;
        justify-content: flex-start;
    }

    .mask-header { background-color: var(--color-red-500); color: white; font-weight: 700; padding: 0.8rem 1rem; font-size: 1.05rem; }
    .mask-body { padding: 1.2rem 1rem; background: #FFFFFF; }
    .mask-body p { margin: 0 0 0.5rem 0; font-size: 0.9rem; color: var(--color-text-600); }

    /* 미세먼지 색상 */
    .text-good { color: #10B981; }
    .text-normal { color: var(--color-amber-500); }
    .text-bad { color: var(--color-text-900); }

    .mask-body .recommend-text { font-weight: 700; color: var(--color-text-900); margin-top: 0.8rem; }
    .mask-body .desc-text { font-size: 0.85rem; color: var(--color-text-400); margin-bottom: 1rem; }

    .badge-group { display: flex; gap: 0.5rem; }
    .badge { background: var(--color-neutral-100); color: var(--color-text-600); font-weight: 700; font-size: 0.7rem; padding: 0.3rem 0.6rem; border-radius: 6px; }

    /* 시간별 예보 그리드 */
    .hourly-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 1rem; }

    .hourly-card {
        background: #FFFFFF;
        border: 1px solid var(--color-neutral-200);
        border-radius: 12px;
        padding: 1.5rem 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
    }

    .hourly-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }

    .hourly-card .time { font-size: 0.95rem; color: var(--color-text-600); margin-bottom: 1rem; }
    
    .hourly-card .icon-placeholder.small { 
        width: 60px; 
        height: 60px; 
        margin: 0 auto 1rem auto; 
        font-size: 2.5rem; 
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .hourly-card .temp { font-size: 1.2rem; font-weight: 700; color: var(--color-text-900); }

    .hourly-card.active-now {
        background-color: #FFFBEB; 
        border: 1px solid var(--color-amber-500);
    }

    .hourly-card.active-now .time,
    .hourly-card.active-now .temp {
        color: var(--color-amber-600);
        font-weight: 700;
    }
</style>