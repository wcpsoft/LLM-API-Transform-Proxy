<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon total-requests">
              <el-icon><DataAnalysis /></el-icon>
            </div>
            <div class="stat-info">
              <h3>{{ stats.totalRequests }}</h3>
              <p>总请求数</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon active-models">
              <el-icon><Setting /></el-icon>
            </div>
            <div class="stat-info">
              <h3>{{ stats.activeModels }}</h3>
              <p>活跃模型</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon api-keys">
              <el-icon><Key /></el-icon>
            </div>
            <div class="stat-info">
              <h3>{{ stats.activeApiKeys }}</h3>
              <p>活跃密钥</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon success-rate">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <h3>{{ stats.successRate }}%</h3>
              <p>成功率</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近7天请求趋势</span>
            </div>
          </template>
          <div class="chart-container">
            <div v-if="dailyRequests.length === 0" class="no-data">
              <el-empty description="暂无数据" />
            </div>
            <div v-else class="simple-chart">
              <div 
                v-for="(item, index) in dailyRequests" 
                :key="index"
                class="chart-bar"
                :style="{ height: getBarHeight(item.requests) + 'px' }"
                :title="`${item.date}: ${item.requests} 请求`"
              >
                <div class="bar-value">{{ item.requests }}</div>
              </div>
              <div class="chart-labels">
                <span v-for="(item, index) in dailyRequests" :key="index" class="chart-label">
                  {{ formatDate(item.date) }}
                </span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>提供商分布</span>
            </div>
          </template>
          <div class="provider-stats">
            <div v-if="providerStats.length === 0" class="no-data">
              <el-empty description="暂无数据" />
            </div>
            <div v-else>
              <div v-for="provider in providerStats" :key="provider.provider" class="provider-item">
                <div class="provider-info">
                  <span class="provider-name">{{ provider.provider }}</span>
                  <span class="provider-count">{{ provider.active_keys }}/{{ provider.total_keys }}</span>
                </div>
                <el-progress 
                  :percentage="getProviderPercentage(provider)" 
                  :show-text="false"
                  :stroke-width="8"
                />
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近活动 -->
    <el-row>
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近请求日志</span>
              <el-button link @click="$router.push('/logs')">
                查看全部
              </el-button>
            </div>
          </template>
          <el-table :data="recentLogs" style="width: 100%" v-loading="loading">
            <el-table-column prop="timestamp" label="时间" width="180">
              <template #default="scope">
                {{ formatDateTime(scope.row.timestamp) }}
              </template>
            </el-table-column>
            <el-table-column prop="source_model" label="源模型" width="150" />
            <el-table-column prop="target_model" label="目标模型" width="150" />
            <el-table-column prop="source_api" label="源API" width="200" show-overflow-tooltip />
            <el-table-column prop="target_api" label="目标API" width="200" show-overflow-tooltip />
            <el-table-column label="状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.target_response ? 'success' : 'danger'">
                  {{ scope.row.target_response ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { logApi, apiKeyApi } from '@/api'
import dayjs from 'dayjs'

export default {
  name: 'Dashboard',
  setup() {
    const loading = ref(false)
    const stats = ref({
      totalRequests: 0,
      activeModels: 0,
      activeApiKeys: 0,
      successRate: 0
    })
    const dailyRequests = ref([])
    const providerStats = ref([])
    const recentLogs = ref([])

    const loadDashboardData = async () => {
      loading.value = true
      try {
        // 加载统计数据
        const [statsData, keyStats, logsData] = await Promise.all([
          logApi.getStats(7),
          apiKeyApi.getStats(),
          logApi.getLogs({ limit: 10 })
        ])

        // 处理统计数据
        if (statsData.daily_requests) {
          dailyRequests.value = statsData.daily_requests
          stats.value.totalRequests = statsData.daily_requests.reduce((sum, item) => sum + item.requests, 0)
        }

        if (statsData.provider_stats) {
          providerStats.value = statsData.provider_stats
          stats.value.activeApiKeys = statsData.provider_stats.reduce((sum, item) => sum + item.active_keys, 0)
        }

        // 处理密钥统计
        if (keyStats) {
          const totalRequests = Object.values(keyStats).reduce((sum, provider) => {
            return sum + Object.values(provider).reduce((pSum, key) => pSum + (key.requests || 0), 0)
          }, 0)
          const successRequests = Object.values(keyStats).reduce((sum, provider) => {
            return sum + Object.values(provider).reduce((pSum, key) => pSum + (key.success || 0), 0)
          }, 0)
          stats.value.successRate = totalRequests > 0 ? Math.round((successRequests / totalRequests) * 100) : 0
        }

        // 处理日志数据
        if (logsData && Array.isArray(logsData)) {
          recentLogs.value = logsData
        }

        // 模拟活跃模型数
        stats.value.activeModels = 5
      } catch (error) {
        console.error('加载仪表盘数据失败:', error)
      } finally {
        loading.value = false
      }
    }

    const getBarHeight = (requests) => {
      const maxRequests = Math.max(...dailyRequests.value.map(item => item.requests))
      return maxRequests > 0 ? Math.max((requests / maxRequests) * 150, 10) : 10
    }

    const getProviderPercentage = (provider) => {
      return provider.total_keys > 0 ? Math.round((provider.active_keys / provider.total_keys) * 100) : 0
    }

    const formatDate = (date) => {
      return dayjs(date).format('MM/DD')
    }

    const formatDateTime = (datetime) => {
      return dayjs(datetime).format('YYYY-MM-DD HH:mm:ss')
    }

    onMounted(() => {
      loadDashboardData()
    })

    return {
      loading,
      stats,
      dailyRequests,
      providerStats,
      recentLogs,
      getBarHeight,
      getProviderPercentage,
      formatDate,
      formatDateTime
    }
  }
}
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stats-row {
  margin-bottom: 20px;
}

.charts-row {
  margin-bottom: 20px;
}

.stat-card {
  height: 120px;
}

.stat-content {
  display: flex;
  align-items: center;
  height: 100%;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
  font-size: 24px;
  color: white;
}

.stat-icon.total-requests {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.stat-icon.active-models {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.stat-icon.api-keys {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.stat-icon.success-rate {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.stat-info h3 {
  margin: 0;
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-info p {
  margin: 5px 0 0 0;
  color: #909399;
  font-size: 14px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  height: 200px;
  display: flex;
  flex-direction: column;
}

.simple-chart {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chart-bar {
  display: inline-block;
  width: calc(100% / 7 - 10px);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  margin: 0 5px;
  border-radius: 4px 4px 0 0;
  position: relative;
  align-self: flex-end;
  transition: all 0.3s ease;
}

.chart-bar:hover {
  opacity: 0.8;
}

.bar-value {
  position: absolute;
  top: -25px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: #303133;
  font-weight: bold;
}

.chart-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
}

.chart-label {
  font-size: 12px;
  color: #909399;
  text-align: center;
  flex: 1;
}

.provider-stats {
  height: 200px;
  overflow-y: auto;
}

.provider-item {
  margin-bottom: 20px;
}

.provider-info {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.provider-name {
  font-weight: bold;
  color: #303133;
}

.provider-count {
  color: #909399;
  font-size: 14px;
}

.no-data {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>