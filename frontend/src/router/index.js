import { createRouter, createWebHistory } from 'vue-router'
import WeatherFitHome from '../components/WeatherFitHome.vue'
import WeatherFitSearch from '../components/WeatherFitSearch.vue'

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
  }

];

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router