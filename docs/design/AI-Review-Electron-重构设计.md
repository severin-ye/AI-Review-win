# AI-Review Electron 重构设计文档

> 版本：v0.1（设计评审稿）
> 日期：2026-07-17
> 状态：待用户确认

---

## 1. 背景与目标

旧版 AI-Review-win 是三年前的 Tkinter 桌面应用，存在以下核心问题：

- UI/交互停留在 Tkinter 弹窗时代，无任务持久化，每次启动清空工作目录
- RAG 为手写实现，检索逻辑有 bug（chroma_db 目录预创建导致新文档永不重建索引）
- 直接用原文做向量检索，top-5 无关键词检索兜底，对医学专有名词不敏感
- 自研语义分割器是硬编码规则，针对特定文章结构，泛化差
- 审校结果只进临时 md 文件，无数据库、不可断点续作

**重构目标**：以 Electron 重写为接近真实产品的桌面应用，保留并升级核心业务（Word 文稿 → AI 审校 → 人工确认 → Word 成稿），引入现代化检索与分割方案。

### 核心需求（来自用户）

| # | 需求 | 决策 |
|---|------|------|
| 1 | Electron 重写 | electron-vite + React + TypeScript |
| 2 | 句子分割用 MIT 小模型 | SaT `segment-any-text/sat-3l-sm`（wtpsplit），与 CuraView 项目一致 |
| 3 | RAG 不手写，用开源包 | LangChain（Python）|
| 4 | 混合检索 | 向量 3 条 + 关键词(BM25) 3 条 / 每句 |
| 5 | 查询重写 | 不用原文直接查，先重写 5~10 个问题再检索（默认 8，可配置）|
| 6 | 持久化与交互逻辑重做 | SQLite + 任务状态机 + SSE 实时进度 |

---

## 2. 总体架构

采用 2025 年 AI 桌面应用主流模式：**Electron 壳 + Python FastAPI sidecar 后端**（参考：腾讯 youtu-tip 同款架构）。

```
┌─────────────────────────────────────────────────┐
│ Electron 主进程 (Node.js)                        │
│  - 窗口/菜单/文件对话框/自动更新                  │
│  - 拉起 & 守护 Python sidecar 子进程              │
│  - IPC 桥接 (contextBridge, 类型安全 API)        │
├─────────────────────────────────────────────────┤
│ Renderer (React SPA)                            │
│  - React 19 + TypeScript + Vite                 │
│  - Tailwind CSS v4 + shadcn/ui                  │
│  - Zustand 状态管理, TanStack Query 数据获取      │
│  - SSE 订阅流水线进度                            │
└──────────────┬──────────────────────────────────┘
               │ HTTP (127.0.0.1:动态端口) + SSE
┌──────────────▼──────────────────────────────────┐
│ Python FastAPI sidecar                          │
│  - 流水线引擎 (解析→分割→检索→审校→导出)          │
│  - LangChain 检索: EnsembleRetriever(BM25+向量)   │
│  - wtpsplit SaT 句子分割                         │
│  - LLM 客户端 (OpenAI 兼容协议, 结构化输出)       │
│  - SQLite (SQLModel) 持久化                      │
│  - python-docx 文档解析/生成                     │
└─────────────────────────────────────────────────┘
```

**为什么不是纯 Node**：SaT 模型（PyTorch/transformers）与 LangChain Python 生态是硬约束；Python sidecar 是业界验证过的方案，开发时 `npm run dev` 同时拉起两端，分发时 PyInstaller 把后端打成单个 exe 内嵌进 Electron 安装包。

---

## 3. 技术栈选型与调研依据

