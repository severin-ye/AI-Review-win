/**
 * 端到端验证（任务 2/3：splash 启动画面 + 系统托盘最小化；任务 1a：单实例）：
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
 *   6. 单实例：隐藏主窗口后拉起第二实例进程 → 第二实例抢锁失败立即退出（退出码 0、
 *      无 E2E_SECOND_STILL_ALIVE），第一实例收到 second-instance → 窗口被 show/focus
 *   7. 触发菜单「退出」→ isQuitting → app.quit() → 进程真正退出（由外层观察进程是否结束）
 *
 * 环境变量：
 *   AI_REVIEW_E2E_ROLE     first（默认，完整验证流程）/ second（仅用于模拟第二实例）
 *   AI_REVIEW_E2E_USERDATA 指定 userData（第二实例必须与第一实例相同才会共享单实例锁）
 *
 * 构建：node scripts/build-e2e-shell.mjs
 * 运行：node_modules\.bin\electron out\main\e2e-shell.cjs
 */
import { spawn } from 'node:child_process'
import os from 'node:os'
import path from 'node:path'
import fs from 'node:fs'
import { app, BrowserWindow } from 'electron'

const sleep = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms))

async function main(): Promise<void> {
  const role = process.env['AI_REVIEW_E2E_ROLE'] ?? 'first'
  const tmp =
    process.env['AI_REVIEW_E2E_USERDATA'] ??
    fs.mkdtempSync(path.join(os.tmpdir(), 'ai-review-shell-e2e-'))
  app.setPath('userData', tmp)

  // 动态加载真实主入口：模块顶层即申请单实例锁；whenReady 后执行 bootstrap
  const mainModule = (await import('../app/desktop/main/index')) as typeof import('../app/desktop/main/index')

  if (role === 'second') {
    // 第二实例：锁必失败，index.ts 顶层已 app.quit()，进程随即退出。
    // 若 5 秒后仍然活着 = 锁被错误获取（bug），打标记并以非 0 码退出便于外层识别。
    setTimeout(() => {
      console.log('E2E_SECOND_STILL_ALIVE')
      process.exit(5)
    }, 5000).unref()
    return
  }

  const hooks = mainModule.getShellHooksForTest()

  const result: Record<string, unknown> = {}
  const waitFor = async (
    pred: () => Promise<boolean> | boolean,
    label: string,
    timeout = 30000,
    interval = 200,
  ): Promise<void> => {
    const t0 = Date.now()
    while (Date.now() - t0 < timeout) {
      let ok = false
      try {
        ok = await pred()
      } catch {
        ok = false // 窗口在两次采样间隙被关闭/销毁属正常竞态，继续轮询
      }
      if (ok) return
      await sleep(interval)
    }
    throw new Error(`等待超时: ${label}`)
  }

  try {
    // —— 1. splash 先于主窗口出现 ——
    // 注意竞态：启动极快时主窗口 ready-to-show 可能在采样间隙关闭 splash，
    // 因此在一次采样内原子地取齐 size/URL/主窗口状态；实在采样不到则以「主窗口已可见」佐证 splash 已完成使命。
    interface SplashInfo {
      size: number[]
      isDataUrl: boolean
      mainHidden: boolean
    }
    let splashInfo: SplashInfo | null = null
    await waitFor(
      () => {
        const s = hooks.getSplash()
        if (s && !s.isDestroyed() && s.isVisible()) {
          const url = s.webContents.getURL()
          if (url === '' || url === 'about:blank') return false // loadURL 尚未提交
          const w = hooks.getMainWindow()
          splashInfo = {
            size: s.getSize(),
            isDataUrl: url.startsWith('data:text/html'),
            mainHidden: w === null || !w.isVisible(),
          }
          return true
        }
        const w = hooks.getMainWindow()
        return w !== null && !w.isDestroyed() && w.isVisible()
      },
      'splash 出现',
      20000,
      50,
    )
    if (splashInfo !== null) {
      const info: SplashInfo = splashInfo
      result.splashShown = true
      result.splashSize = info.size
      result.splashIsDataUrl = info.isDataUrl
      result.mainHiddenWhileSplash = info.mainHidden
    } else {
      result.splashShown = 'closed-before-inspect(startup-too-fast)'
      result.mainHiddenWhileSplash = 'n/a'
    }

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

    // —— 6. 单实例：隐藏后拉起第二实例 → 第二实例退出、第一实例被激活 ——
    win.close()
    await sleep(800)
    result.singleInstance_hiddenBefore = !win.isDestroyed() && !win.isVisible()

    const bundlePath = path.resolve(process.argv[1]!)
    const second = spawn(process.execPath, [bundlePath], {
      env: {
        ...process.env,
        AI_REVIEW_E2E_ROLE: 'second',
        AI_REVIEW_E2E_USERDATA: tmp, // 与第一实例相同 userData → 共享同一把单实例锁
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    let secondOut = ''
    second.stdout?.on('data', (d: Buffer) => (secondOut += d.toString('utf8')))
    second.stderr?.on('data', (d: Buffer) => (secondOut += d.toString('utf8')))
    const secondExitCode = await new Promise<number | 'timeout'>((resolve) => {
      second.on('exit', (code) => resolve(code ?? -1))
      setTimeout(() => resolve('timeout'), 20000)
    })
    result.secondExitCode = secondExitCode
    result.secondStillAlive = secondOut.includes('E2E_SECOND_STILL_ALIVE')
    await waitFor(() => win.isVisible() && win.isFocused(), '第二实例激活主窗口', 10000)
    result.activatedBySecondInstance = true

    // —— 7. 菜单「退出」→ 进程真退 ——
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
