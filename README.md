# AI 审校助手（AI-Review-win）

医学文稿 AI 审校桌面应用：上传 Word 文稿 → AI 自动审校（事实/术语/语法/格式四类问题，附医学知识库证据）→ 人工逐条确认 → 导出双版本 Word 成稿。

技术形态：**Electron 桌面壳 + React 19 / TypeScript / Tailwind v4 渲染层 + Python FastAPI sidecar 后端 + SQLite 持久化 + LanceDB 向量库 + BGE-M3 本地向量模型 + SaT（MIT）句子分割模型 + OpenAI 兼容协议 LLM**（查询重写与审校共用一套配置，DeepSeek / OpenAI / 通义 / 本地 vLLM 均可接入）。

本仓库同时保留三年前的 Python/Tkinter 旧版代码（只读参照，见文末「旧版遗留说明」）；当前活跃代码为 2026 年 7 月按 `docs/design/AI-Review-Electron-重构设计.md` 完成的 Electron 重构版。

## 功能特性

- **文稿解析**：docx 上传；首个表格按「审查意见表」自动移除（可配），其余表格抽取另存并以 `[{表格不予审校_N}]` 占位符原位替换，导出时原样还原。
- **智能分句**：MIT 许可的 SaT `sat-3l-sm` 小模型逐句分割（85 语言），加载失败自动回退中文标点正则；短句碎片合并、按章节分块、参考文献区自动识别（默认不审校）。
- **医学知识库（RAG）**：上传指南/说明书等参考文档（pdf / txt / csv / docx），增量索引（LanceDB 向量 + jieba BM25 关键词双索引）；每个待审校句子经 LLM 查询重写（默认 8 问）后做 **向量 top-3 + BM25 top-3** 混合检索，RRF（k=60）融合去重，产出 ≤6 条带来源的证据。
- **LLM 结构化审校**：按块送审，输出「原文片段 / 修改建议 / 错误类型 / 严重度 / 证据引用 / 解释」，JSON 结构化解析校验后入库；失败可断点重试，已人工决定的条目默认保留。
- **人工审校工作台**：三栏布局（原文高亮 / 修改卡片 / 证据面板），键盘快捷键（1 保留原文、2 采纳、3 自定义、j/k 切换），逐条决定即写库，支持批量接受/拒绝，可随时关闭续作。
- **双版本导出**：清洁版 `{原名}_审校修订1_.docx`（直接替换）+ 留痕版 `{原名}_审校修订2_.docx`（`｛～原文:x AI/用户:y～｝` 标记），表格原位还原、章节标题与首行缩进保留。
- **任务化与实时进度**：审校、知识库索引、模型下载走后台线程 + jobs 表 + SSE 推送进度；后端重启自动收敛僵尸状态。
- **模型管理**：设置页查看 SaT / BGE-M3 本地模型状态，一键从 hf-mirror 预下载（断点续传）；保存设置后自动做 LLM 连通性测试。

## 界面简介

| 页面 | 路由 | 说明 |
|---|---|---|
| 文档库 | `/#/documents` | 上传 docx、查看状态机进度；行内按钮驱动全流程：解析 → 检索 → AI 审校（SSE 进度圈）→ 继续审校 / 查看审校 → 导出成稿；行展开可看分块树、重写问题与证据、parsed.md、导出产物面板 |
| 审校工作台 | `/#/workbench/:docId` | 三栏人工决定界面：左=文档原文（按严重度着色高亮），中=修改建议卡片（字符级 diff），右=该句 3+3 检索证据（AI 引用蓝框标记）；顶栏含进度条、三向筛选、批量操作 |
| 医学知识库 | `/#/kb` | 参考文档上传/删除/重新索引，索引进度 SSE 实时日志；列表显示状态、chunk 数、内容 hash |
| 设置 | `/#/settings` | LLM（base_url / api_key / model）、检索参数、Embedding provider、导出目录；模型管理（状态 + 预下载）；保存后自动 LLM 连通测试（绿勾/红叉） |

## 快速开始

### 环境要求

