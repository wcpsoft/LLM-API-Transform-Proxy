<template>
  <div class="service-status">
    <div class="status-header">
      <h2>服务状态监控</h2>
      <el-button @click="fetchServiceInfo" :loading="loading" type="primary">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading && !healthStatus" class="loading-container">
      <el-skeleton :rows="5" animated />
    </div>

    <!-- 错误状态 -->
    <el-alert
      v-if="error"
      :title="'服务状态检查失败'"
      :description="error"
      type="error"
      show-icon
      :closable="false"
    >
      <template #default>
        <el-button @click="fetchServiceInfo" type="primary" size="small">
          重试
        </el-button>
      </template>
    </el-alert>

    <!-- 健康检查状态 -->
    <el-card v-if="healthStatus" class="status-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>健康检查</span>
          <el-tag :type="healthStatus.status === 'healthy' ? 'success' : 'danger'">
            {{ healthStatus.status }}
          </el-tag>
        </div>
      </template>
      
      <el-descriptions :column="2" border>
        <el-descriptions-item label="总体状态">
          <el-tag :type="healthStatus.status === 'healthy' ? 'success' : 'danger'">
            {{ healthStatus.status }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="检查时间">
          {{ formatTime(healthStatus.timestamp) }}
        </el-descriptions-item>
        <el-descriptions-item label="版本">
          {{ healthStatus.version }}
        </el-descriptions-item>
      </el-descriptions>
      
      <div v-if="healthStatus.services" class="services-status">
        <h4>服务组件状态</h4>
        <el-row :gutter="16">
          <el-col 
            v-for="(status, service) in healthStatus.services" 
            :key="service" 
            :span="12"
          >
            <el-card class="service-item" shadow="never">
              <div class="service-content">
                <span class="service-name">{{ service }}</span>
                <el-tag :type="status === 'healthy' ? 'success' : 'danger'" size="small">
                  {{ status }}
                </el-tag>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-card>

    <!-- 服务发现信息 -->
    <el-card v-if="discoveryInfo" class="status-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>服务发现</span>
          <el-tag type="info">{{ discoveryInfo.service_name }}</el-tag>
        </div>
      </template>
      
      <el-descriptions :column="2" border>
        <el-descriptions-item label="服务名称">
          {{ discoveryInfo.service_name }}
        </el-descriptions-item>
        <el-descriptions-item label="主机">
          {{ discoveryInfo.host }}
        </el-descriptions-item>
        <el-descriptions-item label="端口">
          {{ discoveryInfo.port }}
        </el-descriptions-item>
        <el-descriptions-item label="发现时间">
          {{ formatTime(discoveryInfo.timestamp) }}
        </el-descriptions-item>
      </el-descriptions>
      
      <div v-if="discoveryInfo.endpoints" class="endpoints">
        <h4>可用端点</h4>
        <el-row :gutter="16">
          <el-col 
            v-for="(url, name) in discoveryInfo.endpoints" 
            :key="name" 
            :span="24"
          >
            <div class="endpoint-item">
              <span class="endpoint-name">{{ name }}:</span>
              <el-link :href="url" target="_blank" type="primary">
                {{ url }}
              </el-link>
            </div>
          </el-col>
        </el-row>
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'ServiceStatus',
  setup() {
    const healthStatus = ref(null)
    const discoveryInfo = ref(null)
    const loading = ref(true)
    const error = ref(null)
    let intervalId = null

    const fetchServiceInfo = async () => {
      try {
        loading.value = true
        error.value = null

        // 获取健康检查信息
        const healthResponse = await fetch('/health')
        if (!healthResponse.ok) {
          throw new Error(`健康检查请求失败: ${healthResponse.status}`)
        }
        const healthData = await healthResponse.json()
        healthStatus.value = healthData

        // 获取服务发现信息
        const discoveryResponse = await fetch('/discovery')
        if (!discoveryResponse.ok) {
          throw new Error(`服务发现请求失败: ${discoveryResponse.status}`)
        }
        const discoveryData = await discoveryResponse.json()
        discoveryInfo.value = discoveryData

        ElMessage.success('服务状态更新成功')
      } catch (err) {
        error.value = err.message
        ElMessage.error(`获取服务状态失败: ${err.message}`)
      } finally {
        loading.value = false
      }
    }

    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleString('zh-CN')
    }

    onMounted(() => {
      fetchServiceInfo()
      // 每30秒刷新一次
      intervalId = setInterval(fetchServiceInfo, 30000)
    })

    onUnmounted(() => {
      if (intervalId) {
        clearInterval(intervalId)
      }
    })

    return {
      healthStatus,
      discoveryInfo,
      loading,
      error,
      fetchServiceInfo,
      formatTime
    }
  }
}
</script>

<style scoped>
.service-status {
  padding: 20px;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.status-header h2 {
  margin: 0;
  color: #303133;
}

.loading-container {
  margin: 20px 0;
}

.status-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.services-status {
  margin-top: 20px;
}

.services-status h4 {
  margin-bottom: 16px;
  color: #606266;
}

.service-item {
  margin-bottom: 8px;
}

.service-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.service-name {
  font-weight: 500;
  color: #303133;
}

.endpoints {
  margin-top: 20px;
}

.endpoints h4 {
  margin-bottom: 16px;
  color: #606266;
}

.endpoint-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  padding: 8px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.endpoint-name {
  font-weight: 500;
  margin-right: 12px;
  min-width: 80px;
  color: #606266;
}
</style>