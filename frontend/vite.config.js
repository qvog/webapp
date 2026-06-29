import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  server: {
    host: true, // 🎯 Меняем на true! Это откроет сервер для Windows/сети
    port: 3005, // 🎯 Меняем порт, чтобы обойти кэш браузера
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000', 
        ws: true,
      }
    }
  }
})