| 层 | 选型 | 依据 |
|----|------|------|
| 桌面壳 | Electron 33+ / electron-vite 3 | 2025 标配，HMR 快，主/预加载/渲染三端统一构建 |
| 前端 | React 19 + TypeScript + Tailwind v4 + shadcn/ui | 现代组件体系，接近真实产品 |
| 前端状态 | Zustand + TanStack Query | 轻量、与服务端状态分离清晰 |
| 后端 | Python 3.11 + FastAPI + uvicorn | sidecar 模式事实标准 |
| 句子分割 | **wtpsplit `sat-3l-sm`**（MIT，0.2B 参数，85 语言，支持 ONNX） | CuraView 已验证；HF 官方页确认 MIT 许可；月下载 51 万 |
| 检索框架 | LangChain `EnsembleRetriever` + `BM25Retriever` + 向量库 | 业界混合检索标准做法（RRF 融合）|
| 向量库 | **LanceDB**（嵌入式、无服务、列存） | CuraView GraphRAG 同款；比 Chroma 更轻 |
| Embedding | **BGE-M3**（BAAI，MIT，中英双语强）| 替代旧 text2vec-base-chinese；2024 后中文检索事实标准之一 |
| BM25 中文分词 | jieba | rank_bm25 需要分词器 |
| LLM 接入 | OpenAI 兼容协议（base_url 可配）| 一套代码通吃 OpenAI / DeepSeek / 通义 / 本地 vLLM |
| 结构化输出 | `response_format=json_schema`（fallback tool calling）| 比旧版强制 tool_choice 更稳 |
| 持久化 | SQLite + SQLModel；文件存 app data 目录 | 单机桌面应用标配 |
| 文档 | python-docx + mammoth(docx→md) + pandoc(可选) | 保留旧版表格占位符方案 |
| 打包 | electron-builder + PyInstaller | sidecar 打成单 exe 嵌入 |
| 后端日志/重试 | structlog + tenacity | — |

---

## 4. 目录结构（新）

```
AI-Review-win/
├── electron/                  # Electron 主进程 + 预加载
│   ├── main/                  # 窗口、sidecar 守护、IPC
│   └── preload/               # contextBridge 类型安全 API
├── src/                       # Renderer (React)
│   ├── pages/                 # 文档库 / 审校工作台 / 知识库 / 设置
│   ├── components/
│   ├── stores/  api/  hooks/
│   └── ...
├── backend/                   # Python FastAPI sidecar
│   ├── app/
│   │   ├── main.py            # FastAPI 入口
│   │   ├── api/               # REST + SSE 路由
│   │   ├── pipeline/          # 流水线各阶段
│   │   │   ├── ingest.py      # docx 解析、表格抽取/占位
│   │   │   ├── segment.py     # SaT 分割 + 分块
│   │   │   ├── retrieve.py    # 查询重写 + 混合检索
│   │   │   ├── review.py      # LLM 审校
│   │   │   └── export.py      # 生成两个版本 docx
│   │   ├── rag/
│   │   │   ├── index.py       # 知识库索引(增量)
│   │   │   ├── embeddings.py  # BGE-M3 加载
│   │   │   └── store.py       # LanceDB + BM25 索引
│   │   ├── llm/               # OpenAI 兼容客户端、prompt、schema
│   │   ├── models/            # SQLModel 表结构
│   │   └── core/              # 配置、日志、路径
│   ├── tests/
│   └── pyproject.toml
├── docs/
│   ├── design/                # 本文档
│   └── reference/             # 已从 CuraView/Decathlon 复制的资料
├── package.json  electron.vite.config.ts
└── (旧代码冻结于 legacy/ 或保留 git 历史)
```

---

## 5. 核心流水线设计

### 5.1 总览（每个文档一个 Job，状态机驱动）

```
uploaded → parsed → segmented → retrieving → reviewing
         → pending_manual → exporting → done
                                ↘ failed (可重试，断点续作)
```

每一步产物落库 + 落盘，**任何一步失败可从该步重跑**，不再一次性清空目录。

### 5.2 阶段细节

**① ingest（解析）**
- docx → 可选移除首个审查意见表 → 表格抽取另存 → 原位置换为占位符 `[{表格不予审校_N}]`（沿用旧版验证过的方案）→ 转 Markdown 存盘
- 表格与占位符映射关系入库（JSON），导出时还原

**② segment（分割）**
- **SaT `sat-3l-sm` 逐句分割**（替代旧自研规则分割器）
  - 加载：`wtpsplit.SaT("sat-3l-sm")`，首次自动从 HF 下载（支持配置镜像/本地缓存路径）
  - 回退：模型加载失败时中文标点正则分句（与 CuraView 一致）
  - 过滤：句长 < 10 字符的碎片按配置合并/丢弃（沿用 CuraView `min_sentence_length: 10`）
- **分块**：按章节结构（标题正则）把句子组织成审校块（block），单块上限 ~1000 字；引用文献区单独成块（默认不审校，可配置）
- 产出：blocks[]，每块含 sentences[]，全部入库

**③ retrieve（检索增强，本设计核心）**

对**每个待审校句子**执行：

