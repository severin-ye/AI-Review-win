# AI 审校助手

这是一个基于 AI 的文档审校工具，用于自动化文档审查和校对过程。

## 项目结构

```
AI-Review-win/
├── src/                    # 源代码目录
│   ├── core/              # 核心业务逻辑
│   │   ├── ai_review.py   # AI 审校核心
│   │   ├── file_processor.py
│   │   └── text_processor.py
│   ├── utils/             # 工具类
│   │   ├── file_utils.py
│   │   ├── docx_utils.py
│   │   └── table_utils.py
│   └── security/          # 安全相关
│       ├── key_generator.py
│       └── key_verifier.py
├── config/                # 配置文件目录
│   └── config.py
├── tests/                 # 测试目录
├── docs/                  # 文档目录
├── data/                  # 数据目录
│   ├── input/            # 原文件目录
│   └── output/           # 审校后目录
├── scripts/              # 构建和安装脚本
│   └── installer.py
└── requirements.txt      # 依赖管理
```

## 功能模块

- 文件处理：支持多种文档格式的读取和处理
- AI 审校：利用 AI 技术进行文档审查和校对
- 安全验证：包含密钥生成和验证功能
- 文本处理：支持智能分段、表格处理等功能

## 环境要求

- Python 3.8+
- 详细依赖请参见 requirements.txt

## 使用说明

1. 将待审校文件放入 data/input 目录
2. 运行程序进行审校
3. 审校结果将保存在 data/output 目录 