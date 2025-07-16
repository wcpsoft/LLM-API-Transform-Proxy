import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Models from '@/views/Models.vue'
import ApiKeys from '@/views/ApiKeys.vue'
import Routes from '@/views/Routes.vue'
import Logs from '@/views/Logs.vue'
import ServiceStatus from '@/views/ServiceStatus.vue'
import Login from '@/views/Login.vue'
import Layout from '@/components/Layout.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 检查用户是否已登录
function isAuthenticated() {
  const token = localStorage.getItem('auth_token')
  return !!token
}

// 路由守卫
router.beforeEach((to, from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const isLoggedIn = isAuthenticated()

  if (requiresAuth && !isLoggedIn) {
    // 需要认证但未登录，重定向到登录页
    next('/login')
  } else if (to.path === '/login' && isLoggedIn) {
    // 已登录用户访问登录页，重定向到仪表板
    next('/dashboard')
  } else if (to.path === '/' && isLoggedIn) {
    // 已登录用户访问根路径，重定向到仪表板
    next('/dashboard')
  } else if (to.path === '/' && !isLoggedIn) {
    // 未登录用户访问根路径，重定向到登录页
    next('/login')
  } else {
    next()
  }
})

export default router