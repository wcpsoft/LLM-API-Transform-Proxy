<template>
  <div class="logs-page">
    <!-- 筛选栏 -->
    <el-card class="filter-card">
      <el-form :model="filters" inline>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="filters.dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            format="YYYY-MM-DD HH:mm:ss"
            value-format="YYYY-MM-DD HH:mm:ss"
            @change="loadLogs"
          />
        </el-form-item>
        <el-form-item label="源模型">
          <el-input v-model="filters.sourceModel" placeholder="筛选源模型" clearable @change="loadLogs" />
        </el-form-item>
        <el-form-item label="目标模型">
          <el-input v-model="filters.targetModel" placeholder="筛选目标模型" clearable @change="loadLogs" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="筛选状态" clearable @change="loadLogs">
            <el-option label="全部" value="" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="error" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadLogs">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetFilters">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 日志表格 -->
    <el-card>
      <el-table :data="logs" v-loading="loading" style="width: 100%" @expand-change="handleExpand">
        <el-table-column type="expand">
          <template #default="props">
            <div class="log-detail">
              <el-row :gutter="20">
                <el-col :span="12">
                  <h4>请求信息</h4>
                  <div class="detail-item">
                    <strong>源API:</strong>
                    <code>{{ props.row.source_api }}</code>
                  </div>
                  <div class="detail-item">
                    <strong>目标API:</strong>
                    <code>{{ props.row.target_api }}</code>
                  </div>
                  <div class="detail-item">
                    <strong>请求头:</strong>
                    <pre>{{ formatJson(props.row.headers) }}</pre>
                  </div>
                  <div class="detail-item">
                    <strong>源参数:</strong>
                    <pre>{{ formatJson(props.row.source_params) }}</pre>
                  </div>
                  <div class="detail-item">
                    <strong>目标参数:</strong>
                    <pre>{{ formatJson(props.row.target_params) }}</pre>
                  </div>
                </el-col>
                <el-col :span="12">
                  <h4>响应信息</h4>
                  <div class="detail-item">
                    <strong>源响应:</strong>
                    <pre>{{ formatJson(props.row.source_response) }}</pre>
                  </div>
                  <div class="detail-item">
                    <strong>目标响应:</strong>
                    <pre>{{ formatJson(props.row.target_response) }}</pre>
                  </div>
                </el-col>
              </el-row>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="id" label="ID" width="80" />
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
            <el-tag :type="getStatusTagType(scope.row)">
              {{ getStatusText(scope.row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="100">
          <template #default="scope">
            {{ calculateDuration(scope.row) }}
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadLogs"
          @current-change="loadLogs"
        />
      </div>
    </el-card>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { logApi } from '@/api'
import dayjs from 'dayjs'

export default {
  name: 'Logs',
  setup() {
    const loading = ref(false)
    const logs = ref([])
    
    const filters = reactive({
      dateRange: [],
      sourceModel: '',
      targetModel: '',
      status: ''
    })

    const pagination = reactive({
      page: 1,
      size: 20,
      total: 0
    })

    const loadLogs = async () => {
      loading.value = true
      try {
        const params = {
          page: pagination.page,
          size: pagination.size
        }

        // 添加筛选条件
        if (filters.dateRange && filters.dateRange.length === 2) {
          params.start_time = filters.dateRange[0]
          params.end_time = filters.dateRange[1]
        }
        if (filters.sourceModel) {
          params.source_model = filters.sourceModel
        }
        if (filters.targetModel) {
          params.target_model = filters.targetModel
        }
        if (filters.status) {
          params.status = filters.status
        }

        const data = await logApi.getLogs(params)
        
        if (data && typeof data === 'object') {
          logs.value = Array.isArray(data.items) ? data.items : Array.isArray(data) ? data : []
          pagination.total = data.total || logs.value.length
        } else {
          logs.value = []
          pagination.total = 0
        }
      } catch (error) {
        console.error('加载日志失败:', error)
        ElMessage.error('加载日志失败')
        logs.value = []
        pagination.total = 0
      } finally {
        loading.value = false
      }
    }

    const resetFilters = () => {
      Object.assign(filters, {
        dateRange: [],
        sourceModel: '',
        targetModel: '',
        status: ''
      })
      pagination.page = 1
      loadLogs()
    }

    const handleExpand = (row, expandedRows) => {
      // 可以在这里加载详细信息
    }

    const formatDateTime = (datetime) => {
      return datetime ? dayjs(datetime).format('YYYY-MM-DD HH:mm:ss') : '-'
    }

    const formatJson = (jsonStr) => {
      if (!jsonStr) return ''
      try {
        if (typeof jsonStr === 'string') {
          return JSON.stringify(JSON.parse(jsonStr), null, 2)
        } else {
          return JSON.stringify(jsonStr, null, 2)
        }
      } catch (error) {
        return jsonStr
      }
    }

    const getStatusTagType = (row) => {
      if (row.target_response) {
        try {
          const response = typeof row.target_response === 'string' 
            ? JSON.parse(row.target_response) 
            : row.target_response
          if (response.error) {
            return 'danger'
          }
          return 'success'
        } catch {
          return 'success'
        }
      }
      return 'danger'
    }

    const getStatusText = (row) => {
      if (row.target_response) {
        try {
          const response = typeof row.target_response === 'string' 
            ? JSON.parse(row.target_response) 
            : row.target_response
          if (response.error) {
            return '错误'
          }
          return '成功'
        } catch {
          return '成功'
        }
      }
      return '失败'
    }

    const calculateDuration = (row) => {
      // 这里可以根据实际情况计算请求耗时
      // 目前返回模拟数据
      return Math.floor(Math.random() * 1000) + 'ms'
    }

    onMounted(() => {
      // 设置默认时间范围为最近24小时
      const now = dayjs()
      const yesterday = now.subtract(1, 'day')
      filters.dateRange = [
        yesterday.format('YYYY-MM-DD HH:mm:ss'),
        now.format('YYYY-MM-DD HH:mm:ss')
      ]
      loadLogs()
    })

    return {
      loading,
      logs,
      filters,
      pagination,
      loadLogs,
      resetFilters,
      handleExpand,
      formatDateTime,
      formatJson,
      getStatusTagType,
      getStatusText,
      calculateDuration
    }
  }
}
</script>

<style scoped>
.logs-page {
  padding: 0;
}

.filter-card {
  margin-bottom: 20px;
}

.log-detail {
  padding: 20px;
  background-color: #f8f9fa;
}

.detail-item {
  margin-bottom: 15px;
}

.detail-item strong {
  display: block;
  margin-bottom: 5px;
  color: #303133;
}

.detail-item code {
  background-color: #e6effb;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
}

.detail-item pre {
  background-color: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.pagination-container {
  margin-top: 20px;
  text-align: right;
}

h4 {
  color: #409EFF;
  margin-bottom: 15px;
  border-bottom: 2px solid #409EFF;
  padding-bottom: 5px;
}
</style>