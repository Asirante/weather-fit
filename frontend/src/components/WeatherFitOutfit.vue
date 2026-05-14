<template>
  <main class="outfit-main-content">
    <section class="guide-section">
      <h2 class="section-title">👔 기온별 범용 복장 가이드</h2>
      <p class="section-desc">날씨와 기온에 따라 아래의 기준으로 옷차림이 추천됩니다.</p>
      
      <div class="table-responsive">
        <table class="guide-table">
          <thead>
            <tr>
              <th>기온</th>
              <th>추천 상의</th>
              <th>추천 하의</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(guide, index) in outfitGuides" :key="index">
              <td class="temp-col"><strong>{{ guide.temp }}</strong></td>
              <td>{{ guide.top }}</td>
              <td>{{ guide.bottom }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="extra-guide">
        <h3 class="sub-title">😷 미세먼지 및 🌂 강수 기준</h3>
        <ul class="extra-guide-list">
          <li><strong>미세먼지 / 초미세먼지 나쁨 이상:</strong> KF80 또는 KF94 마스크 착용 필수</li>
          <li><strong>강수량 1mm 미만:</strong> 접이식 우산 추천</li>
          <li><strong>강수량 1mm 이상 (비/눈):</strong> 우산 필수</li>
        </ul>
      </div>
    </section>
  </main>
</template>

<script setup>
// 백엔드 파이썬 코드의 온도 기준을 바탕으로 한 범용 가이드 데이터입니다.
const outfitGuides = [
  { temp: '28°C 이상', top: '민소매, 반팔, 린넨 소재', bottom: '반바지, 짧은 치마' },
  { temp: '23°C ~ 27°C', top: '반팔, 얇은 셔츠', bottom: '반바지, 면바지' },
  { temp: '17°C ~ 22°C', top: '긴팔 티셔츠, 가디건, 후드티, 맨투맨', bottom: '청바지, 면바지, 슬랙스' },
  { temp: '12°C ~ 16°C', top: '가디건, 야상, 재킷, 니트', bottom: '두꺼운 긴바지, 청바지' },
  { temp: '5°C ~ 11°C', top: '코트, 가죽재킷, 두꺼운 니트', bottom: '기모바지, 청바지' },
  { temp: '4°C 이하', top: '패딩, 두꺼운 롱코트, 방한복, 기모 이너', bottom: '방한복, 기모바지' }
];
</script>

<style scoped>
.outfit-main-content { padding: 20px; max-width: 600px; margin: 0 auto; }
.section-title { font-size: 1.3rem; color: #1e293b; margin-bottom: 5px; font-weight: 700; }
.section-desc { font-size: 0.95rem; color: #64748b; margin-bottom: 20px; }

.table-responsive {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.04);
  border: 1px solid #e2e8f0;
  margin-bottom: 30px;
}

.guide-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.guide-table th {
  background-color: #f8fafc;
  padding: 14px 16px;
  color: #334155;
  font-weight: 700;
  border-bottom: 2px solid #e2e8f0;
}

.guide-table td {
  padding: 14px 16px;
  color: #475569;
  border-bottom: 1px solid #f1f5f9;
  line-height: 1.5;
}

.guide-table tr:last-child td {
  border-bottom: none;
}

.temp-col {
  color: #0ea5e9 !important;
  white-space: nowrap;
}

.extra-guide {
  background: #f8fafc;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.sub-title {
  font-size: 1.1rem;
  color: #1e293b;
  margin-top: 0;
  margin-bottom: 15px;
}

.extra-guide-list {
  padding-left: 20px;
  margin: 0;
  color: #475569;
  line-height: 1.6;
}

.extra-guide-list strong {
  color: #334155;
}
</style>