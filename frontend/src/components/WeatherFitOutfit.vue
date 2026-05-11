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
                                <div class="icon-placeholder">
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
                            :key="index" 
                            class="hourly-card"
                            :class="{ 'active-now': selectedHourIndex === index }"
                            @click="selectHour(index)"
                        >
                            <div class="time">{{ data.time }} {{ index === 0 ? '(지금)' : '' }}</div>
                            <div class="icon-placeholder small">{{ getWeatherIcon(data.rain, data.sky) }}</div>
                            <div class="temp">{{ data.temp }}°C</div>
                        </div>
                    </div>
                </section>
            </div>
        </div>

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
        } else{
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

    const getMaskCardClass = (status) => {
        if (status === '좋음') return 'border-good';
        if (status === '보통') return 'border-normal';
        return 'border-bad'; // 나쁨, 매우나쁨
    };

    const getMaskHeaderClass = (status) => {
        if (status === '좋음') return 'bg-good';
        if (status === '보통') return 'bg-normal';
        return 'bg-bad'; // 나쁨, 매우나쁨
    };

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

    // 정적 가이드 데이터
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
    /* 로딩 및 에러 상태 화면 */
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

    /* 가이드 섹션 */
    .guide-container { 
        max-width: 1200px; 
        width: 100%; 
        margin: 0 auto 4rem auto; 
        padding: 0 1rem; 
        font-family: 'Pretendard', sans-serif; 
        box-sizing: border-box;
    }
    
    .guide-banner { 
        background-color: var(--color-navy-800); 
        border-radius: 20px; 
        padding: 3rem; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 2rem; 
        margin-top: 2rem;
        color: #FFFFFF; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.1); 
    }
    .banner-content { flex: 1; }
    .guide-badge { background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2); color: var(--color-amber-500); padding: 0.4rem 0.8rem; border-radius: 8px; font-size: 0.85rem; font-weight: 700; }
    .banner-title { font-size: 2.2rem; font-weight: 800; margin: 1.5rem 0 1rem 0; }
    .banner-desc { color: var(--color-text-400); font-size: 1rem; line-height: 1.6; margin-bottom: 1.5rem; }
    .tag-group { display: flex; gap: 0.8rem; flex-wrap: wrap; }
    .tag { background: rgba(255, 255, 255, 0.08); padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.9rem; color: var(--color-neutral-100); }
    .banner-icon-wrapper { margin-left: 2rem; }
    .icon-circle { width: 160px; height: 160px; background: rgba(255, 255, 255, 0.05); border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 5rem; }
    .guide-content-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 2rem; }
    .section-header h2 { font-size: 1.4rem; font-weight: 800; color: var(--color-text-900); margin-bottom: 1.5rem; }
    .temp-guide-section { background: #FFFFFF; border: 1px solid var(--color-neutral-200); border-radius: 16px; padding: 2rem; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }
    .temp-table { display: flex; flex-direction: column; }
    .table-head { display: flex; padding-bottom: 1rem; border-bottom: 1px solid var(--color-neutral-200); color: var(--color-text-600); font-size: 0.9rem; font-weight: 600; }   
    .table-row { display: flex; padding: 1.5rem 0; border-bottom: 1px solid var(--color-neutral-100); align-items: center; }
    .table-row:last-child { border-bottom: none; padding-bottom: 0; }
    .col-state { width: 80px; display: flex; justify-content: center; }
    .col-temp { width: 140px; }
    .col-clothes { flex: 1; }
    .state-circle { width: 44px; height: 44px; border-radius: 50%; display: flex; justify-content: center; align-items: center; color: #FFFFFF; font-weight: 800; font-size: 1.2rem; }
    .temp-range { font-size: 1.15rem; font-weight: 700; color: var(--color-text-900); margin: 0 0 0.3rem 0; }
    .temp-sub { font-size: 0.85rem; color: var(--color-text-400); }
    .clothes-tags { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.8rem; }
    .cloth-tag { background: var(--color-neutral-50); border: 1px solid var(--color-neutral-200); color: var(--color-text-600); padding: 0.4rem 0.8rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600; }
    .clothes-desc { font-size: 0.85rem; color: var(--color-text-400); margin: 0; }
    .condition-guide-section { display: flex; flex-direction: column; }
    .condition-cards { display: flex; flex-direction: column; gap: 1.2rem; }
    .cond-card { background: #FFFFFF; border: 1px solid var(--color-neutral-200); border-radius: 16px; padding: 1.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }
    .cond-title { font-size: 1.1rem; font-weight: 700; color: var(--color-navy-800); margin: 0 0 1.2rem 0; display: flex; align-items: center; gap: 0.5rem; }
    .cond-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.8rem; }
    .cond-list li { display: flex; align-items: center; gap: 0.8rem; font-size: 0.95rem; color: var(--color-text-600); }
    .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
    .dot-green { background-color: #10B981; } .dot-yellow { background-color: var(--color-amber-500); } .dot-red { background-color: var(--color-red-500); }
</style>