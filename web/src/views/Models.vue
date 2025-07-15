<template>
  <div class="models-page">
    <!-- 操作栏 -->
    <div class="toolbar">
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        添加模型配置
      </el-button>
      <el-button @click="loadModels">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 模型配置表格 -->
    <el-card>
      <el-table :data="models" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="route_key" label="路由键" width="150" />
        <el-table-column prop="target_model" label="目标模型" width="200" />
        <el-table-column prop="provider" label="提供商" width="120">
          <template #default="scope">
            <el-tag :type="getProviderTagType(scope.row.provider)">
              {{ scope.row.provider }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="prompt_keywords" label="关键词" width="150" show-overflow-tooltip />
        <el-table-column prop="api_base" label="API Base" width="200" show-overflow-tooltip />
        <el-table-column prop="enabled" label="状态" width="100">
          <template #default="scope">
            <el-switch
              v-model="scope.row.enabled"
              @change="toggleModelStatus(scope.row)"
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
            <el-button link size="small" @click="editModel(scope.row)">
              编辑
            </el-button>
            <el-button link size="small" @click="deleteModel(scope.row)" class="danger">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      :title="editingModel ? '编辑模型配置' : '创建模型配置'"
      v-model="showCreateDialog"
      width="600px"
      @close="resetForm"
    >
      <el-form :model="modelForm" :rules="formRules" ref="formRef" label-width="120px">
        <el-form-item label="路由键" prop="route_key">
          <el-input v-model="modelForm.route_key" placeholder="例如: gpt-4" />
        </el-form-item>
        <el-form-item label="目标模型" prop="target_model">
          <el-input v-model="modelForm.target_model" placeholder="例如: gpt-4-turbo" />
        </el-form-item>
        <el-form-item label="提供商" prop="provider">
          <el-select v-model="modelForm.provider" placeholder="选择提供商" style="width: 100%">
            <el-option label="OpenAI" value="openai" />
            <el-option label="Anthropic" value="anthropic" />
            <el-option label="Google" value="google" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="modelForm.prompt_keywords" placeholder="用于匹配的关键词，可选" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="modelForm.description" type="textarea" placeholder="模型描述" />
        </el-form-item>
        <el-form-item label="API密钥">
          <el-input v-model="modelForm.api_key" placeholder="API密钥，可选" show-password />
        </el-form-item>
        <el-form-item label="API Base">
          <el-input v-model="modelForm.api_base" placeholder="自定义API基础URL，可选" />
        </el-form-item>
        <el-form-item label="认证头">
          <el-input v-model="modelForm.auth_header" placeholder="默认: Authorization" />
        </el-form-item>
        <el-form-item label="认证格式">
          <el-input v-model="modelForm.auth_format" placeholder="默认: Bearer {key}" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="modelForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" @click="saveModel" :loading="saving">
            {{ editingModel ? '更新' : '创建' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { modelApi } from '@/api'
import dayjs from 'dayjs'

export default {
  name: 'Models',
  setup() {
    const loading = ref(false)
    const saving = ref(false)
    const showCreateDialog = ref(false)
    const editingModel = ref(null)
    const models = ref([])
    const formRef = ref()

    const modelForm = reactive({
      route_key: '',
      target_model: '',
      provider: '',
      prompt_keywords: '',
      description: '',
      api_key: '',
      api_base: '',
      auth_header: 'Authorization',
      auth_format: 'Bearer {key}',
      enabled: true
    })

    const formRules = {
      route_key: [
        { required: true, message: '请输入路由键', trigger: 'blur' }
      ],
      target_model: [
        { required: true, message: '请输入目标模型', trigger: 'blur' }
      ],
      provider: [
        { required: true, message: '请选择提供商', trigger: 'change' }
      ]
    }

    const loadModels = async () => {
      loading.value = true
      try {
        const data = await modelApi.getModels()
        models.value = Array.isArray(data) ? data : []
      } catch (error) {
        console.error('加载模型配置失败:', error)
        ElMessage.error('加载模型配置失败')
      } finally {
        loading.value = false
      }
    }

    const saveModel = async () => {
      if (!formRef.value) return
      
      try {
        await formRef.value.validate()
        saving.value = true

        if (editingModel.value) {
          await modelApi.updateModel(editingModel.value.id, modelForm)
          ElMessage.success('模型配置更新成功')
        } else {
          await modelApi.createModel(modelForm)
          ElMessage.success('模型配置创建成功')
        }

        showCreateDialog.value = false
        await loadModels()
      } catch (error) {
        console.error('保存模型配置失败:', error)
        ElMessage.error('保存模型配置失败')
      } finally {
        saving.value = false
      }
    }

    const editModel = (model) => {
      editingModel.value = model
      Object.assign(modelForm, {
        route_key: model.route_key,
        target_model: model.target_model,
        provider: model.provider,
        prompt_keywords: model.prompt_keywords || '',
        description: model.description || '',
        api_key: model.api_key || '',
        api_base: model.api_base || '',
        auth_header: model.auth_header || 'Authorization',
        auth_format: model.auth_format || 'Bearer {key}',
        enabled: model.enabled
      })
      showCreateDialog.value = true
    }

    const deleteModel = async (model) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除模型配置 "${model.route_key}" 吗？`,
          '确认删除',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await modelApi.deleteModel(model.id)
        ElMessage.success('模型配置删除成功')
        await loadModels()
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除模型配置失败:', error)
          ElMessage.error('删除模型配置失败')
        }
      }
    }

    const toggleModelStatus = async (model) => {
      try {
        await modelApi.updateModel(model.id, { ...model, enabled: model.enabled })
        ElMessage.success(`模型配置已${model.enabled ? '启用' : '禁用'}`)
      } catch (error) {
        console.error('更新模型状态失败:', error)
        ElMessage.error('更新模型状态失败')
        // 回滚状态
        model.enabled = !model.enabled
      }
    }

    const resetForm = () => {
      editingModel.value = null
      Object.assign(modelForm, {
        route_key: '',
        target_model: '',
        provider: '',
        prompt_keywords: '',
        description: '',
        api_key: '',
        api_base: '',
        auth_header: 'Authorization',
        auth_format: 'Bearer {key}',
        enabled: true
      })
      if (formRef.value) {
        formRef.value.resetFields()
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

    const formatDateTime = (datetime) => {
      return datetime ? dayjs(datetime).format('YYYY-MM-DD HH:mm:ss') : '-'
    }

    onMounted(() => {
      loadModels()
    })

    return {
      loading,
      saving,
      showCreateDialog,
      editingModel,
      models,
      modelForm,
      formRules,
      formRef,
      loadModels,
      saveModel,
      editModel,
      deleteModel,
      toggleModelStatus,
      resetForm,
      getProviderTagType,
      formatDateTime
    }
  }
}
</script>

<style scoped>
.models-page {
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