// 날씨 관련 공용 유틸리티
// (Home / Search / Outfit 세 컴포넌트에 흩어져 있던 중복 로직을 통합)

/**
 * 강수/하늘 상태로 날씨 이모지를 반환한다.
 * @param {string} rain 강수 형태 (예: '강수없음', '비', '눈')
 * @param {string} sky 하늘 상태 (예: '맑음', '흐림')
 * @returns {string} 날씨 이모지
 */
export const getWeatherIcon = (rain, sky) => {
    if (!sky) return '🌤️';
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

/**
 * 날씨 이모지에 대응하는 사람이 읽을 수 있는 라벨(스크린리더용).
 */
export const getWeatherLabel = (rain, sky) => {
    if (!sky) return '날씨 정보';
    if (rain && rain !== '강수없음') {
        if (rain.includes('비') || sky.includes('비')) return '비';
        if (rain.includes('눈') || sky.includes('눈')) return '눈';
    }
    if (sky === '맑음') return '맑음';
    if (sky.includes('흐림')) return '흐림';
    return sky;
};

/**
 * 추천 상의 텍스트에 어울리는 이모지를 반환한다.
 */
export const getTopIcon = (top = '') => {
    // 두꺼운 겉옷·방한 → 코트 아이콘
    if (top.includes('패딩') || top.includes('코트') || top.includes('방한')
        || top.includes('가죽') || top.includes('재킷') || top.includes('야상')) return '🧥';
    // 긴팔·니트·후드류 → 긴소매 상의
    if (top.includes('긴팔') || top.includes('니트') || top.includes('가디건')
        || top.includes('맨투맨') || top.includes('후드') || top.includes('기모')) return '👔';
    // 반팔·민소매·얇은 소재 → 반소매 티셔츠
    return '👕';
};

/**
 * 추천 하의 텍스트에 어울리는 이모지를 반환한다.
 */
export const getBottomIcon = (bottom = '') => {
    if (bottom.includes('반바지') || bottom.includes('치마')) return '🩳';
    return '👖';
};

/**
 * 소지품(우산 등) 이모지를 반환한다.
 */
export const getPackIcon = (pack = '', sky = '') => {
    if (pack.includes('우산')) return '☔';
    if (sky?.includes('눈')) return '🌨️';
    return '✋';
};
