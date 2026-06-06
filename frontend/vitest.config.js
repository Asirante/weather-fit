import { defineConfig } from 'vitest/config';

// 순수 함수(유틸/스토어 헬퍼) 단위 테스트용 설정.
// .vue SFC는 테스트 대상에 포함하지 않으므로 vue 플러그인은 불필요.
export default defineConfig({
    test: {
        environment: 'node',
        include: ['tests/unit/**/*.spec.js'],
    },
});
