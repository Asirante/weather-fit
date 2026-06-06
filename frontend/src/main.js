import { createApp } from 'vue';
import App from './App.vue';
import router from './router'; // 설정한 라우터 불러오기

const app = createApp(App);
app.use(router); // 라우터 플러그인 사용
app.mount('#app');

// PWA: 서비스워커 등록 (HTTPS 또는 localhost에서만 동작)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register(`${process.env.BASE_URL}service-worker.js`)
      .catch((err) => console.warn('서비스워커 등록 실패:', err));
  });
}