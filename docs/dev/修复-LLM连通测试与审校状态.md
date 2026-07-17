# 修复：LLM 连通测试 + 审校进度与失败状态（2026-07-17）

对应用户反馈的三个问题：保存设置后无连通反馈、审校缺进度与时间信息、审校失败卡在「审校中」。

## 1. LLM 连通性测试（保存后自动触发）

- 后端新增 `POST /api/settings/test-llm`（`backend/app/api/settings.py`）：
  读取库中已保存配置，发一次最小 chat 调用（`max_tokens=8`，timeout 30s，**单发不走 tenacity 重试**，失败快速返回）。
  始终 200：成功 `{ok:true, model, latency_ms}`；失败 `{ok:false, stage: config|connect, message}`（含 HTTP 状态码，截断 300 字符）。
- 前端 `SettingsPage.tsx`：保存成功 → 自动测试。状态 tag：
  - 测试中：琥珀色 tag + 旋转圈「LLM 连通性测试中…」（保存按钮此间禁用）
  - 成功：绿色 `✓ LLM 连接正常（模型名）xxxms`
  - 失败：红色 `✗ LLM 连接失败` + 下方红框展示具体原因
- 编辑任意 `llm.*` 字段 → 测试结果重置为 idle（避免绿勾与表单值不符）。
- client.ts 新增 `testLlmConnection()`。

## 2. 审校进度圈 + 开始时间 + 已持续时间

- `DocumentsPage.tsx`：点击「AI 审校」后出现进度面板：
  - SVG 环形进度（`ProgressRing`，块 x/y 百分比；总量未知时退化为旋转圈）
  - `开始于 HH:MM:SS · 已持续 mm:ss`（每秒刷新，`nowTick` interval）
  - 进度数据来自 SSE `start` / `progress` 事件的 `block_idx` / `blocks`

## 3. 审校失败正确显示（不再卡在审校中）

四层兜底：

1. **后端启动清理**（`main.py` lifespan `_sweep_interrupted_state()`）：
   进程重启后，`running` jobs → `error`；`reviewing/retrieving` 文档 → `failed`（error="任务中断：后端服务已重启，请重新执行该操作"）；`indexing` 知识库文档 → `failed`。
   解决 daemon 线程随进程死亡导致的僵尸状态。
2. **失败可重试**：`pipeline/review.py` 新增 `RETRYABLE_STATUSES = REVIEWABLE_STATUSES + ("failed",)`，
   failed 文档可直接重审/重检索（无 blocks 的解析失败文档给出明确 400 提示）。前端 failed 行显示「重试审校」按钮。
3. **前端轮询**：文档列表存在 `reviewing/retrieving` 状态时每 2s 刷新——页面重开也能跟上任务终态，不会永远转圈。
4. **失败原因展示**：SSE `done{status:error}` 时拉取文档详情取 `doc.error`，横幅显示「审校失败：原因」；状态芯片变红「失败」。

## 验证

- `pytest tests/ -q`：30 passed
- `npm run build`（electron-vite）：通过
- 冒烟（隔离数据目录 `AI_REVIEW_DATA_DIR=backend/.smoke-data`，已清理）：
  - test-llm 未配置 → `{ok:false, stage:"config"}`；不可达主机 → `{ok:false, stage:"connect", "HTTP 502…"}`
  - GET settings 掩码 `****abcd` 正常
  - 植入僵尸 reviewing/running/indexing 行 → 重启后全部收敛为 failed/error
