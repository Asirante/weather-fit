<template>
    <div v-if="isLoading" class="loading-screen">
        <div class="spinner"></div>
        <p>날씨 데이터를 분석하고 있습니다...</p>
    </div>

    <div v-else-if="errorMessage" class="status-screen error">
        <p>{{ errorMessage }}</p>
    </div>

    <main v-else-if="currentWeather" class="outfit-main-content">
        
        <div class="weather-summary-bar">
            <div class="summary-inner">
                <span class="location">📍 {{ currentWeather.location }}</span>
                <div class="divider"></div>
                <span class="info-item">🌡️ 기온 <strong>{{ currentWeather.temp }}°C</strong></span>
                <span v-if="currentWeather.feelsLike != null" class="info-item">🥵 체감 <strong>{{ currentWeather.feelsLike }}°C</strong></span>
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
                        :class="[
                            { 'mask-card': item.type === '마스크' },
                            item.type === '마스크' ? getMaskCardClass(selectedHourlyWeather?.pm25Status) : ''
                        ]"
                    >
                        <template v-if="item.type === '마스크'">
                            <div class="mask-header" :class="getMaskHeaderClass(selectedHourlyWeather?.pm25Status)">
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
                            <div class="icon-placeholder" role="img" :aria-label="item.description">
                                {{ item.type }}
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
                        :key="data.time"
                        class="hourly-card"
                        :class="{ 'active-now': selectedHourIndex === index }"
                        @click="selectHour(index)"
                        @keydown.enter.prevent="selectHour(index)"
                        @keydown.space.prevent="selectHour(index)"
                        role="button"
                        tabindex="0"
                        :aria-pressed="selectedHourIndex === index"
                    >
                        <div class="time">{{ data.time }} {{ index === 0 ? '(지금)' : '' }}</div>
                        <div class="icon-placeholder small" role="img" :aria-label="getWeatherLabel(data.rain, data.sky)">{{ getWeatherIcon(data.rain, data.sky) }}</div>
                        <div class="temp">{{ data.temp }}°C</div>
                    </div>
                </div>
            </section>
        </div>
    </main>
</template>

