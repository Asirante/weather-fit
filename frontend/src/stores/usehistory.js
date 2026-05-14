import { ref, watch } from 'vue';

// 1. 브라우저 저장소(localStorage)에서 기존 기록 불러오기 (없으면 빈 배열)
const savedHistory = JSON.parse(localStorage.getItem('weatherFit-history')) || [];

// 2. 핵심: export const로 선언하여 앱 전체에서 공유할 수 있는 전역 변수 만들기
export const searchHistory = ref(savedHistory);

// 3. 기록이 변경될 때마다 자동으로 브라우저 저장소에 저장 (새로고침해도 안 날아감!)
watch(searchHistory, (newHistory) => {
  localStorage.setItem('weatherFit-history', JSON.stringify(newHistory));
}, { deep: true });

// 4. 기록 추가 로직도 이곳에 모아두면 컴포넌트 코드가 훨씬 깔끔해집니다.
export const addToHistory = (keyword) => {
  // 중복 제거
  searchHistory.value = searchHistory.value.filter(item => item !== keyword);
  // 맨 앞에 추가
  searchHistory.value.unshift(keyword);
  // 최대 5개 유지
  if (searchHistory.value.length > 5) {
    searchHistory.value.pop();
  }
};