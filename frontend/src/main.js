import { createApp } from 'vue';
import App from './App.vue';
import router from './router'; // 설정한 라우터 불러오기

const app = createApp(App);
app.use(router); // 라우터 플러그인 사용
app.mount('#app');