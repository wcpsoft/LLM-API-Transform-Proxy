<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside width="250px" class="sidebar">
      <div class="logo">
        <h2>Claude Proxy</h2>
        <p>管理后台</p>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        class="sidebar-menu"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/models">
          <el-icon><Setting /></el-icon>
          <span>模型配置</span>
        </el-menu-item>
        <el-menu-item index="/api-keys">
          <el-icon><Key /></el-icon>
          <span>API密钥</span>
        </el-menu-item>
        <el-menu-item index="/routes">
          <el-icon><Connection /></el-icon>
          <span>API路由</span>
        </el-menu-item>
        <el-menu-item index="/logs">
          <el-icon><Document /></el-icon>
          <span>请求日志</span>
        </el-menu-item>
        <el-menu-item index="/service-status">
          <el-icon><Monitor /></el-icon>
          <span>服务状态</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-content">
          <h3>{{ getPageTitle() }}</h3>
          <div class="header-actions">
            <el-dropdown @command="handleCommand">
              <span class="user-info">
                <el-icon><User /></el-icon>
                {{ userInfo?.username || 'Admin' }}
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">个人资料</el-dropdown-item>
                  <el-dropdown-item command="changePassword">修改密码</el-dropdown-item>
                  <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button type="primary" @click="refreshData">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </el-header>

      <!-- 主要内容 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi, clearUserAuth } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'Layout',
  setup() {
    const route = useRoute()
    const router = useRouter()
    const userInfo = ref(null)

    // 获取用户信息
    onMounted(async () => {
      try {
        const savedUserInfo = localStorage.getItem('user_info')
        if (savedUserInfo) {
          userInfo.value = JSON.parse(savedUserInfo)
        }
        
        // 验证token并获取最新用户信息
        const response = await authApi.getProfile()
        if (response.success) {
          userInfo.value = response.data
          localStorage.setItem('user_info', JSON.stringify(response.data))
        }
      } catch (error) {
        console.error('获取用户信息失败:', error)
      }
    })

    const getPageTitle = () => {
      const titles = {
        '/dashboard': '仪表盘',
        '/models': '模型配置管理',
        '/api-keys': 'API密钥管理',
        '/routes': 'API路由管理',
        '/logs': '请求日志',
        '/service-status': '服务状态监控'
      }
      return titles[route.path] || 'Claude Code Proxy 管理后台'
    }

    const refreshData = () => {
      // 触发当前页面数据刷新
      window.location.reload()
    }

    const handleCommand = async (command) => {
      switch (command) {
        case 'profile':
          ElMessage.info('个人资料功能开发中')
          break
        case 'changePassword':
          ElMessage.info('修改密码功能开发中')
          break
        case 'logout':
          await handleLogout()
          break
      }
    }

    const handleLogout = async () => {
      try {
        await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })

        // 调用退出API
        try {
          await authApi.logout()
        } catch (error) {
          console.error('退出API调用失败:', error)
        }

        // 清除本地认证信息
        clearUserAuth()
        
        // 跳转到登录页
        router.push('/login')
        ElMessage.success('已退出登录')
      } catch (error) {
        // 用户取消退出
      }
    }

    return {
      userInfo,
      getPageTitle,
      refreshData,
      handleCommand
    }
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
  color: #bfcbd9;
}

.logo {
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid #434a50;
}

.logo h2 {
  margin: 0;
  color: #409EFF;
  font-size: 20px;
}

.logo p {
  margin: 5px 0 0 0;
  font-size: 12px;
  color: #bfcbd9;
}

.sidebar-menu {
  border: none;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 20px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.header-content h3 {
  margin: 0;
  color: #333;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background-color 0.3s;
}

.user-info:hover {
  background-color: #f5f5f5;
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 200px !important;
  }
  
  .header-content {
    flex-direction: column;
    gap: 10px;
  }
  
  .header-actions {
    flex-wrap: wrap;
  }
}
</style>