```
句子 S
 ├─ ① 查询重写: LLM 一次调用生成 5~10 个检索问题
 │     （默认 8，可配置 5-10；包含 1 个原句保留 + N 个改写）
 │     prompt 要求: 提取医学实体、生成不同角度的核查问题
 ├─ ② 并行检索: 每个问题同时打两路
 │     ├─ 向量路: BGE-M3 embedding → LanceDB top-k
 │     └─ 关键词路: jieba 分词 → BM25 top-k
 ├─ ③ 融合: 每路内部跨问题 RRF 融合去重
 │     （EnsembleRetriever 同算法；RRF k=60）
 └─ ④ 截断: 向量路 top-3 + 关键词路 top-3，去重后 ≤6 条证据
       每条带来源标签(vector/keyword)、来源文档、相似度
```

- **数量依据**：用户指定 3+3；业界 EnsembleRetriever 常配 k=3~5/路
- **重写数量依据**：用户指定 5~10（默认 8）；业界 MultiQueryRetriever 默认 3、RAG-Fusion 4~5、实践指南 3~6——8 偏上限，靠 RRF+去重压噪，且重写调用本身是一次 LLM 调用出全部问题，成本可控
- 证据按句子分组存入 DB，审校 prompt 中按句附上

**④ review（LLM 审校）**
- 以 block 为单位调用 LLM（保留上下文连贯），prompt 中给出：
  - 块原文（句子编号）
  - 每句对应的检索证据（编号引用）
- 结构化输出（json_schema）：
  ```json
  {"corrections": [{
    "sentence_id": 3,
    "original": "…",
    "suggestion": "…",
    "error_type": "事实错误|语法错误|格式错误",
    "severity": "high|medium|low",
    "evidence_ids": [1,2],
    "explanation": "…"
  }]}
  ```
  （相比旧版只 original+suggestion，新增类型/严重度/证据引用/解释——旧《重构思路》文档里的扩展建议落地）
- 全部 corrections 入库，状态 → pending_manual

**⑤ 人工审校（Web 工作台，替代 Tkinter 弹窗）**
- 三栏布局：左=文档原文（差异句高亮）；中=差异卡片列表（原句/建议句/类型/证据可展开）；右=证据面板
- 每条约：接受(2) / 保留原文(1) / 自定义(3) / 跳过，支持键盘快捷键
- 批量操作：按类型/严重度筛选、全部接受低风险、撤销
- **进度实时保存**（每条决定即写库），可随时关闭续作

**⑥ export（导出）**
- 双版本沿用旧版逻辑：
  - 清洁版：直接替换
  - 留痕版：`｛～原文:x AI:y～｝`（自定义标「用户:」）
- 占位符还原真实表格 → 首行缩进 → 输出 docx 到用户指定目录

### 5.3 医学知识库管理（独立模块）

- 知识库页面：上传/删除参考文档（PDF/TXT/CSV/DOCX），列表显示索引状态
- **增量索引**：文档稳定 ID + 内容 hash，变更才重建对应 chunk（修复旧版"永不重建"bug）
- chunk 500 字 / overlap 50（沿用），chunk 同时入 LanceDB（向量）和 BM25 索引（内存+落盘）
- 索引进度 SSE 推送

---

## 6. 数据模型（SQLite）

```sql
documents      -- id, filename, status(状态机), created_at, error
blocks         -- id, document_id, idx, chapter, text
sentences      -- id, block_id, idx, text
queries        -- id, sentence_id, text, idx           (重写的问题)
evidence       -- id, sentence_id, source(vector|keyword), chunk_text,
                  doc_name, score, rank                 (3+3 证据)
corrections    -- id, sentence_id, original, suggestion, error_type,
                  severity, explanation, evidence_ids(json),
                  decision(pending|accepted|rejected|custom),
                  custom_text, decided_at
kb_documents   -- id, filename, content_hash, status, chunk_count
kb_chunks      -- id, kb_document_id, idx, text        (LanceDB 向量外挂)
settings       -- key, value (json)
jobs / job_events -- 任务与 SSE 事件流水
```

文件布局：`%APPDATA%/ai-review/{projects/<doc-id>/…, kb/, models/, app.db}`

---

## 7. API 设计（FastAPI，后端 ↔ 前端）

