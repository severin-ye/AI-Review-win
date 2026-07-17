# 导入setuptools中的setup和find_packages函数
# setup用于配置项目的元数据和依赖
# find_packages用于自动发现项目中的Python包
from setuptools import setup, find_packages

setup(
    # 项目名称
    name="ai-review",
    
    # 项目版本号
    version="0.1.0",
    
    # 自动发现并包含所有Python包
    packages=find_packages(),
    
    # 项目运行所需的依赖包
    install_requires=[
        # 在这里列出项目依赖
        "python-docx",  # 处理Word文档
        "lxml",  # XML处理
        "openai",  # OpenAI API
        "dashscope", # 通义千问 API
        "langchain", # LangChain框架
        "langchain-community", # LangChain社区组件
        "langchain-huggingface", # LangChain HuggingFace集成
        "chromadb", # 向量数据库
        "sentence-transformers", # 文本向量化
        "pypdf", # PDF处理
    ],
    
    # 项目作者信息
    author="severin",
    author_email="xxx@gmail.com",
    
    # 项目的简要描述
    description="AI文档审校助手",
    
    # 项目的关键词,用于PyPI搜索
    keywords="AI, document, review, medical, RAG",
    
    # 指定项目运行所需的Python最低版本
    python_requires=">=3.8",
) 