<template>
    <main class="main-content search-layout">
        <aside class="left-panel">
            <div class="search-box-container">
                <div class="search-input-wrapper">
                    <span class="search-icon">🔍</span>
                    <input 
                        type="text" 
                        v-model="searchQuery" 
                        @input="handleInput" 
                        @keyup.enter="searchAddress(null)" 
                        placeholder="행정동 명 입력" 
                        class="search-input"
                    />
            
                    <ul v-if="showAutoComplete && filteredLocations.length > 0" class="autocomplete-list">
                        <li 
                            v-for="(loc, index) in filteredLocations" 
                            :key="index"
                            @click="selectLocation(loc)"
                            class="autocomplete-item"
                        >
                            {{ loc }}
                        </li>
                    </ul>
                </div>
                <button @click="searchAddress(null)" class="search-submit-btn">검색</button>
            </div>

            <div class="search-results-container">
                <h2 class="results-title">최근 검색 기록</h2>
                <div class="results-list">
                    <div v-if="searchHistory.length === 0" class="empty-history">
                        최근 검색한 내역이 없습니다.
                    </div>

                    <div 
                        v-else
                        v-for="(history, index) in searchHistory" 
                        :key="index" 
                        class="result-card" 
                        @click="clickHistory(history)"
                    >
                        <h3 class="result-name">🕒 {{ history }}</h3>
                        <button class="delete-btn" @click.stop="removeHistory(index)" title="기록 삭제">✕</button>
                    </div>
                </div>
            </div>
        </aside>

        <section class="right-panel map-section">
            <div id="kakao-map" class="map-container">
                <div v-if="!isMapLoaded" class="map-placeholder">
                    <div class="spinner"></div>
                    <p>지도를 불러오는 중입니다</p>
                </div>
            </div>

            <transition name="slide-up">
                <div v-if="showBottomPanel" class="bottom-weather-panel">
                    <div class="weather-content">
                        
                        <div v-if="isUnsupported" class="weather-data-box unsupported">
                            <div class="info-group location-group">
                                <span class="label">선택 지역</span>
                                <h2 class="area-title">
                                    <div class="city">{{ getLocationParts(lastAttemptedRegion).city }}</div>
                                    <div class="district">{{ getLocationParts(lastAttemptedRegion).district }}</div>
                                </h2>
                            </div>
                            <div class="status-warning">
                                ⚠️ 현재 지원하지 않는 지역입니다.
                            </div>
                        </div>

                        <div v-else-if="currentWeather" class="weather-data-box">
                            <div class="info-group location-group">
                                <span class="label">선택 지역</span>
                                <h2 class="area-title">
                                    <div class="city">{{ getLocationParts(currentWeather.location).city }}</div>
                                    <div class="district">{{ getLocationParts(currentWeather.location).district }}</div>
                                </h2>
                            </div>
                            
                            <div class="info-group data-group">
                                <div class="temp-display">
                                    <span class="icon">{{ getWeatherIcon(currentWeather.rain, currentWeather.sky) }}</span>
                                    <span class="degree">{{ currentWeather.temp }}°C</span>
                                </div>
                                <div class="divider"></div>
                                <div class="dust-display">
                                    <span class="dust-label">미세먼지</span>
                                    <span class="status" :class="getDustClass(currentWeather.pm10Status)">
                                        {{ currentWeather.pm10Status }}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <button class="action-btn" @click="goToHome">
                            복장지표 확인 👕
                        </button>
                    </div>
                </div>
            </transition>
        </section>
    </main>
</template>

