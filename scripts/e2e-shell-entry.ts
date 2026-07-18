/**
 * 端到端验证（任务 2/3：splash 启动画面 + 系统托盘最小化）：
 *   真实 Electron 主进程 = 真实 app/desktop/main/index.ts 全量逻辑
 *   （仅 './sidecar' 经 esbuild 插件替换为本地桩，不启动 Python，不触碰 8767/8768）
 *   + 真实 preload/renderer 构建产物 + 临时 userData
 *
 * 验证点：
 *   1. 启动即出现 splash 小窗（360x220，data: URL），主窗口此时尚不可见
 *   2. 主窗口 ready-to-show 后：splash 关闭、主窗口可见、背景色为 #f8fafc
 *   3. 托盘存在，菜单为「显示主窗口 / 分隔符 / 退出 AI 审校助手」
 *   4. 主窗口 close() → 不销毁、仅隐藏（进程存活）
 *   5. 合成托盘 click → 主窗口恢复可见
 *   6. 触发菜单「退出」→ isQuitting → app.quit() → 进程真正退出（由外层观察进程是否结束）
 *
 * 构建：node scripts/build-e2e-shell.mjs
 * 运行：node_modules\.bin\electron scripts\.e2e-shell-main.cjs
 */
import os from 'node:os'
import path from 'node:path'
import fs from 'node:fs'
import { app, BrowserWindow } from 'electron'

const sleep = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms))

async function main(): Promise<void> {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ai-review-shell-e2e-'))
  app.setPath('userData', tmp)

  // 动态加载真实主入口：其模块副作用注册 whenReady → bootstrap（许可证 init → 桩 sidecar → 建窗 → 托盘）
  const mainModule = (await import('../app/desktop/main/index')) as typeof import('../app/desktop/main/index')
  const hooks = mainModule.getShellHooksForTest()

  const result: Record<string, unknown> = {}
  const waitFor = async (
    pred: () => Promise<boolean> | boolean,
    label: string,
    timeout = 30000,
  ): Promise<void> => {
    const t0 = Date.now()
    while (Date.now() - t0 < timeout) {
      if (await pred()) return
      await sleep(200)
    }
    throw new Error(`等待超时: ${label}`)
  }

  try {
    // —— 1. splash 先于主窗口出现 ——
    await waitFor(() => {
      const s = hooks.getSplash()
      return s !== null && !s.isDestroyed() && s.isVisible()
    }, 'splash 出现', 20000)
    const splashWin = hooks.getSplash()!
    result.splashShown = true
    result.splashSize = splashWin.getSize()
    await waitFor(
      () => splashWin.webContents.getURL().startsWith('data:text/html'),
      'splash 加载 data URL',
      10000,
    )
    result.splashIsDataUrl = true
    const winAtSplash = hooks.getMainWindow()
    result.mainHiddenWhileSplash = winAtSplash === null || !winAtSplash.isVisible()

    // —— 2. 主窗口就绪：splash 关闭 + 主窗口可见 ——
    await waitFor(() => {
      const w = hooks.getMainWindow()
      return w !== null && !w.isDestroyed() && w.isVisible()
    }, '主窗口可见')
    result.mainVisible = true
    await waitFor(() => hooks.getSplash() === null, 'splash 关闭')
    result.splashClosedAfterMain = true
    const win = hooks.getMainWindow()!
    result.mainBackground = win.getBackgroundColor()
    await waitFor(
      async () =>
        String(
          await win.webContents.executeJavaScript('document.body.innerText', true),
        ).includes('激活许可证'),
      '渲染层激活页就绪',
    )
    result.rendererReady = true

    // —— 3. 托盘与菜单 ——
    await waitFor(() => hooks.getTray() !== null, '托盘创建')
    result.trayExists = true
    const menu = hooks.getTrayMenu()
    result.menuItems = menu ? menu.items.map((i) => (i.label !== '' ? i.label : i.type)) : null

    // —— 4. 点关闭 → 隐藏而非销毁（进程存活）——
    win.close()
    await sleep(1000)
    result.afterClose_destroyed = win.isDestroyed()
    result.afterClose_visible = win.isVisible()
    result.afterClose_windowCount = BrowserWindow.getAllWindows().length

    // —— 5. 合成托盘 click → 恢复主窗口 ——
    hooks.getTray()!.emit('click')
    await waitFor(() => win.isVisible() && win.isFocused(), '托盘单击恢复', 10000)
    result.restoredByTrayClick = true

    // —— 6. 菜单「退出」→ 进程真退 ——
    const quitItem = menu?.items.find((i) => i.label.includes('退出'))
    result.quitItemFound = Boolean(quitItem)
    console.log(`E2E_SHELL_RESULT ${JSON.stringify(result, null, 2)}`)
    if (quitItem) {
      quitItem.click(quitItem, undefined, {} as Electron.KeyboardEvent)
    } else {
      app.quit()
    }
    // 退出路径失效时兜底强退（非 0 码便于外层识别失败）
    setTimeout(() => {
      console.log('E2E_SHELL_FORCE_EXIT')
      process.exit(3)
    }, 10000).unref()
  } catch (err) {
    result.error = err instanceof Error ? err.message : String(err)
    console.log(`E2E_SHELL_RESULT ${JSON.stringify(result, null, 2)}`)
    app.quit()
    setTimeout(() => process.exit(4), 5000).unref()
  }
}

void main()
