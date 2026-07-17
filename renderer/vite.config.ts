import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// 独立 vite 配置：仅起 renderer 的 dev server（浏览器预览兜底，不经 Electron）。
// 用法：npm run dev:renderer -- --port <port>（等价 vite --config renderer/vite.config.ts）
// 后端另开终端跑 npm run backend:dev（127.0.0.1:8765），页面顶部显示「浏览器预览模式」提示条。
export default defineConfig({
  root: __dirname,
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    host: '127.0.0.1',
    strictPort: false,
  },
})
