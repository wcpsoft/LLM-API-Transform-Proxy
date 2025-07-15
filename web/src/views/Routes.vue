<template>
  <div class="routes-page">
    <!-- 操作栏 -->
    <div class="toolbar">
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        添加路由
      </el-button>
      <el-button @click="loadRoutes">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 路由表格 -->
    <el-card>
      <el-table :data="routes" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="path" label="路径" width="300" />
        <el-table-column prop="method" label="方法" width="100">
          <template #default="scope">
            <el-tag :type="getMethodTagType(scope.row.method)">
              {{ scope.row.method }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="enabled" label="状态" width="100">
          <template #default="scope">
            <el-switch
              v-model="scope.row.enabled"
              @change="toggleRouteStatus(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="scope">
            <el-button link size="small" @click="editRoute(scope.row)">
              编辑
            </el-button>
            <el-button link size="small" @click="deleteRoute(scope.row)" class="danger">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      :title="editingRoute ? '编辑路由' : '创建路由'"
      v-model="showCreateDialog"
      width="500px"
      @close="resetForm"
    >
      <el-form :model="routeForm" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="路径" prop="path">
          <el-input v-model="routeForm.path" placeholder="例如: /v1/chat/completions" />
        </el-form-item>
        <el-form-item label="方法" prop="method">
          <el-select v-model="routeForm.method" placeholder="选择HTTP方法" style="width: 100%">
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
            <el-option label="PUT" value="PUT" />
            <el-option label="DELETE" value="DELETE" />
            <el-option label="PATCH" value="PATCH" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="routeForm.description" type="textarea" placeholder="路由描述" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="routeForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" @click="saveRoute" :loading="saving">
            {{ editingRoute ? '更新' : '创建' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { routeApi } from '@/api'
import dayjs from 'dayjs'

export default {
  name: 'Routes',
  setup() {
    const loading = ref(false)
    const saving = ref(false)
    const showCreateDialog = ref(false)
    const editingRoute = ref(null)
    const routes = ref([])
    const formRef = ref()

    const routeForm = reactive({
      path: '',
      method: 'POST',
      description: '',
      enabled: true
    })

    const formRules = {
      path: [
        { required: true, message: '请输入路径', trigger: 'blur' },
        { pattern: /^\//, message: '路径必须以 / 开头', trigger: 'blur' }
      ],
      method: [
        { required: true, message: '请选择HTTP方法', trigger: 'change' }
      ]
    }

    const loadRoutes = async () => {
      loading.value = true
      try {
        const data = await routeApi.getRoutes()
        routes.value = Array.isArray(data) ? data : []
      } catch (error) {
        console.error('加载路由失败:', error)
        ElMessage.error('加载路由失败')
      } finally {
        loading.value = false
      }
    }

    const saveRoute = async () => {
      if (!formRef.value) return
      
      try {
        await formRef.value.validate()
        saving.value = true

        if (editingRoute.value) {
          await routeApi.updateRoute(editingRoute.value.id, routeForm)
          ElMessage.success('路由更新成功')
        } else {
          await routeApi.createRoute(routeForm)
          ElMessage.success('路由创建成功')
        }

        showCreateDialog.value = false
        await loadRoutes()
      } catch (error) {
        console.error('保存路由失败:', error)
        ElMessage.error('保存路由失败')
      } finally {
        saving.value = false
      }
    }

    const editRoute = (route) => {
      editingRoute.value = route
      Object.assign(routeForm, {
        path: route.path,
        method: route.method,
        description: route.description || '',
        enabled: route.enabled
      })
      showCreateDialog.value = true
    }

    const deleteRoute = async (route) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除路由 "${route.path}" 吗？`,
          '确认删除',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await routeApi.deleteRoute(route.id)
        ElMessage.success('路由删除成功')
        await loadRoutes()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除路由失败:', error)
          ElMessage.error('删除路由失败')
        }
      }
    }

    const toggleRouteStatus = async (route) => {
      try {
        await routeApi.updateRoute(route.id, { ...route, enabled: route.enabled })
        ElMessage.success(`路由已${route.enabled ? '启用' : '禁用'}`)
      } catch (error) {
        console.error('更新路由状态失败:', error)
        ElMessage.error('更新路由状态失败')
        // 回滚状态
        route.enabled = !route.enabled
      }
    }

    const resetForm = () => {
      editingRoute.value = null
      Object.assign(routeForm, {
        path: '',
        method: 'POST',
        description: '',
        enabled: true
      })
      if (formRef.value) {
        formRef.value.resetFields()
      }
    }

    const getMethodTagType = (method) => {
      const types = {
        GET: 'success',
        POST: 'primary',
        PUT: 'warning',
        DELETE: 'danger',
        PATCH: 'info'
      }
      return types[method] || 'default'
    }

    const formatDateTime = (datetime) => {
      return datetime ? dayjs(datetime).format('YYYY-MM-DD HH:mm:ss') : '-'
    }

    onMounted(() => {
      loadRoutes()
    })

    return {
      loading,
      saving,
      showCreateDialog,
      editingRoute,
      routes,
      routeForm,
      formRules,
      formRef,
      loadRoutes,
      saveRoute,
      editRoute,
      deleteRoute,
      toggleRouteStatus,
      resetForm,
      getMethodTagType,
      formatDateTime
    }
  }
}
</script>

<style scoped>
.routes-page {
  padding: 0;
}

.toolbar {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
}

.danger {
  color: #f56c6c;
}

.danger:hover {
  color: #f78989;
}
</style>