<template>
  <div class="api-keys-page">
    <!-- 操作栏 -->
    <div class="toolbar">
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        添加API密钥
      </el-button>
      <el-button @click="loadApiKeys">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
      <el-select v-model="selectedProvider" placeholder="筛选提供商" style="width: 150px; margin-left: 10px" @change="loadApiKeys">
        <el-option label="全部" value="" />
        <el-option label="OpenAI" value="openai" />
        <el-option label="Anthropic" value="anthropic" />
        <el-option label="Google" value="google" />
      </el-select>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number">{{ totalKeys }}</div>
            <div class="stat-label">总密钥数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number">{{ activeKeys }}</div>
            <div class="stat-label">活跃密钥</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number">{{ totalRequests }}</div>
            <div class="stat-label">总请求数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-number">{{ successRate }}%</div>
            <div class="stat-label">成功率</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- API密钥表格 -->
    <el-card>
      <el-table :data="apiKeys" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="provider" label="提供商" width="120">
          <template #default="scope">
            <el-tag :type="getProviderTagType(scope.row.provider)">
              {{ scope.row.provider }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="api_key" label="API密钥" width="200">
          <template #default="scope">
            <span class="masked-key">{{ maskApiKey(scope.row.api_key) }}</span>
            <el-button link size="small" @click="copyApiKey(scope.row.api_key)">
              <el-icon><CopyDocument /></el-icon>
            </el-button>
          </template>
        </el-table-column>
        <el-table-column prop="auth_header" label="认证头" width="120" />
        <el-table-column prop="requests_count" label="请求数" width="100" />
        <el-table-column prop="success_count" label="成功数" width="100" />
        <el-table-column label="成功率" width="100">
          <template #default="scope">
            {{ getSuccessRate(scope.row) }}%
          </template>
        </el-table-column>
        <el-table-column prop="last_used_at" label="最后使用" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.last_used_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="scope">
            <el-switch
              v-model="scope.row.is_active"
              @change="toggleKeyStatus(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-button link size="small" @click="deleteApiKey(scope.row)" class="danger">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加密钥对话框 -->
    <el-dialog
      title="添加API密钥"
      v-model="showAddDialog"
      width="500px"
      @close="resetForm"
    >
      <el-form :model="keyForm" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="提供商" prop="provider">
          <el-select v-model="keyForm.provider" placeholder="选择提供商" style="width: 100%">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Anthropic" value="anthropic" />
            <el-option label="Google" value="google" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="API密钥" prop="api_key">
          <el-input v-model="keyForm.api_key" placeholder="输入API密钥" show-password />
        </el-form-item>
        <el-form-item label="认证头">
          <el-input v-model="keyForm.auth_header" placeholder="默认: Authorization" />
        </el-form-item>
        <el-form-item label="认证格式">
          <el-input v-model="keyForm.auth_format" placeholder="默认: Bearer {key}" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="keyForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddDialog = false">取消</el-button>
          <el-button type="primary" @click="addApiKey" :loading="saving">
            添加
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiKeyApi } from '@/api'
import dayjs from 'dayjs'

