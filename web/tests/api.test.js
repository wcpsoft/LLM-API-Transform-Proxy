import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import axios from 'axios'
import { modelApi, apiKeyApi, routeApi, logApi } from '../src/api/index.js'

// Mock axios for testing
const mockAxios = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn()
}

// Mock successful responses
const mockResponses = {
  models: [
    { id: 1, name: 'gpt-4', provider: 'openai', enabled: true },
    { id: 2, name: 'claude-3', provider: 'anthropic', enabled: true }
  ],
  apiKeys: [
    { id: 1, provider: 'openai', key: 'sk-***', enabled: true },
    { id: 2, provider: 'anthropic', key: 'sk-***', enabled: false }
  ],
  routes: [
    { id: 1, path: '/v1/chat/completions', target: 'openai', enabled: true }
  ],
  logs: [
    { id: 1, method: 'POST', path: '/v1/chat/completions', status: 200, timestamp: '2024-01-01T00:00:00Z' }
  ],
  stats: {
    total_requests: 100,
    success_rate: 0.95,
    avg_response_time: 1200
  }
}

describe('API Tests', () => {
  beforeAll(() => {
    // Setup axios mock
    vi.mock('axios', () => ({
      default: {
        create: () => mockAxios
      }
    }))
  })

  describe('Model API', () => {
    it('should get models with correct endpoint', async () => {
      mockAxios.get.mockResolvedValue(mockResponses.models)
      
      await modelApi.getModels()
      
      expect(mockAxios.get).toHaveBeenCalledWith('/v1/admin/models')
    })

    it('should create model with correct endpoint and data', async () => {
      const modelData = { name: 'gpt-3.5-turbo', provider: 'openai', enabled: true }
      mockAxios.post.mockResolvedValue({ id: 3, ...modelData })
      
      await modelApi.createModel(modelData)
      
      expect(mockAxios.post).toHaveBeenCalledWith('/v1/admin/models', modelData)
    })

    it('should update model with correct endpoint and data', async () => {
      const modelData = { enabled: false }
      mockAxios.put.mockResolvedValue({ id: 1, ...modelData })
      
      await modelApi.updateModel(1, modelData)
      
      expect(mockAxios.put).toHaveBeenCalledWith('/v1/admin/models/1', modelData)
    })

    it('should delete model with correct endpoint', async () => {
      mockAxios.delete.mockResolvedValue({})
      
      await modelApi.deleteModel(1)
      
      expect(mockAxios.delete).toHaveBeenCalledWith('/v1/admin/models/1')
    })
  })

  describe('API Key API', () => {
    it('should get API keys with correct endpoint', async () => {
      mockAxios.get.mockResolvedValue(mockResponses.apiKeys)
      
      await apiKeyApi.getKeys()
      
      expect(mockAxios.get).toHaveBeenCalledWith('/v1/admin/api-keys', { params: {} })
    })

    it('should get API keys with provider filter', async () => {
      mockAxios.get.mockResolvedValue(mockResponses.apiKeys.filter(k => k.provider === 'openai'))
      
      await apiKeyApi.getKeys('openai')
      
      expect(mockAxios.get).toHaveBeenCalledWith('/v1/admin/api-keys', { params: { provider: 'openai' } })
    })

    it('should add API key with correct endpoint and data', async () => {
      const keyData = { provider: 'openai', key: 'sk-test123', enabled: true }
      mockAxios.post.mockResolvedValue({ id: 3, ...keyData })
      
      await apiKeyApi.addKey(keyData)
      
      expect(mockAxios.post).toHaveBeenCalledWith('/v1/admin/api-keys', keyData)
    })

    it('should update key status with correct endpoint and data', async () => {
      mockAxios.patch.mockResolvedValue({})
      
      await apiKeyApi.updateKeyStatus(1, false)
      
      expect(mockAxios.patch).toHaveBeenCalledWith('/v1/admin/api-keys/1/status', { enabled: false })
    })

    it('should delete API key with correct endpoint', async () => {
      mockAxios.delete.mockResolvedValue({})
      
      await apiKeyApi.deleteKey(1)
      
      expect(mockAxios.delete).toHaveBeenCalledWith('/v1/admin/api-keys/1')
    })
  })

  describe('Route API', () => {
    it('should get routes with correct endpoint', async () => {
      mockAxios.get.mockResolvedValue(mockResponses.routes)
      
      await routeApi.getRoutes()
      
      expect(mockAxios.get).toHaveBeenCalledWith('/v1/admin/routes')
    })

    it('should create route with correct endpoint and data', async () => {
      const routeData = { path: '/v1/completions', target: 'anthropic', enabled: true }
      mockAxios.post.mockResolvedValue({ id: 2, ...routeData })
      
      await routeApi.createRoute(routeData)
      
      expect(mockAxios.post).toHaveBeenCalledWith('/v1/admin/routes', routeData)
    })

    it('should update route with correct endpoint and data', async () => {
      const routeData = { enabled: false }
      mockAxios.put.mockResolvedValue({ id: 1, ...routeData })
      
      await routeApi.updateRoute(1, routeData)
      
      expect(mockAxios.put).toHaveBeenCalledWith('/v1/admin/routes/1', routeData)
    })

    it('should delete route with correct endpoint', async () => {
      mockAxios.delete.mockResolvedValue({})
      
      await routeApi.deleteRoute(1)
      
      expect(mockAxios.delete).toHaveBeenCalledWith('/v1/admin/routes/1')
    })
  })

  describe('Log API', () => {
    it('should get logs with correct endpoint', async () => {
      mockAxios.get.mockResolvedValue(mockResponses.logs)
      
      await logApi.getLogs()
      
      expect(mockAxios.get).toHaveBeenCalledWith('/v1/admin/logs', { params: {} })
    })

    it('should get logs with parameters', async () => {
      const params = { limit: 10, offset: 0 }
      mockAxios.get.mockResolvedValue(mockResponses.logs)
      
      await logApi.getLogs(params)
      
      expect(mockAxios.get).toHaveBeenCalledWith('/v1/admin/logs', { params })
    })

    it('should get stats with correct endpoint', async () => {
      mockAxios.get.mockResolvedValue(mockResponses.stats)
      
      await logApi.getStats()
      
      expect(mockAxios.get).toHaveBeenCalledWith('/v1/admin/stats', { params: { days: 7 } })
    })

    it('should get stats with custom days parameter', async () => {
      mockAxios.get.mockResolvedValue(mockResponses.stats)
      
      await logApi.getStats(30)
      
      expect(mockAxios.get).toHaveBeenCalledWith('/v1/admin/stats', { params: { days: 30 } })
    })
  })

  afterAll(() => {
    vi.clearAllMocks()
  })
})