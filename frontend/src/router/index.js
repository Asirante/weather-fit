import { createRouter, createWebHistory } from 'vue-router'
import WeatherFitHome from '../components/WeatherFitHome.vue'
import WeatherFitSearch from '../components/WeatherFitSearch.vue'
import WeatherFitOutfit from '../components/WeatherFitOutfit.vue'
import WeatherFitDetail from '../components/WeatherFitDetail.vue'

const routes = [
  {
    path: '/',
    name: 'home',
    component: WeatherFitHome
  },
  {
    path: '/search',
    name: 'search',
    component: WeatherFitSearch
  },
  {
    path: '/detail',
    name: 'detail',
    component: WeatherFitDetail
  },
  {
    path: '/outfit',
    name: 'outfit',
    component: WeatherFitOutfit
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router