- Windows 10+（当前代码与脚本仅适配 Windows；sidecar 进程树清理用了 `taskkill`）
- Node.js（本机开发使用 v24.15.0；electron-vite 5 要求 Node 20.19+/22.12+）
- Python **3.12**（本机 `backend/.venv` 实测 3.12.13）
- Git Bash 用户注意：本仓库脚本里 `npm` 需写作 `npm.cmd`（详见 `docs/development/开发指南.md`）

### 首次安装

```bash
npm install                # 前端依赖（.npmrc 已配 Electron 镜像）
npm run backend:setup      # 创建 backend/.venv 并安装 requirements.txt
# torch 必须单独装 CPU 版（requirements.txt 无法表达 --index-url）：
backend/.venv/Scripts/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 开发模式（Electron，推荐）

```bash
npm run dev
```

electron-vite 同时构建主进程/预加载/渲染层并启动 Electron；主进程自动拉起 Python sidecar（`backend/.venv` 的 uvicorn，动态空闲端口，健康检查通过后才创建窗口）。

### 浏览器预览模式（无 Electron，调 UI 用）

```bash
npm run backend:dev        # 终端 1：后端 uvicorn，127.0.0.1:8765，--reload
npm run dev:renderer       # 终端 2：renderer 独立 vite dev server
```

页面顶部显示「浏览器预览模式」提示条；`window.api` 系统集成功能（打开所在文件夹）降级为下载链接。

### 运行测试

```bash
cd backend
.venv/Scripts/python -m pytest tests/ -q     # 30 个用例，stub embedding + mock LLM，零网络/模型依赖
```

### 构建与打包

```bash
npm run build          # electron-vite 三端构建到 out/
npm run dist:backend   # PyInstaller 打 backend/dist/ai-review-backend.exe（约 361MB，需先 pip install pyinstaller）
npm run dist           # npm run build + electron-builder → release/ 下 NSIS 安装包
```

模型文件（数 GB）不打入安装包；首次启动后在「设置 → 模型管理」一键预下载。

## 顶层目录导览

```
AI-Review-win/
├── electron/                  # 【新版】Electron 主进程 + 预加载脚本
│   ├── main/index.ts          #   窗口创建、sidecar 引导、IPC、生命周期
│   ├── main/sidecar.ts        #   动态端口、spawn 后端、健康轮询、进程树清理
│   └── preload/index.ts       #   contextBridge → window.api
├── renderer/                  # 【新版】React 渲染层（不用 src/ 命名，避免与旧 Python 冲突）
│   ├── index.html  vite.config.ts
│   └── src/
│       ├── pages/             #   文档库 / 审校工作台 / 医学知识库 / 设置（四页面）
│       ├── api/client.ts      #   fetch 封装 + SSE 订阅 + baseUrl 解析
│       ├── stores/            #   zustand：workbenchStore（工作台）、appStore（预留）
│       ├── components/        #   BackendStatus + shadcn 风格手工 UI 组件
│       └── lib/               #   diff.ts（字符级 LCS diff）、utils.ts（cn）
├── backend/                   # 【新版】Python FastAPI sidecar
│   ├── app/
│   │   ├── main.py            #   FastAPI 装配、CORS、启动建库 + 僵尸状态清理
│   │   ├── api/               #   REST + SSE 路由（health/documents/corrections/jobs/kb/models/settings）
│   │   ├── pipeline/          #   ingest 解析 / segment 分句 / review 审校 / export 导出
│   │   ├── rag/               #   embeddings / index / retrieve / store（LanceDB+BM25）
│   │   ├── llm/client.py      #   OpenAI 兼容客户端（chat_json + tenacity 重试）
│   │   ├── models/tables.py   #   11 张 SQLModel 表
│   │   └── core/              #   config（数据目录/模型探测）、db、joblog、user_settings
│   ├── tests/                 #   pytest 30 用例
│   ├── run.py                 #   PyInstaller 打包入口（--port / env PORT）
│   ├── ai-review-backend.spec #   PyInstaller spec（单文件 exe）
│   └── requirements.txt
├── docs/                      # 文档（见下方索引）
├── package.json  electron.vite.config.ts  electron-builder.yml
├── tsconfig.json  tsconfig.node.json  .npmrc
│
│  ─── 以下为旧版（2023 年 Python/Tkinter 单体）遗留，只读保留，不参与新版构建 ───
├── main.py                    # 【旧版】Tkinter 应用入口
├── src/                       # 【旧版】core/ui/utils/security 源码
├── config/                    # 【旧版】配置管理与主题
├── tests/                     # 【旧版】pytest（与 backend/tests/ 无关）
├── hide_file/                 # 【旧版】运行时配置备份、Chroma 向量库、临时产物
├── logs/                      # 【旧版】运行日志
├── material/                  # 【旧版】图标资源
├── requirements.txt  setup.py # 【旧版】依赖与安装脚本（UTF-16 编码；新版用 backend/requirements.txt）
├── doc_Structure_Description.md  doc_log.md   # 【旧版】结构说明与变更记录
├── 可以用的提示词  重构思路        # 【旧版】提示词汇编与早期重构设想
```

## 文档索引

| 文档 | 内容 |
|---|---|
| [docs/architecture/架构总览.md](docs/architecture/架构总览.md) | 三进程拓扑、技术栈全表、端到端数据流、开发/生产模式、浏览器预览降级 |
| [docs/architecture/后端详解.md](docs/architecture/后端详解.md) | 模块树、API 端点全表、文档状态机、jobs/SSE 机制、pipeline 四阶段、RAG 与 LLM 客户端细节 |
| [docs/architecture/前端详解.md](docs/architecture/前端详解.md) | 路由与四页面、zustand stores、api/client.ts、SSE 封装、BackendStatus、样式体系 |
| [docs/architecture/数据模型与持久化.md](docs/architecture/数据模型与持久化.md) | SQLite 11 表逐字段、数据目录布局、模型文件、导出命名、LanceDB 结构 |
| [docs/architecture/配置项参考.md](docs/architecture/配置项参考.md) | settings 全部键、api_key 掩码规则、环境变量、DeepSeek 等接入示例 |
| [docs/development/开发指南.md](docs/development/开发指南.md) | 环境准备与坑、全部命令、测试清单、调试技巧、打包流程与已知问题、代码风格 |
| [docs/design/AI-Review-Electron-重构设计.md](docs/design/AI-Review-Electron-重构设计.md) | 重构总体设计（选型依据、流水线设计、数据模型、实施计划） |
| docs/dev/M1~M5 与修复文档 | 各里程碑实现说明与验证记录（M1 骨架 / M2 解析分割 / M3 混合检索 / M4 审校工作台 / M5 导出打包 / LLM 连通与状态修复） |
| [docs/research/调研笔记.md](docs/research/调研笔记.md) | SaT / 混合检索 / 查询重写 / sidecar 架构的调研结论 |

## 旧版遗留说明

仓库根部的 `main.py`、`src/`、`config/`、`tests/`、`hide_file/`、`logs/`、`material/`、根 `requirements.txt`、`setup.py` 及 `doc_*.md` 等文件属于 2023 年的 Python/Tkinter 旧版应用，**保持原样只读保留**（设计文档第 11 节决议），其作用仅剩：

- 新版移植业务逻辑时的对照参考（如 `src/utils/table_utils.py` 的表格占位方案、`docx` 导出标记语法 `｛～原文:x AI:y～｝`、首行缩进等，均已在新版 `backend/app/pipeline/` 中重写并注明出处）；
- git 历史之外的实物存档。

旧版的已知缺陷（每次启动清空工作目录、Chroma 索引"永不重建"bug、自研规则分割器泛化差、结果不入库等）正是本次重构的动因，细节见 `docs/design/AI-Review-Electron-重构设计.md` 第 1 节。**不要**在旧目录下新增代码，也不要让新版代码 import 旧模块；旧版如需运行请自行创建独立虚拟环境（其依赖与 `backend/.venv` 不共享）。
