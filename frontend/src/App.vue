<template>
  <div class="weatherfit-app">
    <header class="header">
      <div class="header-container">
        <h1 class="logo">WeatherFit</h1>
        <nav class="nav-menu">
          <button @click="goTo('/')" :class="route.path === '/' ? 'nav-button accent-btn' : 'nav-text-btn'">홈</button>
          <button @click="goTo('/search')" :class="route.path === '/search' ? 'nav-button accent-btn' : 'nav-text-btn'">지역검색</button>
          <button @click="goTo('/outfit')" :class="route.path === '/outfit' ? 'nav-button accent-btn' : 'nav-text-btn'">복장지표</button>
        </nav>
      </div>
    </header>

    <router-view></router-view>

    <footer class="footer">
      <p>© 2026 WeatherFit | 2팀 | 서버리스 아키텍처 기반 옷차림 추천 서비스</p>
    </footer>
  </div>

</template>

<script setup>

  import { useRouter, useRoute } from 'vue-router';

  const router = useRouter();
  const route = useRoute(); // 현재 페이지의 경로 정보를 가져오는 객체

  const goTo = (path) => {
    router.push(path);
  };

</script>

<style>
  /* 가장자리 여백 초기화 (전역 설정) */
  body {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }
</style>

<style scoped>
  /* 앱 전체 컨테이너 및 전역 색상 변수 */
  .weatherfit-app {
    --color-navy-900: #0F172A;
    --color-navy-800: #1E293B;
    --color-amber-600: #D97706;
    --color-amber-500: #F59E0B;
    --color-red-500: #FF4444;
    --color-neutral-50: #F8FAFC;
    --color-neutral-100: #F1F5F9;
    --color-neutral-200: #E2E8F0;
    --color-text-900: #0F172A;
    --color-text-600: #475569;
    --color-text-400: #94A3B8;

    font-family: 'Pretendard', -apple-system, sans-serif;
    background-color: var(--color-neutral-100);
    min-height: 100vh;
    width: 100%;
    display: flex;
    flex-direction: column;
    color: var(--color-text-900);
  }

  /* 헤더 스타일 */
  .header {
    background-color: var(--color-navy-900);
    color: white;
    padding: 0 2rem;
    height: 72px;
    min-height: 72px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    width: 100%;
    box-sizing: border-box;
  }

  .header-container {
    max-width: 1200px;
    width: 100%;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .logo { font-size: 1.75rem; font-weight: 700; margin: 0; }
  .nav-menu { display: flex; gap: 2rem; align-items: center; }

  /* 활성화된 주황색 버튼 */
  .nav-button.accent-btn {
    background-color: var(--color-amber-600);
    color: white;
    border: none;
    padding: 0.5rem 1.5rem;
    border-radius: 2rem;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  /* 비활성화된 일반 텍스트 버튼 */
  .nav-text-btn {
    background: none;
    border: none;
    color: var(--color-neutral-200);
    font-size: 1rem;
    font-family: inherit;
    cursor: pointer;
    padding: 0;
    transition: color 0.2s ease;
  }
  .nav-text-btn:hover { color: #FFFFFF; }

  /* 푸터 스타일 */
  .footer {
    background-color: var(--color-navy-900);
    color: var(--color-text-400);
    text-align: center;
    padding: 1.5rem;
    font-size: 0.875rem;
    width: 100%;
    flex-shrink: 0;
    margin-top: auto;
    box-sizing: border-box;
  }

</style>