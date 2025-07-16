import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 认证管理
const AUTH_KEY = 'admin_auth_key'
const USER_TOKEN_KEY = 'auth_token'

// 获取存储的认证密钥
function getAdminKey() {
  return localStorage.getItem(AUTH_KEY) || 'admin123'
}

// 设置认证密钥
function setAdminKey(key) {
  localStorage.setItem(AUTH_KEY, key)
}

// 获取用户认证token
function getUserToken() {
  return localStorage.getItem(USER_TOKEN_KEY)
}

// 设置用户认证token
function setUserToken(token) {
  localStorage.setItem(USER_TOKEN_KEY, token)
}

// 清除用户认证信息
function clearUserAuth() {
  localStorage.removeItem(USER_TOKEN_KEY)
  localStorage.removeItem('user_info')
}

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 为管理员API添加认证头
    if (config.url && config.url.includes('/v1/admin/')) {
      config.headers['X-Admin-Key'] = getAdminKey()
    }
    
    // 为用户认证API添加Bearer token
    const userToken = getUserToken()
    if (userToken && !config.url?.includes('/v1/auth/login')) {
      config.headers.Authorization = `Bearer ${userToken}`
    }
    
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    // 处理401未授权错误
    if (error.response?.status === 401) {
      clearUserAuth()
      // 动态导入router避免循环依赖
      import('@/router').then(({ default: router }) => {
        if (router.currentRoute.value.path !== '/login') {
          router.push('/login')
        }
      })
    }
    
    const message = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// 模型配置API
export const modelApi = {
  // 获取所有模型配置
  getModels() {
    return api.get('/v1/admin/models')
  },
  
  // 创建模型配置
  createModel(data) {
    return api.post('/v1/admin/models', data)
  },
  
  // 更新模型配置
  updateModel(id, data) {
    return api.put(`/v1/admin/models/${id}`, data)
  },
  
  // 删除模型配置
  deleteModel(id) {
    return api.delete(`/v1/admin/models/${id}`)
  }
}

// API密钥管理API
export const apiKeyApi = {
  // 获取密钥统计
  getStats() {
    return api.get('/v1/admin/api-keys/stats')
  },
  
  // 获取密钥列表
  getKeys(provider) {
    const params = provider ? { provider } : {}
    return api.get('/v1/admin/api-keys', { params })
  },
  
  // 添加密钥
  addKey(data) {
    return api.post('/v1/admin/api-keys', data)
  },
  
  // 删除密钥
  deleteKey(id) {
    return api.delete(`/v1/admin/api-keys/${id}`)
  },
  
  // 更新密钥状态
  updateKeyStatus(id, isActive) {
    return api.patch(`/v1/admin/api-keys/${id}/status`, { enabled: isActive })
  }
}

// 路由管理API
export const routeApi = {
  // 获取所有路由
  getRoutes() {
    return api.get('/v1/admin/routes')
  },
  
  // 创建路由
  createRoute(data) {
    return api.post('/v1/admin/routes', data)
  },
  
  // 更新路由
  updateRoute(id, data) {
    return api.put(`/v1/admin/routes/${id}`, data)
  },
  
  // 删除路由
  deleteRoute(id) {
    return api.delete(`/v1/admin/routes/${id}`)
  }
}

// 日志API
export const logApi = {
  // 获取请求日志
  getLogs(params = {}) {
    return api.get('/v1/admin/logs', { params })
  },
  
  // 获取统计数据
  getStats(days = 7) {
    return api.get('/v1/admin/stats', { params: { days } })
  }
}

// 用户认证API
export const authApi = {
  // 用户登录
  login(data) {
    return api.post('/v1/auth/login', data)
  },
  
  // 用户退出
  logout() {
    return api.post('/v1/auth/logout')
  },
  
  // 获取用户资料
  getProfile() {
    return api.get('/v1/auth/profile')
  },
  
  // 验证token
  validateToken() {
    return api.get('/v1/auth/validate')
  },
  
  // 修改密码
  changePassword(data) {
    return api.post('/v1/auth/change-password', data)
  }
}

// 导出认证管理函数
export { getAdminKey, setAdminKey, getUserToken, setUserToken, clearUserAuth }

export default api