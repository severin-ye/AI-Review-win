# CuraView (精衡) — 医疗AI幻觉检测与评估系统

**中文** | [English](README.md)

> 基于多智能体架构和GraphRAG知识图谱的医疗大语言模型幻觉检测、评估研究平台，已投稿至 *Knowledge-Based Systems* (KBS)

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![GraphRAG](https://img.shields.io/badge/GraphRAG-Microsoft-orange.svg)](https://github.com/microsoft/graphrag)
[![LangChain](https://img.shields.io/badge/LangChain-1.0-purple.svg)](https://www.langchain.com/)

---

## 项目概述

**CuraView（精衡）** 是一个医疗AI幻觉检测研究平台，聚焦于医疗大语言模型输出的可靠性与安全性问题。系统构建了 **知识图谱构建 → 智能幻觉检测 → 多维度评估** 的全流程研究管线，核心创新在于将 GraphRAG 结构化证据与多层级检测架构相结合。

### 核心创新

- **GraphRAG 医疗知识图谱**：基于 Microsoft GraphRAG 构建，支持实体关系抽取、社区检测与向量检索，为检测提供结构化证据
- **多层次幻觉检测 Agent**：结合 GraphRAG 上下文增强的逐句检测，支持 API / 本地模型双模式，包含语义一致性、逻辑连贯性、术语准确性等多层验证
- **E0–E4 证据等级体系**：从无证据到绝对证据的五级证据分级，支持细粒度幻觉判定
- **完整评估管线**：涵盖基线对照实验、多模型规模对比、性能分析、人工标注一致性验证的全套评测工具
- **KBS 论文投稿**：完整论文稿件（LaTeX + PDF）及全套投稿附件

---

## 项目架构

```
CuraView/
│
├── langchain/                                    # LangChain 多智能体系统
│   └── hallucination_detection_graphrag_agent/   # 幻觉检测 Agent ⭐
│       ├── detect.py                             # 主入口（交互/后台/批量）
│       ├── config.yaml                           # API/本地模式配置
│       ├── models/                               # 核心模型
│       │   ├── agent.py                          # Agent 创建与单句检测
│       │   ├── schemas.py                        # Pydantic 数据模型
│       │   ├── validators.py                     # 三层验证器
│       │   ├── local_llm.py                      # 本地 LLM 推理
│       │   └── local_llm_json.py                 # JSON 结构化输出
│       ├── doc/                                  # 详细文档（设计/修复/验证）
│       │   ├── 设计文档/
│       │   ├── 配置与切换/
│       │   ├── 修复/
│       │   ├── 验证系统/
│       │   └── prompts/                          # 检测 Prompt 模板
│       ├── logs/                                 # Agent 运行日志
│       └── README.md
│
├── graphrag/                                     # GraphRAG 知识图谱系统 ⭐
│   ├── settings.yaml                             # 全局配置（qwen-plus + text-embedding-v3）
│   ├── input/                                    # EHR 数据输入（46,998 患者）
│   ├── prompts/                                  # Prompt 模板（3 套可切换）
│   │   ├──  医学定制 病历/                        # 当前激活的医疗定制 Prompt
│   │   ├── 医学定制 4文件 图谱构建 问答 中文提示词/
│   │   └── 原提示词备份/                           # 英文原始备份
│   ├── core/                                     # 核心功能模块
│   │   ├── index/                                # 索引构建（分患者/批量/预处理）
│   │   ├── query/                                # 查询功能（LocalSearch/上下文捕获）
│   │   ├── Visualization/                        # 图谱可视化
│   │   └── clean/                                # 数据清洗
│   ├── tools/prompt_switch/                      # Prompt 集切换工具
│   └── doc/                                      # 内部文档
│
├── experiment/                                   # 实验与评估 ⭐
│   ├── 幻觉生成_幻觉检测_系统联调/                  # 核心评估管线
│   │   ├── compare_systems.py                    # SystemComparator 主程序
│   │   ├── tools/                                # 指标计算/异常率/报告生成
│   │   │   ├── metrics_calculator.py             # Recall/Precision/F1
│   │   │   ├── anomaly_calculator.py             # E1-E4 异常率/惩罚率
│   │   │   ├── report_generator.py               # JSON/TXT 报告
│   │   │   └── table_generator.py                # 多模型对比表格
│   │   ├── scripts/                              # 辅助脚本
│   │   └── output/                               # 按模型组织的评估输出
│   │
│   ├── baseline_comparison/                      # 基线对照实验
│   │   ├── baseline_common.py                    # 共享基础设施
│   │   ├── run_flat_evidence_baseline.py         # 扁平证据基线
│   │   ├── run_no_evidence_baseline.py           # 无证据基线
│   │   ├── run_rule_based_baseline.py            # 规则基线
│   │   ├── run_ragtruth_baseline.py              # RAGTruth 基线
│   │   ├── run_qags_baseline.py                  # QAGS 基线
│   │   └── paperstyle_baselines/                 # 论文风格基线实现
│   │
│   ├── 性能分析/                                  # 性能分析工具
│   │   ├── analyze_performance.py                # 日志解析/瓶颈识别
│   │   ├── batch_analyze.py                      # 跨批次对比
│   │   └── monitor_performance.py                # 实时监控
│   │
│   ├── 8b vs 14b vs 32b/                         # 模型规模对比
│   │   └── compare_8b_14b_32b.py                 # 复用 SystemComparator
│   │
│   ├── Meditron-7B相关/                           # Meditron 模型评估
│   │   ├── Meditron-7B-生成内容评估/
│   │   └── Meditron-7B-幻觉类型统计/
│   │
│   ├── min_10_test/                               # 最少句子数边界测试
│   └── sentence_gt_review/                        # 人工标注一致性验证
│       ├── analyze_agreement_report.py
│       ├── export_sentence_gt_review_packet.py
│       └── 人工标注.json
│
├── Meditron-7B/                                  # Meditron-7B 模型工具
│   ├── generation/                               # 出院小结生成
│   │   ├── batch_process_patients.py             # 批量处理（46,998 患者）
│   │   └── test_meditron.py                      # 单患者测试
│   ├── detection/                                # Meditron 输出幻觉检测
│   │   ├── detect_hallucinations_local.py        # 本地模型检测
│   │   └── detect_meditron_reports.py            # 检测包装器
│   ├── docs/                                     # 使用文档
│   └── README.md
│
├── Dataset/                                      # 数据集
│   ├── discharge-me/                             # MIMIC-IV 原始数据
│   │   ├── train/                                # 训练集（46,998 患者）
│   │   ├── valid/
│   │   ├── test_phase_1/
│   │   └── test_phase_2/
│   └── discharge-me_with_person_in_json/         # 以患者为中心的 JSON 格式
│       ├── ehr_dataset_full.json
│       └── README.md
│
├── 论文/                                         # KBS 期刊投稿 ⭐
│   ├── KBS-最终投稿包/                            # 最终投稿包
│   │   ├── 01_Manuscript/                        # LaTeX + PDF 稿件
│   │   ├── 02_Title_Page/
│   │   ├── 03_Highlights/
│   │   ├── 04_Cover_Letter/
│   │   ├── 05_Declarations/
│   │   └── 06_Figures/
│   ├── KBS-统一工作区/                             # 投稿工作区（含源素材）
│   └── figures/                                  # 论文图表 PDF
│
├── 开源/                                         # 开源子模块
│   ├── CuraView/                                 # GitHub 主仓库镜像
│   └── CuraView-EVD/                             # 证据标注数据集仓库
│
├── scripts/                                      # 工具脚本
│   └── generate_unified_paper_figures.py         # 论文图表统一生成
│
├── AGENTS.md                                     # AI Agent 使用说明
├── build_complete_paper.py                       # 论文构建入口
├── README.md                                     # 英文文档
└── README.zh-CN.md                               # 中文文档（当前）
```

---

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/severin-ye/CuraView.git
cd CuraView

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装核心依赖
pip install graphrag langchain langchain-openai openai pyyaml pydantic pandas
```

### 2. 配置 API 密钥

```bash
export GRAPHRAG_API_KEY="your_qwen_api_key_here"
```

### 3. 构建 GraphRAG 知识图谱

```bash
cd graphrag

# 初始化并构建索引（需先准备 input/ 中的 EHR 数据）
graphrag index --root .

# 索引构建完成后验证
ls output/index_output/
```

### 4. 运行幻觉检测

```bash
cd langchain/hallucination_detection_graphrag_agent

# 交互式检测
python detect.py

# 后台批量检测
python detect.py --background --all

# 检测指定患者范围
python detect.py --background --start 1 --end 50

# 查看检测进度
python detect.py --status
```

### 5. 系统评估

```bash
cd experiment/幻觉生成_幻觉检测_系统联调

# 交互式联调
python compare_systems.py

# 指定模型和患者
python compare_systems.py --model qwen-plus --patient 1

# 多患者范围
python compare_systems.py --model qwen3-14b-base --patient "1 50"
```

### 6. 基线对照实验

```bash
cd experiment/baseline_comparison

# 一键运行所有基线
python run_all_baselines.py

# 或单独运行
python run_flat_evidence_baseline.py
python run_no_evidence_baseline.py
python run_rule_based_baseline.py
```

---

## 核心功能详解

### 1. GraphRAG 知识图谱

**位置**: `graphrag/`

基于 Microsoft GraphRAG 构建医疗领域知识图谱，支持实体关系抽取、社区检测和向量检索。

#### 架构流程

```
EHR JSON 数据
    ↓
文本块分割（chunk_size=1200, overlap=100）
    ↓
实体提取（患者/诊断/症状/药物/手术/生命体征等）
    ↓
关系抽取（has_diagnosis, prescribed, performed 等）
    ↓
社区检测（Leiden 算法）
    ↓
向量化（text-embedding-v3）
    ↓
LanceDB 存储
    ↓
LocalSearch / GlobalSearch 查询
```

#### 可切换 Prompt 集

| Prompt 集 | 路径 | 说明 |
|-----------|------|------|
| 医学定制 病历 | `prompts/ 医学定制 病历/` | 当前激活，含 18 个中文医疗定制 Prompt 文件 |
| 医学定制 4文件 | `prompts/医学定制 4文件 图谱构建 问答 中文提示词/` | 备选医疗 Prompt 集 |
| 原提示词备份 | `prompts/原提示词备份/` | 英文原始 Prompt（用于 A/B 对照） |

```bash
# 使用 Prompt 切换工具
cd graphrag/tools/prompt_switch
python switch_prompts.py --list         # 列出可用集
python switch_prompts.py --set medical_custom  # 切换集
```

---

### 2. 幻觉检测 Agent

**位置**: `langchain/hallucination_detection_graphrag_agent/`

**入口**: `detect.py` — 交互式 / 后台 / 批量三种运行模式

#### 多层次检测架构

```
Detection Framework:
├── 语义一致性检测：基于医学知识图谱的事实验证
├── 逻辑连贯性检测：推理链路径验证
├── 上下文相关性检测：GraphRAG 召回内容对比分析
├── 专业术语准确性：医学词典 + 本体匹配
└── 临床安全性检测：风险评估 + 禁忌症检查
```

#### 检测流程

```
待检测文本
    ↓
句子切分
    ↓
逐句 GraphRAG 查询（获取上下文证据）
    ↓
LLM 幻觉检测（结构化输出）
    ↓
三层验证（格式 → 一致性 → 业务规则）
    ↓
生成检测报告（JSON 格式）
```

#### 证据等级定义

| 等级 | 名称 | 含义 |
|------|------|------|
| **E0** | 无证据 | GraphRAG 未找到相关信息 |
| **E1** | 弱证据 | 部分相关但不直接支持 |
| **E2** | 中等证据 | 相关信息但有模糊性 |
| **E3** | 强证据 | 直接支持或反驳 |
| **E4** | 绝对证据 | 完全匹配的事实 |

#### API / 本地双模式

```yaml
# config.yaml 核心配置
llm:
  mode: local          # api 或 local
  api:
    model: qwen-plus
    provider: qwen
    temperature: 0.3
  local:
    model_path: /path/to/Qwen3-14B-Base
    device_map: auto

detection:
  async_graphrag: true
  enable_batch_processing: true

graphrag:
  query_method: local
  project_root: ../../graphrag
```

#### 使用示例

```bash
# 交互模式
python detect.py

# 后台批量模式
python detect.py --background --start 1 --end 100

# 查看检测状态
python detect.py --status
```

---

### 3. 幻觉类型体系

检测系统覆盖 **7 种** 医学幻觉类型：

| 类型 | 英文名 | 说明 | 示例 |
|------|--------|------|------|
| 诊断错误 | diagnosis_error | 疾病诊断被篡改 | 糖尿病 → 高血压 |
| 用药错误 | medication_error | 药物信息被篡改 | 阿司匹林 → 青霉素 |
| 检查结果错误 | exam_result_error | 检查结果极性翻转 | 阴性 → 阳性 |
| 时间错误 | time_error | 时间信息偏差 | 3天 → 7天 |
| 数值错误 | value_error | 数值被修改 | 120/80 → 180/120 |
| 否定错误 | negation_error | 肯定/否定颠倒 | "无发热" → "有发热" |
| 虚构事实 | invented_fact | 完全伪造医学事件 | 插入不存在的手术 |

---

### 4. 系统评估与实验

**位置**: `experiment/`

#### 4.1 核心评估管线（`幻觉生成_幻觉检测_系统联调/`）

`SystemComparator` 类（976 行）对比幻觉生成与检测系统的输出，计算完整性能指标。

**评估指标**：
- **召回率 (Recall)**：检测到的幻觉 / 实际注入的幻觉
- **精确率 (Precision)**：正确识别的幻觉 / 总检出幻觉
- **F1 分数**：召回率与精确率的调和平均（分别以 E3+E4 和仅 E4 计算）
- **验证准确率 (Verif. Acc.)**：幻觉/非幻觉二分类准确率
- **异常率 / 惩罚率**：基于 E1-E4 证据等级的错误分布分析

```bash
# 交互式运行
python compare_systems.py

# 多模型对比
python compare_systems.py --model qwen-plus --all
python compare_systems.py --model qwen3-14b-base --patient "1 50"
python compare_systems.py --model qwen3-32b-base --patient "1 50"
```

#### 4.2 基线对照实验（`baseline_comparison/`）

通过消融实验验证 CuraView 各组件的贡献：

| 基线 | 说明 | 核心发现 |
|------|------|---------|
| 扁平证据 | GraphRAG 证据去结构化 | 结构化组织对 E4 检测至关重要 |
| 无证据 | 不提供 GraphRAG 证据 | 缺少证据使 F1 大幅下降 |
| 规则基线 | 仅基于启发式规则 | 规则方法召回率极低（~15%） |
| RAGTruth | RAGTruth 风格判定 | 论文风格对照 |
| QAGS | 问题生成 + 答案比对 | 问答风格对照 |

#### 4.3 性能分析（`性能分析/`）

日志解析工具，分析 GPU 内存、步骤耗时、瓶颈识别：

```bash
python analyze_performance.py       # 单次运行分析
python batch_analyze.py              # 跨批次对比
python monitor_performance.py        # 实时监控
```

#### 4.4 模型规模对比（`8b vs 14b vs 32b/`）

对比 Qwen3-8B / 14B / 32B 在同一患者集上的检测性能。

#### 4.5 人工标注验证（`sentence_gt_review/`）

计算 AI 检测与人工标注的一致性，支持幻觉存在性、类型、证据等级的交叉验证。

---

### 5. Meditron-7B 评估

**位置**: `Meditron-7B/`

完整的 Meditron-7B 医疗报告生成与幻觉检测工具链：
- **生成模块**：批量出院小结生成（46,998 患者）
- **检测模块**：使用主检测管线评估 Meditron 输出的幻觉分布
- **统计分析**：7 种幻觉类型的分布统计

```bash
cd Meditron-7B

# 批量生成
python generation/batch_process_patients.py

# 幻觉检测
python detection/detect_hallucinations_local.py

# 快捷脚本
./quick_start.sh
```

---

### 6. KBS 论文投稿

**位置**: `论文/`

已完成 KBS 期刊投稿包准备，包含：
- LaTeX 稿件源码（Elsevier CAS 模板）
- 编译后的 PDF 稿件
- 标题页、Highlights、Cover Letter
- 利益冲突声明、数据可用性声明、AI 使用声明
- 8 张论文图表（PDF 格式）
- 统一投稿工作区（含历史版本归档）

```bash
# 重新编译论文
cd 论文/KBS-统一工作区/01_current_submission/manuscript_source
pdflatex submission_format_fin.tex
bibtex submission_format_fin
pdflatex submission_format_fin.tex
pdflatex submission_format_fin.tex
```

---

## 开源仓库

**位置**: `开源/`

项目包含两个 Git 子模块：

| 子模块 | 仓库 | 说明 |
|--------|------|------|
| CuraView | [github.com/severin-ye/CuraView](https://github.com/severin-ye/CuraView) | 主代码仓库 |
| CuraView-EVD | [github.com/severin-ye/CuraView-EVD](https://github.com/severin-ye/CuraView-EVD) | 证据标注幻觉数据集 |

```bash
# 初始化子模块
git submodule update --init --recursive
```

---

## 技术栈

| 类别 | 技术 |
|------|------|
| **Agent 框架** | LangChain 1.0, LangGraph |
| **知识图谱** | Microsoft GraphRAG, LanceDB, NetworkX |
| **LLM 后端** | Qwen-plus (API), Qwen3-8B/14B/32B (本地), Meditron-7B |
| **数据验证** | Pydantic 2.0 |
| **数据处理** | Pandas, NumPy, PyArrow |
| **可视化** | Matplotlib, NetworkX |
| **论文排版** | LaTeX (Elsevier CAS) |

---

## 系统要求

- **Python**: 3.10+
- **内存**: 32GB+（本地模型推理），16GB+（API 模式）
- **存储**: 100GB+（含 GraphRAG 索引输出和模型权重）
- **GPU**: NVIDIA RTX 4090+（本地模型推理）
- **API**: Qwen API Key（API 模式）

---

## 性能基准

| 任务 | 性能 | 硬件 |
|------|------|------|
| GraphRAG 索引构建 | ~2 小时 / 10,000 患者 | GPU: RTX 4090 |
| 幻觉检测（串行） | ~3 秒 / 句子 | API: qwen-plus |
| 幻觉检测（并行） | ~1 秒 / 句子（4 并发） | API: qwen-plus |
| 检测 F1 分数（E3+E4） | 64–77% | 取决于模型 |
| 检测 F1 分数（仅 E4） | 56–77% | 取决于模型 |

---

## 当前进展

### 已完成

- [x] Microsoft GraphRAG 框架集成（医疗实体-关系图谱）
- [x] 自定义 Prompt 模板（医学定制 3 套可切换）
- [x] LanceDB 向量存储
- [x] 多层次幻觉检测 Agent（API + 本地双模式）
- [x] E0-E4 五级证据等级体系
- [x] Pydantic 结构化输出 + 三层验证管线
- [x] 并行检测支持
- [x] 后台批量运行与进度追踪
- [x] 完整评估管线（Recall/Precision/F1/异常率）
- [x] 基线对照实验（扁平证据/无证据/规则/RAGTruth/QAGS）
- [x] 模型规模对比（8B vs 14B vs 32B）
- [x] 性能分析工具（日志解析/瓶颈识别/实时监控）
- [x] 人工标注一致性验证
- [x] Meditron-7B 幻觉检测与统计分析
- [x] KBS 期刊完整投稿包

### 进行中

- [ ] 幻觉纠错 Agent 开发
- [ ] 多种检测策略对比实验
- [ ] 大规模数据集评估
- [ ] 模型微调实验

---

## 文档资源

### 核心文档

| 文档 | 位置 |
|------|------|
| 幻觉检测 Agent README | [langchain/hallucination_detection_graphrag_agent/README.md](langchain/hallucination_detection_graphrag_agent/README.md) |
| 检测系统详细文档 | [langchain/hallucination_detection_graphrag_agent/doc/](langchain/hallucination_detection_graphrag_agent/doc/) |
| 系统联调 README | [experiment/幻觉生成_幻觉检测_系统联调/README.md](experiment/幻觉生成_幻觉检测_系统联调/README.md) |
| 基线实验 README | [experiment/baseline_comparison/README.md](experiment/baseline_comparison/README.md) |
| 性能分析 README | [experiment/性能分析/README.md](experiment/性能分析/README.md) |
| 模型对比 README | [experiment/8b vs 14b vs 32b/README.md](experiment/8b vs 14b vs 32b/README.md) |
| GraphRAG 查询模块 | [graphrag/core/query/README.md](graphrag/core/query/README.md) |
| GraphRAG 索引模块 | [graphrag/core/index/README.md](graphrag/core/index/README.md) |
| Prompt 切换工具 | [graphrag/tools/prompt_switch/README.md](graphrag/tools/prompt_switch/README.md) |
| Prompt 定制指南 | [graphrag/prompts/ 医学定制 病历/GraphRAG_Prompts自定义指南.md](graphrag/prompts/%20医学定制%20病历/GraphRAG_Prompts自定义指南.md) |
| EHR 数据集说明 | [graphrag/input/README.md](graphrag/input/README.md) |
| Meditron 使用说明 | [Meditron-7B/README.md](Meditron-7B/README.md) |
| 论文投稿包说明 | [论文/KBS-最终投稿包/00_README_最终投稿包说明.md](论文/KBS-最终投稿包/00_README_最终投稿包说明.md) |
| AGENTS.md | [AGENTS.md](AGENTS.md) |

---

## 故障排除

### 常见问题

#### 1. API 密钥未设置

```bash
# 错误信息
ValueError: 请设置环境变量: GRAPHRAG_API_KEY

# 解决方案
export GRAPHRAG_API_KEY="your_key_here"
```

#### 2. GraphRAG 索引未构建

```bash
# 错误信息
FileNotFoundError: output/index_output/create_final_entities.parquet

# 解决方案
cd graphrag
graphrag index --root .
```

#### 3. 并行检测错误

```bash
# 错误信息
RuntimeError: Thread pool execution error

# 解决方案
# 在 config.yaml 中设低 max_concurrent_queries 或设置 parallel_detection: false
```

#### 4. 本地模型显存不足

```bash
# 使用更小的模型或降低批处理参数
# 在 config.yaml 中调整 device_map 或使用 API 模式
```

---

## 贡献

欢迎社区贡献！参与方式：

```bash
# 1. Fork 项目
# 2. 创建功能分支
git checkout -b feature/new-feature

# 3. 提交更改
git commit -m "Add: 新功能描述"

# 4. 推送到分支
git push origin feature/new-feature

# 5. 创建 Pull Request
```

---

## 项目统计

- **数据规模**: 46,998 患者 EHR 记录
- **知识图谱**: 已构建医疗实体-关系-社区三层结构
- **检测系统**: 完整的多层次检测 Agent（~140KB Python 代码）
- **评估工具**: 6 套实验模块，35+ 评估脚本
- **基线实验**: 5 种基线方法对照
- **论文稿件**: 已完成的 KBS 期刊投稿包

---

## KBS 论文

本项目的研究成果已撰写论文投稿至 *Knowledge-Based Systems*：

> Ye, S., Kong, X., He, X., Yan, G., Peng, L., & Oh, D. (2026). **CuraView: A Multi-Agent Framework for Medical Hallucination Detection with GraphRAG-Enhanced Knowledge Verification**.

论文相关文件位于 `论文/` 目录，包含完整的 LaTeX 源码、编译 PDF 及全部投稿附件。

---

## 许可证

本项目采用 **MIT License**。

---

## 联系方式

- **项目负责人**: Severin Ye
- **GitHub**: [@severin-ye](https://github.com/severin-ye)
- **邮箱**: [6severin9@gmail.com](mailto:6severin9@gmail.com)

---

## 相关链接

- [Microsoft GraphRAG](https://github.com/microsoft/graphrag)
- [LangChain 官方文档](https://python.langchain.com/)
- [MIMIC-IV 数据集](https://physionet.org/content/mimic-iv-ed/)
- [Qwen 模型系列](https://github.com/QwenLM/Qwen)
- [CuraView GitHub](https://github.com/severin-ye/CuraView)
- [CuraView-EVD 数据集](https://github.com/severin-ye/CuraView-EVD)

---

## 引用

如果本项目对您的研究有帮助，请考虑引用：

```bibtex
@misc{curaview2026,
  title  = {CuraView: A Multi-Agent Framework for Medical Hallucination Detection with GraphRAG-Enhanced Knowledge Verification},
  author = {Ye, Severin and Kong, Xiao and He, Xiaopeng and Yan, Guangsu and Peng, Limei and Oh, Dongsuk},
  year   = {2026},
  url    = {https://github.com/severin-ye/CuraView}
}
```

---

<div align="center">

**如果本项目对您有帮助，请给我们一个 Star!**

[![Stars](https://img.shields.io/github/stars/severin-ye/CuraView?style=social)](https://github.com/severin-ye/CuraView/stargazers)

**共同推进医疗AI安全研究！**

</div>
