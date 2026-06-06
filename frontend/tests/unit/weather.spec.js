import { describe, it, expect } from 'vitest';
import {
    getWeatherIcon,
    getWeatherLabel,
    getTopIcon,
    getBottomIcon,
    getPackIcon,
} from '../../src/utils/weather';

describe('getWeatherIcon', () => {
    it('하늘 정보가 없으면 기본 아이콘을 반환한다', () => {
        expect(getWeatherIcon('강수없음', '')).toBe('🌤️');
        expect(getWeatherIcon('강수없음', null)).toBe('🌤️');
    });

    it('강수가 없을 때 맑음/흐림을 구분한다', () => {
        expect(getWeatherIcon('강수없음', '맑음')).toBe('☀️');
        expect(getWeatherIcon('강수없음', '흐림')).toBe('⛅');
    });

    it('강수가 있으면 비/눈 아이콘을 반환한다', () => {
        expect(getWeatherIcon('비', '비')).toBe('🌧️');
        expect(getWeatherIcon('눈', '눈')).toBe('🌨️');
    });
});

describe('getWeatherLabel', () => {
    it('스크린리더용 텍스트 라벨을 반환한다', () => {
        expect(getWeatherLabel('강수없음', '맑음')).toBe('맑음');
        expect(getWeatherLabel('비', '비')).toBe('비');
        expect(getWeatherLabel('눈', '눈')).toBe('눈');
        expect(getWeatherLabel('강수없음', null)).toBe('날씨 정보');
    });
});

describe('getTopIcon', () => {
    it('두꺼운 외투(패딩/코트)를 우선 판별한다', () => {
        expect(getTopIcon('롱패딩')).toBe('🧣');
        expect(getTopIcon('코트')).toBe('🧣');
    });

    it('재킷류와 긴팔류를 구분한다', () => {
        expect(getTopIcon('가죽 재킷')).toBe('🧥');
        expect(getTopIcon('니트, 가디건')).toBe('👔');
    });

    it('해당 없으면 기본 반팔 아이콘', () => {
        expect(getTopIcon('반팔 티셔츠')).toBe('👕');
        expect(getTopIcon('')).toBe('👕');
    });
});

describe('getBottomIcon', () => {
    it('반바지/치마는 반바지 아이콘', () => {
        expect(getBottomIcon('반바지')).toBe('🩳');
        expect(getBottomIcon('치마')).toBe('🩳');
    });

    it('그 외에는 긴바지 아이콘', () => {
        expect(getBottomIcon('청바지')).toBe('👖');
        expect(getBottomIcon('')).toBe('👖');
    });
});

describe('getPackIcon', () => {
    it('우산이 필요하면 우산 아이콘', () => {
        expect(getPackIcon('우산', '비')).toBe('☔');
    });

    it('눈이 오면 눈 아이콘', () => {
        expect(getPackIcon('불필요', '눈')).toBe('🌨️');
    });

    it('해당 없으면 기본 아이콘', () => {
        expect(getPackIcon('불필요', '맑음')).toBe('✋');
        expect(getPackIcon()).toBe('✋');
    });
});
