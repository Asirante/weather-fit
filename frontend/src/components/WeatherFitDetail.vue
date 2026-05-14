<template>
  <main class="detail-main-content">
    <div v-if="isLoading" class="loading-screen">
      <div class="spinner"></div>
      <p>상세정보를 불러오고 있습니다...</p>
    </div>

    <div v-else-if="errorMessage" class="status-screen error">
      <p>{{ errorMessage }}</p>
    </div>

    <div v-else-if="currentWeather" class="content-wrapper">
      
      <!-- 1. 날씨 요약 바 -->
      <div class="weather-summary-bar">
        <div class="summary-inner">
          <span class="location">📍 {{ currentWeather.location }}</span>
          <div class="divider"></div>
          <span class="info-item">🌡️ <strong>{{ currentWeather.temp }}°C</strong></span>
          <span class="info-item">💧 먼지: <strong>{{ currentWeather.pm10Status }}</strong></span>
        </div>
      </div>

      <!-- 2. OOTD (오늘의 실제 옷차림 추천 데이터) -->
      <section class="ootd-section detail-section" v-if="currentOutfit">
        <h2 class="section-title">👕 현재 날씨 맞춤 추천</h2>
        
        <div class="condition-cards">
          <div class="cond-card">
            <h3 class="cond-title">추천 상의</h3>
            <div class="clothes-tags">
              <span v-for="(item, index) in topList" :key="'top-'+index" class="cloth-tag">
                #{{ item }}
              </span>
            </div>
          </div>

          <div class="cond-card">
            <h3 class="cond-title">추천 하의</h3>
            <div class="clothes-tags">
              <span v-for="(item, index) in bottomList" :key="'bottom-'+index" class="cloth-tag">
                #{{ item }}
              </span>
            </div>
          </div>

          <div class="cond-card item-card">
            <h3 class="cond-title">외출 필수품</h3>
            <div class="accessories-flex">
              <p>😷 마스크: <strong>{{ currentOutfit.mask }}</strong></p>
              <p>🌂 우산/가방: <strong>{{ currentOutfit.pack }}</strong></p>
            </div>
          </div>
        </div>
      </section>

      <!-- 3. 시간별 예보 -->
      <section class="hourly-section detail-section" v-if="hourlyData && hourlyData.length">
        <h2 class="section-title">⏰ 시간별 예보</h2>
        <div class="hourly-flex">
          <div v-for="(hour, index) in hourlyData" :key="index" class="hourly-item">
            <span class="hour-time">{{ hour.time }}</span>
            <span class="hour-temp">{{ hour.temp }}°C</span>
            <span class="hour-desc">{{ hour.sky }}</span>
          </div>
        </div>
      </section>

    </div>
  </main>
</template>

<script setup>
import { computed } from 'vue';
import { isLoading, errorMessage, currentWeather, hourlyData, currentOutfit } from '../stores/useWeather';

// 문자열로 들어오거나 배열로 들어오는 의상 데이터를 배열 형태로 정규화하여 태그로 만듭니다.
const topList = computed(() => {
  if (!currentOutfit.value || !currentOutfit.value.top) return [];
  return Array.isArray(currentOutfit.value.top) 
    ? currentOutfit.value.top 
    : currentOutfit.value.top.split(',').map(s => s.trim());
});

const bottomList = computed(() => {
  if (!currentOutfit.value || !currentOutfit.value.bottom) return [];
  return Array.isArray(currentOutfit.value.bottom) 
    ? currentOutfit.value.bottom 
    : currentOutfit.value.bottom.split(',').map(s => s.trim());
});
</script>

<style scoped>
.detail-main-content { padding: 20px; max-width: 600px; margin: 0 auto; }
.weather-summary-bar { background: #f8fafc; padding: 15px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
.summary-inner { display: flex; gap: 15px; align-items: center; justify-content: center; font-size: 0.95rem; }
.divider { width: 1px; height: 16px; background: #cbd5e1; }
.info-item strong { color: #1e293b; }

.section-title { font-size: 1.2rem; color: #1e293b; margin-bottom: 15px; font-weight: 700; }
.detail-section { margin-bottom: 30px; }

/* OOTD(옷 추천) 카드 스타일 */
.condition-cards { display: flex; flex-direction: column; gap: 12px; }
.cond-card { background: #FFFFFF; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
.cond-title { font-size: 1.05rem; color: #64748b; margin-bottom: 12px; margin-top: 0; }
.clothes-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.cloth-tag { background: #f1f5f9; border: 1px solid #cbd5e1; color: #475569; padding: 8px 14px; border-radius: 20px; font-size: 0.95rem; font-weight: 600; }
.item-card { background: #f8fafc; }
.accessories-flex p { margin: 8px 0; font-size: 1.05rem; color: #334155; }
.accessories-flex strong { color: #0f172a; }

/* 시간별 예보 스타일 */
.hourly-flex { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 10px; }
.hourly-item { flex: 1; min-width: 70px; background: white; padding: 15px 10px; border-radius: 12px; text-align: center; border: 1px solid #e2e8f0; }
.hour-time { display: block; font-size: 0.9rem; color: #64748b; margin-bottom: 8px; }
.hour-temp { display: block; font-weight: 700; font-size: 1.1rem; margin-bottom: 4px; color: #1e293b;}
.hour-desc { font-size: 0.85rem; color: #94a3b8; }
</style>