export default {
  name: 'ApiKeys',
  setup() {
    const loading = ref(false)
    const saving = ref(false)
    const showAddDialog = ref(false)
    const selectedProvider = ref('')
    const apiKeys = ref([])
    const keyStats = ref({})
    const formRef = ref()

    const keyForm = reactive({
      provider: '',
      api_key: '',
      auth_header: 'Authorization',
      auth_format: 'Bearer {key}',
      is_active: true
    })

    const formRules = {
      provider: [
        { required: true, message: '请选择提供商', trigger: 'change' }
      ],
      api_key: [
        { required: true, message: '请输入API密钥', trigger: 'blur' }
      ]
    }

    // 计算统计数据
    const totalKeys = computed(() => apiKeys.value.length || 0)
    const activeKeys = computed(() => apiKeys.value.filter(key => key.is_active).length || 0)
    const totalRequests = computed(() => {
      return apiKeys.value.reduce((sum, key) => {
        const requests = Number(key.requests_count) || 0
        return sum + requests
      }, 0)
    })
    const successRate = computed(() => {
      const total = totalRequests.value
      const success = apiKeys.value.reduce((sum, key) => {
        const successCount = Number(key.success_count) || 0
        return sum + successCount
      }, 0)
      return total > 0 ? Math.round((success / total) * 100) : 0
    })

    const loadApiKeys = async () => {
      loading.value = true
      try {
        const data = await apiKeyApi.getKeys(selectedProvider.value)
        apiKeys.value = Array.isArray(data) ? data : []
      } catch (error) {
        console.error('加载API密钥失败:', error)
        ElMessage.error('加载API密钥失败')
      } finally {
        loading.value = false
      }
    }

    const loadStats = async () => {
      try {
        const data = await apiKeyApi.getStats()
        keyStats.value = data || {}
      } catch (error) {
        console.error('加载统计数据失败:', error)
      }
    }

    const addApiKey = async () => {
      if (!formRef.value) return
      
      try {
        await formRef.value.validate()
        saving.value = true

        await apiKeyApi.addKey(keyForm)
        ElMessage.success('API密钥添加成功')
        showAddDialog.value = false
        await loadApiKeys()
      } catch (error) {
        console.error('添加API密钥失败:', error)
        ElMessage.error('添加API密钥失败')
      } finally {
        saving.value = false
      }
    }

    const deleteApiKey = async (key) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除这个API密钥吗？`,
          '确认删除',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await apiKeyApi.deleteKey(key.id)
        ElMessage.success('API密钥删除成功')
        await loadApiKeys()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除API密钥失败:', error)
          ElMessage.error('删除API密钥失败')
        }
      }
    }

    const toggleKeyStatus = async (key) => {
      try {
        await apiKeyApi.updateKeyStatus(key.id, key.is_active)
        ElMessage.success(`API密钥已${key.is_active ? '启用' : '禁用'}`)
      } catch (error) {
        console.error('更新密钥状态失败:', error)
        ElMessage.error('更新密钥状态失败')
        // 回滚状态
        key.is_active = !key.is_active
      }
    }

    const resetForm = () => {
      Object.assign(keyForm, {
        provider: '',
        api_key: '',
        auth_header: 'Authorization',
        auth_format: 'Bearer {key}',
        is_active: true
      })
      if (formRef.value) {
        formRef.value.resetFields()
      }
    }

    const maskApiKey = (key) => {
      if (!key) return ''
      if (key.length <= 10) return key
      return key.substring(0, 8) + '...' + key.substring(key.length - 4)
    }

    const copyApiKey = async (key) => {
      try {
        await navigator.clipboard.writeText(key)
        ElMessage.success('API密钥已复制到剪贴板')
      } catch (error) {
        ElMessage.error('复制失败')
      }
    }

    const getProviderTagType = (provider) => {
      const types = {
        openai: 'success',
        anthropic: 'warning',
        google: 'info',
        other: 'default'
      }
      return types[provider] || 'default'
    }

    const getSuccessRate = (key) => {
      const requests = Number(key.requests_count) || 0
      const success = Number(key.success_count) || 0
      if (requests === 0) return 0
      return Math.round((success / requests) * 100)
    }

    const formatDateTime = (datetime) => {
      return datetime ? dayjs(datetime).format('YYYY-MM-DD HH:mm:ss') : '从未使用'
    }

    onMounted(() => {
      loadApiKeys()
      loadStats()
    })

    return {
      loading,
      saving,
      showAddDialog,
      selectedProvider,
      apiKeys,
      keyForm,
      formRules,
      formRef,
      totalKeys,
      activeKeys,
      totalRequests,
      successRate,
      loadApiKeys,
      addApiKey,
      deleteApiKey,
      toggleKeyStatus,
      resetForm,
      maskApiKey,
      copyApiKey,
      getProviderTagType,
      getSuccessRate,
      formatDateTime
    }
  }
}
</script>

<style scoped>
.api-keys-page {
  padding: 0;
}

.toolbar {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  padding: 20px;
}

.stat-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-number {
  font-size: 32px;
  font-weight: bold;
  color: #409EFF;
  margin-bottom: 8px;
}

.stat-label {
  color: #909399;
  font-size: 14px;
}

.masked-key {
  font-family: monospace;
  margin-right: 8px;
}

.danger {
  color: #f56c6c;
}

.danger:hover {
  color: #f78989;
}
</style>