<script setup>
    import { ref, computed, onMounted } from 'vue';
    import { useRouter } from 'vue-router';
    import { searchHistory, addToHistory } from '../stores/usehistory';
    import { currentWeather, fetchWeatherData, errorMessage } from '../stores/useWeather';

    const router = useRouter();

    const searchQuery = ref('');
    const showAutoComplete = ref(false);
    const sggData = ref([]); 
    const isUnsupported = ref(false); 
    const lastAttemptedRegion = ref(''); 
    const showBottomPanel = ref(false);
    
    const isMapLoaded = ref(false);
    let map = null;
    let marker = null;
    let geocoder = null;
    let currentPolygons = []; 

    const filteredLocations = computed(() => {
        if (!searchQuery.value) return [];
        const query = searchQuery.value.toLowerCase();
        const names = sggData.value.map(f => f.properties.adm_nm);
        return [...new Set(names)].filter(name => name.includes(query));
    });

    onMounted(async () => {
        try {
            const response = await fetch('/HangJeongDong_ver20260201.json'); 
            const data = await response.json();
            sggData.value = data.features;
        } catch (e) { 
            console.error("JSON 로드 실패:", e); 
        }
        loadKakaoMap();
    });

    const loadKakaoMap = () => {
        if (window.kakao && window.kakao.maps) {
            window.kakao.maps.load(() => initMap());
        } else {
            console.log("카카오맵 SDK 대기 중...");
            setTimeout(loadKakaoMap, 300);
        }
    };

    const initMap = () => {
        const container = document.getElementById('kakao-map');
        map = new window.kakao.maps.Map(container, {
            center: new window.kakao.maps.LatLng(37.449419, 126.700583),
            level: 4
        });
        geocoder = new window.kakao.maps.services.Geocoder();
        isMapLoaded.value = true;
    };

    const clearMapGraphics = () => {
        if (marker) marker.setMap(null);
        currentPolygons.forEach(polygon => polygon.setMap(null));
        currentPolygons = [];
    };

    const drawSggPolygon = (feature) => {
        const geometry = feature.geometry;
        const makePolygon = (coordinates) => {
            const path = coordinates.map(coord => new window.kakao.maps.LatLng(coord[1], coord[0]));
            const polygon = new window.kakao.maps.Polygon({
                path: path,
                strokeWeight: 3,
                strokeColor: '#D97706',
                strokeOpacity: 0.8,
                fillColor: '#F59E0B',
                fillOpacity: 0.2
            });
            polygon.setMap(map);
            currentPolygons.push(polygon);
        };

        if (geometry.type === 'Polygon') {
            makePolygon(geometry.coordinates[0]);
        } else if (geometry.type === 'MultiPolygon') {
            geometry.coordinates.forEach(coords => makePolygon(coords[0]));
        }
    };

    const handleInput = () => { 
        showAutoComplete.value = searchQuery.value.length > 0; 
    };

    const selectLocation = (location) => {
        searchQuery.value = location;
        showAutoComplete.value = false;
        searchAddress(location);
    };

    const searchAddress = async (keyword = null) => {
        let inputKeyword = keyword || searchQuery.value;
        if (!inputKeyword || !geocoder) return;

        const targetFeature = sggData.value.find(f => f.properties.adm_nm.includes(inputKeyword));
        
        if (!targetFeature) {
            alert('정확한 행정동명을 입력해주세요.');
            return;
        }

        const officialName = targetFeature.properties.adm_nm;
        
        lastAttemptedRegion.value = officialName;
        showBottomPanel.value = false;

        geocoder.addressSearch(officialName, async (result, status) => {
            if (status === window.kakao.maps.services.Status.OK) {
                const coords = new window.kakao.maps.LatLng(result[0].y, result[0].x);
                
                clearMapGraphics();
                map.setCenter(coords);
                marker = new window.kakao.maps.Marker({ position: coords, map: map });
                drawSggPolygon(targetFeature); 
                
                await fetchWeatherData(officialName);
                isUnsupported.value = !!errorMessage.value || (currentWeather.value?.location.includes('지원하지 않'));

                searchQuery.value = officialName;
                showAutoComplete.value = false;
                
                addToHistory(officialName);
                showBottomPanel.value = true;
            }
        });
    };

    const clickHistory = (historyName) => {
        searchAddress(historyName);
    };

    const removeHistory = (index) => {
        searchHistory.value.splice(index, 1);
    };

    // 🌟 요구사항 1 반영: 검색 결과 들고 홈('/')으로 이동
    const goToHome = () => {
        if (isUnsupported.value) {
            alert('현재 지원하지 않는 지역입니다.\n홈 화면 이동 시 [인천광역시 남동구 구월3동] 데이터로 안내됩니다.');
        }
        const regionToPass = isUnsupported.value ? '인천광역시 남동구 구월3동' : currentWeather.value.location;
        addToHistory(regionToPass); 
        router.push({ path: '/', query: { region: regionToPass } });
    };

    const getDustClass = (status) => {
        if (status === '좋음') return 'good';
        if (status === '보통') return 'normal';
        if (status === '나쁨' || status === '매우나쁨') return 'bad';
        return ''; 
    };

    const getLocationParts = (location) => {
        if (!location) return { city: '', district: '' };
        const parts = location.split(' ');
        if (parts.length >= 2) {
            return {
                city: parts[0], 
                district: parts.slice(1).join(' ') 
            };
        }
        return { city: location, district: '' };
    };

    const getWeatherIcon = (rain, sky) => {
        if (!sky) return '🌤️'; 
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
        return '🌤️';
    };
</script>

