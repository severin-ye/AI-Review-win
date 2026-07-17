import { resolve } from 'node:path'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// 目录布局（方案 D 重构后）：
//   app/desktop/main    → 主进程（含 Python sidecar 守护）
//   app/desktop/preload → 预加载（contextBridge 类型安全 API）
//   app/web/            → React 渲染层（不能用 src/，与旧 Python 代码冲突）
export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'app/desktop/main/index.ts'),
        },
      },
    },
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'app/desktop/preload/index.ts'),
        },
      },
    },
  },
  renderer: {
    root: resolve(__dirname, 'app/web'),
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'app/web/src'),
      },
    },
    build: {
      rollupOptions: {
        input: resolve(__dirname, 'app/web/index.html'),
      },
    },
  },
})
