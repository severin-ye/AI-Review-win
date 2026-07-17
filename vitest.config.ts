import { defineConfig } from 'vitest/config'

// 许可证客户端单测：Node 环境，不依赖 electron / 真实服务器（全部依赖注入 + 假 fetch）。
// 真实服务器端到端链路走 scripts/license-smoke.ts（不进 vitest 默认套件）。
export default defineConfig({
  test: {
    environment: 'node',
    include: ['app/desktop/main/license/__tests__/**/*.test.ts'],
    testTimeout: 15_000,
  },
})
