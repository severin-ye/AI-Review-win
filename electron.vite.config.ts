import { resolve } from 'node:path'
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// 目录布局（M1 骨架）：
//   electron/main    → 主进程（含 Python sidecar 守护）
//   electron/preload → 预加载（contextBridge 类型安全 API）
//   renderer/        → React 渲染层（不能用 src/，与旧 Python 代码冲突）
export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'electron/main/index.ts'),
        },
      },
    },
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: {
          index: resolve(__dirname, 'electron/preload/index.ts'),
        },
      },
    },
  },
  renderer: {
    root: resolve(__dirname, 'renderer'),
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'renderer/src'),
      },
    },
    build: {
      rollupOptions: {
        input: resolve(__dirname, 'renderer/index.html'),
      },
    },
  },
})