<script setup>
    import { ref, computed, onMounted } from 'vue';
    import { useRoute } from 'vue-router';
    import { searchHistory } from '../stores/usehistory';
    import { currentWeather, hourlyData, hourlyOutfitData, isLoading, errorMessage, fetchWeatherData } from '../stores/useWeather';
    import { getWeatherIcon, getWeatherLabel, getTopIcon, getBottomIcon, getPackIcon } from '../utils/weather';

    const route = useRoute();

    // ------------------------------------------------------------------------
    // 1. 초기 데이터 로드 및 상태
    // ------------------------------------------------------------------------
    const lastSearchedLocation = computed(() => {
        return searchHistory.value.length > 0 ? searchHistory.value[0] : '지역을 검색해주세요';
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

    // ------------------------------------------------------------------------
    // 2. OOTD 로직
    // ------------------------------------------------------------------------
    const displayOotdItems = computed(() => {
        const weather = selectedHourlyWeather.value;
        const outfit = hourlyOutfitData.value?.length > 0 ? hourlyOutfitData.value[selectedHourIndex.value] : null;

        if (!weather || !outfit) return [];

        return [
            { id: 1, type: getTopIcon(outfit.top), name: outfit.top, description: '추천 상의' },
            { id: 2, type: getBottomIcon(outfit.bottom), name: outfit.bottom, description: '추천 하의' },
            { id: 3, type: getPackIcon(outfit.pack, weather.sky), name: outfit.pack === '불필요' ? '없음' : outfit.pack, description: '추천 소지품' },
            { id: 4, type: '마스크', name: outfit.mask === '마스크 선택' ? '자유' : outfit.mask, description: '식약처 인증 마스크' }
        ];
    });

    // ------------------------------------------------------------------------
    // 3. UI 유틸리티 함수 (백엔드 데이터 null 방어 로직 추가)
    // ------------------------------------------------------------------------
    const getDustTextClass = (status) => {
        if (status === '좋음') return 'text-good';
        // '정보없음' 일 때 빨간색으로 뜨지 않도록 '보통'과 동일한 컬러 부여
        if (status === '보통' || status === '정보없음') return 'text-normal';
        return 'text-bad'; 
    };

    const getMaskCardClass = (status) => {
        if (status === '좋음') return 'border-good';
        if (status === '보통' || status === '정보없음') return 'border-normal';
        return 'border-bad';
    };

    const getMaskHeaderClass = (status) => {
        if (status === '좋음') return 'bg-good';
        if (status === '보통' || status === '정보없음') return 'bg-normal';
        return 'bg-bad';
    };
</script>

<style scoped>
    /* --------------------------------------------------------------------------
       로딩 및 에러 상태 화면
    -------------------------------------------------------------------------- */
    .loading-screen {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
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

    .status-screen.error {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        color: var(--color-red-500);
        font-size: 1.2rem;
        font-weight: 600;
    }

    /* --------------------------------------------------------------------------
       전체 레이아웃
    -------------------------------------------------------------------------- */
    .outfit-main-content {
        background-color: var(--color-neutral-50);
        /* 헤더 높이(72px) 보정 + 모바일 동적 뷰포트 대응 */
        min-height: calc(100vh - 72px);
        min-height: calc(100dvh - 72px);
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
        width: 100%;
        margin: 0 auto;
        padding: 0 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        box-sizing: border-box;
    }

    .location { font-weight: 700; }
    .divider { width: 1px; height: 14px; background-color: var(--color-text-600); }
    .info-item { color: var(--color-neutral-200); }
    .info-item strong { color: #FFFFFF; font-weight: 600; }

    /* 메인 컨텐츠 래퍼 */
    .content-wrapper { 
        max-width: 1200px; 
        width: 100%;
        margin: 0 auto; 
        padding: 2rem 1rem; 
        box-sizing: border-box;
    }
    .section-title { font-size: 1.4rem; font-weight: 800; color: var(--color-text-900); margin-bottom: 1.5rem; }

    /* --------------------------------------------------------------------------
       OOTD 그리드 및 카드 공통
    -------------------------------------------------------------------------- */
    .ootd-section { margin-bottom: 3rem; }
    .ootd-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem; }

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

    /* --------------------------------------------------------------------------
       마스크 전용 카드
    -------------------------------------------------------------------------- */
    .mask-card {
        padding: 0;
        border: 2px solid transparent;
        overflow: hidden;
        text-align: left;
        align-items: stretch;
        justify-content: flex-start;
    }

    .mask-card.border-good { border-color: #10B981; }
    .mask-card.border-normal { border-color: var(--color-amber-500); }
    .mask-card.border-bad { border-color: var(--color-red-500); }

    .mask-header { 
        color: white; 
        font-weight: 700; 
        padding: 0.8rem 1rem; 
        font-size: 1.05rem; 
    }

    .mask-header.bg-good { background-color: #10B981; }
    .mask-header.bg-normal { background-color: var(--color-amber-500); }
    .mask-header.bg-bad { background-color: var(--color-red-500); }

    .mask-body { padding: 1.2rem 1rem; background: #FFFFFF; }
    .mask-body p { margin: 0 0 0.5rem 0; font-size: 0.9rem; color: var(--color-text-600); }

    /* 미세먼지 색상 */
    .text-good { color: #10B981; }
    .text-normal { color: var(--color-amber-500); }
    .text-bad { color: var(--color-red-500); }

    .mask-body .recommend-text { font-weight: 700; color: var(--color-text-900); margin-top: 0.8rem; }
    .mask-body .desc-text { font-size: 0.85rem; color: var(--color-text-400); margin-bottom: 1rem; }

    .badge-group { display: flex; gap: 0.5rem; }
    .badge { background: var(--color-neutral-100); color: var(--color-text-600); font-weight: 700; font-size: 0.7rem; padding: 0.3rem 0.6rem; border-radius: 6px; }

    /* --------------------------------------------------------------------------
       시간별 예보 그리드
    -------------------------------------------------------------------------- */
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

    /* --------------------------------------------------------------------------
       📱 모바일 화면 대응 (768px 이하) — 이전엔 미디어쿼리가 없어 6열이 찌그러짐
    -------------------------------------------------------------------------- */
    @media screen and (max-width: 768px) {
        .outfit-main-content {
            min-height: calc(100vh - 60px);
            min-height: calc(100dvh - 60px);
        }

        /* 요약 바: 가로 넘침 대신 줄바꿈 허용 */
        .summary-inner {
            flex-wrap: wrap;
            gap: 0.5rem 0.8rem;
            font-size: 0.85rem;
        }
        .summary-inner .divider { display: none; }

        .content-wrapper { padding: 1.5rem 1rem; }
        .section-title { font-size: 1.2rem; margin-bottom: 1rem; }

        /* OOTD: 4열 → 2열 */
        .ootd-section { margin-bottom: 2rem; }
        .ootd-grid { grid-template-columns: repeat(2, 1fr); gap: 1rem; }
        .ootd-card { padding: 1.5rem 0.8rem; }
        .icon-placeholder { width: 60px; height: 60px; font-size: 2.8rem; margin-bottom: 0.8rem; }

        /* 마스크 카드는 2열에서 가로 전체 차지 */
        .mask-card { grid-column: 1 / -1; }

        /* 시간별 예보: 6열 그리드 → 가로 스크롤(스와이프) */
        .hourly-grid {
            display: flex;
            gap: 0.8rem;
            overflow-x: auto;
            scroll-snap-type: x mandatory;
            -webkit-overflow-scrolling: touch;
            padding-bottom: 0.5rem;
        }
        .hourly-card {
            flex: 0 0 auto;
            min-width: 100px;
            scroll-snap-align: start;
            padding: 1.2rem 0.8rem;
        }
    }
</style>