import { describe, it, expect } from 'vitest';
import { getDustStatusText, parseLambdaResponse } from '../../src/stores/useWeather';

describe('getDustStatusText', () => {
    it('등급 코드를 한글 상태로 변환한다', () => {
        expect(getDustStatusText('1')).toBe('좋음');
        expect(getDustStatusText('2')).toBe('보통');
        expect(getDustStatusText('3')).toBe('나쁨');
        expect(getDustStatusText('4')).toBe('매우나쁨');
    });

    it('숫자 타입도 처리한다', () => {
        expect(getDustStatusText(1)).toBe('좋음');
    });

    it('null/undefined는 정보없음으로 방어한다', () => {
        expect(getDustStatusText(null)).toBe('정보없음');
        expect(getDustStatusText(undefined)).toBe('정보없음');
    });

    it('알 수 없는 코드는 보통으로 폴백한다', () => {
        expect(getDustStatusText('9')).toBe('보통');
    });
});

describe('parseLambdaResponse', () => {
    it('body가 JSON 문자열이면 파싱한다 (Lambda proxy 형태)', () => {
        const raw = { statusCode: 200, body: JSON.stringify({ temp: 12 }) };
        expect(parseLambdaResponse(raw)).toEqual({ temp: 12 });
    });

    it('이미 객체면 그대로 반환한다', () => {
        const raw = { temp: 12 };
        expect(parseLambdaResponse(raw)).toEqual({ temp: 12 });
    });

    it('null이면 그대로 반환한다', () => {
        expect(parseLambdaResponse(null)).toBeNull();
    });
});
