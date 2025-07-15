import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Models from '@/views/Models.vue'
import ApiKeys from '@/views/ApiKeys.vue'
import Routes from '@/views/Routes.vue'
import Logs from '@/views/Logs.vue'
import ServiceStatus from '@/views/ServiceStatus.vue'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/models',
    name: 'Models',
    component: Models
  },
  {
    path: '/api-keys',
    name: 'ApiKeys',
    component: ApiKeys
  },
  {
    path: '/routes',
    name: 'Routes',
    component: Routes
  },
  {
    path: '/logs',
    name: 'Logs',
    component: Logs
  },
  {
    path: '/service-status',
    name: 'ServiceStatus',
    component: ServiceStatus
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router