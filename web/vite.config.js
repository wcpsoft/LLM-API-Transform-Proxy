import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8083',
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/v1': {
        target: 'http://localhost:8083',
        changeOrigin: true,
        secure: false
      },
      '/health': {
        target: 'http://localhost:8083',
        changeOrigin: true,
        secure: false
      },
      '/discovery': {
        target: 'http://localhost:8083',
        changeOrigin: true,
        secure: false
      },
      '/metrics': {
        target: 'http://localhost:8083',
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
})