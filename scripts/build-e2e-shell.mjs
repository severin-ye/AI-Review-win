/**
 * 构建任务 2/3 的 shell e2e 主进程包：
 *   入口 scripts/e2e-shell-entry.ts（动态加载真实 app/desktop/main/index.ts）
 *   通过 esbuild 插件把真实 index.ts 对 './sidecar' 的引用替换为 scripts/e2e-sidecar-stub.ts，
 *   其余模块（license/*、preload/renderer 产物）全部为真实代码。
 *
 * 用法：node scripts/build-e2e-shell.mjs
 * 产物：scripts/.e2e-shell-main.cjs
 */
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { build } from 'esbuild'

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

/** 仅当引用方是真实 app/desktop/main/index.ts 时，把 './sidecar' 重定向到桩模块 */
const stubSidecarPlugin = {
  name: 'stub-sidecar',
  setup(b) {
    b.onResolve({ filter: /^\.\/sidecar$/ }, (args) => {
      const importer = args.importer.replace(/\\/g, '/')
      if (importer.endsWith('app/desktop/main/index.ts')) {
        return { path: path.join(repoRoot, 'scripts', 'e2e-sidecar-stub.ts') }
      }
      return null
    })
  },
}

await build({
  entryPoints: [path.join(repoRoot, 'scripts', 'e2e-shell-entry.ts')],
  bundle: true,
  platform: 'node',
  format: 'cjs',
  external: ['electron'],
  plugins: [stubSidecarPlugin],
  // 必须输出到 out/main/：真实 index.ts 用 __dirname/../renderer、__dirname/../preload 定位构建产物，
  // 放在此处才能解析到 out/renderer、out/preload（注意：electron-vite build 会清空 out/，需重新执行本脚本）
  outfile: path.join(repoRoot, 'out', 'main', 'e2e-shell.cjs'),
})

console.log('built out/main/e2e-shell.cjs')
