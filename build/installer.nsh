; AI 审校助手 — NSIS 自定义钩子（electron-builder 26.x）
;
; 背景：客户端是托盘常驻设计（窗口收到 WM_CLOSE 只隐藏不退出，进程与后端 sidecar 驻留）。
; electron-builder 默认的 _CHECK_APP_RUNNING「先礼后兵」（allowOnlyOneInstallerInstance.nsh:105-164）：
;   先 taskkill 不带 /F（= 发 WM_CLOSE，对本应用无效）→ 重试时才 /F，且 PowerShell CIM 按
;   $INSTDIR 路径匹配进程在中文安装路径下可能匹配失败 → 最终弹「无法关闭」对话框。
; 此处用官方 customCheckAppRunning 钩子（allowOnlyOneInstallerInstance.nsh:37-38，
; CHECK_APP_RUNNING 宏内 !ifmacrodef 分支）整体替换默认逻辑：
;   安装/卸载需要关闭应用时，静默 taskkill /F /T /IM 强制结束全部同名进程，
;   短等后复查，全程无对话框；仅连续强杀仍存活（如应用以管理员身份运行）才回退标准重试提示。
;
; 本文件由 electron-builder 自动包含（nsis.include，未配置时默认取 buildResources 下
; installer.nsh；见 NsisTarget.js:600-603），在模板主体之前编译，宏定义先于使用点。
; 调用点：安装段 installSection.nsh:36（assisted 且非 UAC 内层实例）；
;        卸载 Function un.checkAppRunning（uninstaller.nsh:1-2，被 un.onInit 与卸载段调用）。

!macro customCheckAppRunning
  ; $R0 = tasklist/findstr 返回码（0 = 进程存在）；$R1 = 已强杀轮次。
  ; $CmdPath 由外层 CHECK_APP_RUNNING 宏初始化为 "$SYSDIR\cmd.exe"，直接沿用（与模板同款写法）。
  StrCpy $R1 0

  aiReviewCheckLoop:
    nsExec::Exec `"$CmdPath" /C tasklist /FI "IMAGENAME eq ${APP_EXECUTABLE_FILENAME}" /FO CSV /NH | "$SYSDIR\findstr.exe" /B /I /C:"\"${APP_EXECUTABLE_FILENAME}\""`
    Pop $R0
    ${if} $R0 != 0
      Goto aiReviewCheckDone ; 进程不存在，放行
    ${endIf}

    DetailPrint "$(appClosing)"
    ; 托盘常驻应用只能强杀：/F 强制、/T 连带进程树、/IM 按映像名匹配全部实例；nsExec 无窗口静默
    nsExec::Exec `"$CmdPath" /C taskkill /F /T /IM "${APP_EXECUTABLE_FILENAME}"`
    Pop $R0
    Sleep 1500 ; 等进程真正退出，避免后续文件占用

    IntOp $R1 $R1 + 1
    ${if} $R1 <= 4
      Goto aiReviewCheckLoop
    ${endIf}

    ; 连续强杀仍存活（更高权限运行等）：回退标准提示，用户手动关闭后点「重试」再走一轮；
    ; 静默模式（/SD IDCANCEL）下默认取消 → 中止安装，好过装出文件占用坏包
    MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "$(appCannotBeClosed)" /SD IDCANCEL IDRETRY aiReviewCheckRetry
    Quit
    aiReviewCheckRetry:
      StrCpy $R1 0
      Goto aiReviewCheckLoop

  aiReviewCheckDone:
!macroend
