import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 请求拦截器
api.interceptors.request.use(
  config => {
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
    return api.get('/v1/api-keys/stats')
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

export default api