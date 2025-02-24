# AI 审校助手架构设计

## 整体架构

AI 审校助手采用模块化设计，主要分为以下几个核心模块：

### 1. 核心模块 (src/core)

- `main.py`: 程序入口，负责协调各个模块的工作
- `ai_review.py`: AI 审校核心逻辑，负责文本分析和审校
- `text_processor.py`: 文本处理核心，负责文本的分割、合并等操作

### 2. 工具模块 (src/utils)

- `file_utils.py`: 文件操作相关工具
- `docx_utils.py`: Word 文档处理工具
- `table_utils.py`: 表格处理工具
- `text_utils.py`: 文本处理工具
- `ai_utils.py`: AI 相关工具
- `similarity_utils.py`: 文本相似度计算工具
- `cleanup_utils.py`: 清理工具

### 3. 安全模块 (src/security)

- `key_generator.py`: 密钥生成器
- `key_verifier.py`: 密钥验证器
- `time_lock.py`: 时间锁定功能

### 4. 配置模块 (config)

- `config.py`: 基础配置
- `config_manager.py`: 配置管理器

## 数据流

1. 输入文件 → data/input/
2. 文件处理 (file_utils.py, docx_utils.py)
3. 文本处理 (text_processor.py)
4. AI 审校 (ai_review.py)
5. 结果输出 → data/output/

## 安全机制

- 使用密钥系统控制软件使用权限
- 时间锁定机制防止非法使用
- 配置文件加密存储敏感信息

## 扩展性设计

- 模块化架构便于添加新功能
- 工具类设计遵循单一职责原则
- 配置系统支持灵活调整参数 