<style scoped>
    /* ... Search CSS 유지 ... */
    .search-layout { flex: 1; max-width: 1200px; width: 100%; margin: 2rem auto; padding: 0 1rem; display: grid; grid-template-columns: 380px 1fr; gap: 1.5rem; box-sizing: border-box; }
    .left-panel { display: flex; flex-direction: column; gap: 1.5rem; align-items: stretch; width: 100%; }
    .search-box-container { position: relative; display: flex; gap: 0.5rem; height: 48px; box-sizing: border-box; z-index: 50; }
    .search-input-wrapper { position: relative; flex: 1; display: flex; align-items: center; background: #FFFFFF; border: 1px solid var(--color-neutral-200); border-radius: 8px; padding: 0 1rem; box-sizing: border-box; height: 100%; }
    .search-input { flex: 1; height: 100%; border: none; outline: none; font-size: 0.95rem; color: var(--color-text-900); padding: 0; margin-left: 0.5rem; width: 100%; }
    .search-submit-btn { background-color: var(--color-red-500); color: #FFFFFF; border: none; border-radius: 8px; padding: 0 1.5rem; font-weight: 600; font-size: 1rem; cursor: pointer; white-space: nowrap; height: 100%; box-sizing: border-box; }
    .autocomplete-list { position: absolute; top: calc(100% + 8px); left: 0; width: 100%; background: #FFFFFF; border: 1px solid var(--color-neutral-200); border-radius: 8px; margin: 0; padding: 0; list-style-type: none !important; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); z-index: 999; max-height: 250px; overflow-y: auto; }
    .autocomplete-item { padding: 0.8rem 1.2rem; cursor: pointer; border-bottom: 1px solid var(--color-neutral-100); font-size: 0.95rem; color: var(--color-text-900); text-align: left; }
    .search-results-container { background: #FFFFFF; border-radius: 12px; border: 1px solid var(--color-neutral-200); padding: 1.5rem; flex: 1; }
    .empty-history { color: var(--color-text-400); text-align: center; margin-top: 2rem; }
    .result-card { border: 1px solid var(--color-neutral-200); border-radius: 8px; padding: 1rem; margin-top: 0.5rem; cursor: pointer; display: flex; align-items: center; justify-content: space-between; transition: background-color 0.2s; }
    .result-card:hover { background-color: var(--color-neutral-50); }
    .result-name { font-size: 1.05rem; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--color-text-900); flex: 1; }
    .delete-btn { background: none; border: none; color: var(--color-text-400); font-size: 1.1rem; cursor: pointer; padding: 0.2rem 0.5rem; transition: color 0.2s; }
    .delete-btn:hover { color: var(--color-red-500); }
    .map-section { position: relative; background: white; border-radius: 12px; border: 1px solid var(--color-neutral-200); overflow: hidden; }
    .map-container { width: 100%; height: 100%; min-height: 550px; }
    .map-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; min-height: 550px; background-color: var(--color-neutral-50, #f8fafc); color: var(--color-text-600, #475569); font-weight: 600; font-size: 1.1rem; gap: 1.5rem; }
    .spinner { width: 50px; height: 50px; border: 5px solid var(--color-neutral-200, #e2e8f0); border-top: 5px solid var(--color-amber-500, #f59e0b); border-radius: 50%; animation: spin 1s cubic-bezier(0.55, 0.15, 0.45, 0.85) infinite; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .bottom-weather-panel { position: absolute; bottom: 20px; left: 20px; right: 20px; z-index: 10; background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 16px; padding: 1.5rem 2rem; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1); min-height: 115px; display: flex; align-items: center; box-sizing: border-box; }
    .weather-content { display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 2rem; }
    .weather-data-box { display: flex; align-items: center; gap: 3rem; flex: 1; }
    .weather-data-box.unsupported { gap: 2rem; }
    .unsupported-msg-box { display: flex; flex-direction: column; justify-content: center; gap: 0.4rem; flex: 1; }
    .location-group { min-width: 150px; flex-shrink: 0; }
    .area-title { margin: 0; line-height: 1.3; }
    .area-title .city { font-size: 1rem; font-weight: 600; color: var(--color-text-600); }
    .area-title .district { font-size: 1.35rem; font-weight: 800; color: #1e293b; }
    .info-group .label { font-size: 0.75rem; color: #64748b; display: block; margin-bottom: 0.2rem; }
    .status-warning { color: var(--color-red-500); font-weight: 700; font-size: 1.1rem; flex: 1;}
    .data-group { display: flex; align-items: center; gap: 1.5rem; flex-shrink: 0; }
    .temp-display { display: flex; align-items: center; gap: 0.5rem; white-space: nowrap; }
    .temp-display .icon { font-size: 2rem; }
    .temp-display .degree { font-size: 1.8rem; font-weight: 800; color: #1e293b; }
    .divider { width: 1px; height: 30px; background: #cbd5e1; }
    .dust-display { display: flex; align-items: center; gap: 0.6rem; white-space: nowrap; }
    .dust-display .dust-label { font-size: 0.9rem; color: #64748b; margin: 0; }
    .status { font-weight: 700; font-size: 1.1rem; }
    .status.good { color: #10b981; }
    .status.normal { color: #f59e0b; }
    .status.bad { color: #ef4444; }
    .action-btn { background: #1e293b; color: white; border: none; padding: 0.8rem 1.2rem; border-radius: 10px; font-weight: 700; cursor: pointer; transition: transform 0.2s; white-space: nowrap; }
    .action-btn:hover { transform: scale(1.05); }
    .slide-up-enter-active, .slide-up-leave-active { transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
    .slide-up-enter-from, .slide-up-leave-to { transform: translateY(40px); opacity: 0; }
</style>