```
POST   /api/documents              上传 docx
GET    /api/documents              列表(含状态)
POST   /api/documents/{id}/run     启动/重跑流水线(可从指定阶段)
GET    /api/documents/{id}/detail  blocks+sentences+corrections
POST   /api/corrections/{id}/decision   人工决定(accept/reject/custom)
POST   /api/documents/{id}/export  导出双版本 docx
POST   /api/kb/documents           上传参考文档(异步索引)
GET    /api/kb/documents           知识库列表
DELETE /api/kb/documents/{id}
GET    /api/settings  PUT /api/settings
GET    /api/models/status          SaT/embedding 模型下载状态
POST   /api/models/download        预下载模型(带进度)
SSE    /api/jobs/{id}/events       流水线实时事件
```

---

## 8. 配置体系（设置页）

| 配置 | 默认 | 说明 |
|------|------|------|
| llm.base_url / api_key / model | — | OpenAI 兼容；密钥存 OS 钥匙串(keytar) |
| review.prompt | 内置医学审校模板 | 可编辑 |
| retrieve.query_count | 8 | 查询重写数量，范围 5-10 |
| retrieve.vector_topk / bm25_topk | 3 / 3 | 每句两路各取条数 |
| retrieve.rrf_k | 60 | RRF 常数 |
| retrieve.enabled | true | 关闭则纯 LLM 审校 |
| segment.min_sentence_length | 10 | SaT 碎片过滤 |
| segment.review_references | false | 是否审校引用文献块 |
| embedding.model | BAAI/bge-m3 | 可切换 |
| docx.has_review_table / first_line_indent | Y / 0.5in | 兼容旧版 |

---

## 9. 打包与分发

- 开发：`npm run dev` → electron-vite HMR + 自动拉起 `uvicorn --reload`
- 分发：PyInstaller 把 backend 打成 `ai-review-backend.exe`（模型不打包，首次启动引导下载，支持 HF 镜像）→ electron-builder 打 NSIS 安装包
- 模型管理：设置页显示 SaT/BGE-M3 下载状态，支持预下载、断点续传、自定义缓存目录

---

## 10. 分阶段实施计划

| 阶段 | 内容 | 验收 |
|------|------|------|
| M1 骨架 | electron-vite+React+TS 工程、FastAPI sidecar 拉起、IPC/HTTP 通道、设置页 | 两端连通，hello 流水线 |
| M2 解析+分割 | ingest(docx/表格)、SaT 分割、分块入库 | 上传 docx 出句子列表 |
| M3 检索 | 知识库索引(LanceDB+BM25)、查询重写、3+3 混合检索 | 知识库页+每句证据可见 |
| M4 审校 | LLM 结构化审校、工作台 UI、人工决定 | 完整跑通一篇 |
| M5 导出+打磨 | docx 双版本导出、模型管理、打包 | 安装包可用 |

---

## 11. 开放问题（请拍板）

1. **LLM 默认接入**：只保留 OpenAI 兼容协议一套（推荐，DeepSeek/通义都能接），还是仍要 dashscope 原生 SDK？
2. **Embedding 模型**：BGE-M3（推荐，效果好但 ~2.2GB 下载）还是 bge-base-zh-v1.5（~400MB，轻量）？
3. **旧密钥验证机制**（HMAC 每日密钥）还要吗？建议废弃或换成简单 License 文件。
4. **旧代码处置**：保留在 `legacy/` 目录参照，还是直接从工作区移除（git 历史仍在）？
5. **审校粒度**：以 block（多句，默认，上下文连贯）还是逐句（证据更精准、LLM 调用更多）为单位送审？
6. **界面语言**：中文 UI 优先？（旧版为中文）

---

## 附录 A：调研来源

- CuraView 项目（`1_Research/CuraView`）：SaT 模型用法、LangChain 1.0/LangGraph、GraphRAG(LanceDB) —— 文档已复制至 `docs/reference/curaview/`
- Decathlon_VOC_Analyzer：LangChain 1.0 教程 —— 已复制至 `docs/reference/langchain-1.0教程.md`
- HF 官方页 `segment-any-text/sat-3l-sm`：MIT 许可、0.2B 参数、85 语言、ONNX 支持（2026-07-17 访问）
- LangChain 混合检索实践（EnsembleRetriever + BM25Retriever + RRF）：掘金/SegmentFault 多篇 2025-2026 实践文
- 查询重写规模：MultiQueryRetriever 默认 3、RAG-Fusion(Rackauckas 2024)、DMQR-RAG(arXiv:2411.13154)、GEO Community 实践指南(3~6 条)
- Electron+Python sidecar 架构：TencentCloudADP/youtu-tip（Electron+React+Vite / Python3.11+FastAPI / PyInstaller）
