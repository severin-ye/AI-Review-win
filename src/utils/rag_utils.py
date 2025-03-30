"""
医学RAG系统工具模块
为AI审校助手提供基于文档的医学事实性判断能力
"""

import os
import warnings
import json
import time
import openai
import logging
from typing import List, Dict, Any
import numpy as np
from openai import OpenAI
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_random_exponential
from config import path_manager

# 更精确地过滤LangChain弃用警告
warnings.filterwarnings("ignore", category=UserWarning)
# 特别屏蔽HuggingFaceEmbeddings相关警告
warnings.filterwarnings("ignore", message=".*HuggingFaceEmbeddings.*")

# langchain导入
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
# 使用新的嵌入导入路径
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader
from langchain_core.documents import Document

# 获取医学文档目录
MEDICAL_DOCS_DIR = path_manager.get_medical_docs_dir()

# 日志配置
logger = logging.getLogger(__name__)

class MedicalRAG:
    """医学RAG系统，提供医学事实性验证功能"""
    
    def __init__(self, docs_dir: str = MEDICAL_DOCS_DIR):
        """初始化医学RAG系统
        
        Args:
            docs_dir: 医学参考文档目录路径
        """
        self.docs_dir = docs_dir
        self.vector_store = None
        self.embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese",
            model_kwargs={'device': 'cpu'}
        )
        
        # 确保医学文档目录存在
        if not os.path.exists(self.docs_dir):
            os.makedirs(self.docs_dir)
    
    def load_documents(self) -> List[Document]:
        """加载医学参考文档
        
        Returns:
            List[Document]: 加载的文档列表
        """
        documents = []
        
        for filename in os.listdir(self.docs_dir):
            file_path = os.path.join(self.docs_dir, filename)
            
            try:
                if filename.lower().endswith('.pdf'):
                    loader = PyPDFLoader(file_path)
                    documents.extend(loader.load())
                elif filename.lower().endswith('.txt'):
                    loader = TextLoader(file_path, encoding='utf-8')
                    documents.extend(loader.load())
                elif filename.lower().endswith('.csv'):
                    loader = CSVLoader(file_path)
                    documents.extend(loader.load())
            except Exception as e:
                print(f"加载文档 {filename} 时出错: {e}")
        
        return documents
    
    def process_documents(self, documents: List[Document]) -> None:
        """处理文档并创建向量存储
        
        Args:
            documents: 要处理的文档列表
        """
        # 文本分割
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "，", " ", ""]
        )
        
        # 分割文档
        splits = text_splitter.split_documents(documents)
        
        # 创建向量存储
        self.vector_store = Chroma.from_documents(
            documents=splits,
            embedding=self.embeddings,
            persist_directory=os.path.join(self.docs_dir, "chroma_db")
        )
        
        print(f"成功处理 {len(splits)} 个文档片段")
    
    def initialize(self) -> None:
        """初始化RAG系统"""
        try:
            # 加载之前持久化的向量库
            if os.path.exists(os.path.join(self.docs_dir, "chroma_db")):
                self.vector_store = Chroma(
                    persist_directory=os.path.join(self.docs_dir, "chroma_db"),
                    embedding_function=self.embeddings
                )
                print("已加载现有向量数据库")
            else:
                # 加载文档并处理
                documents = self.load_documents()
                if documents:
                    self.process_documents(documents)
                    print("已创建新的向量数据库")
                else:
                    print(f"警告: 在 {self.docs_dir} 中未找到医学参考文档")
        except Exception as e:
            print(f"初始化医学RAG系统时出错: {e}")
    
    def search_medical_context(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索与查询相关的医学上下文
        
        Args:
            query: 查询文本
            top_k: 返回的最相关文档数量
            
        Returns:
            List[Dict]: 包含相关文档和相似度分数的字典列表
        """
        if not self.vector_store:
            print("错误: 向量存储未初始化，请先调用initialize()")
            return []
        
        try:
            # 执行相似度搜索
            results = self.vector_store.similarity_search_with_score(query, k=top_k)
            
            # 格式化结果
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                })
            
            return formatted_results
        except Exception as e:
            print(f"搜索医学上下文时出错: {e}")
            return []
    
    def get_medical_context(self, text: str) -> str:
        """获取与文本相关的医学上下文
        
        Args:
            text: 需要查找上下文的文本
            
        Returns:
            str: 组合的医学上下文
        """
        results = self.search_medical_context(text)
        
        if not results:
            return "未找到相关医学参考信息。"
        
        # 组合上下文
        context = "医学参考信息：\n\n"
        for i, result in enumerate(results, 1):
            context += f"{i}. {result['content']}\n"
            if result['metadata'] and 'source' in result['metadata']:
                context += f"   来源: {result['metadata']['source']}\n"
            context += "\n"
        
        return context

# 单例RAG系统
medical_rag = MedicalRAG()

def initialize_rag():
    """初始化RAG系统"""
    medical_rag.initialize()

def get_medical_verification(text: str) -> str:
    """获取医学事实验证信息
    
    Args:
        text: 需要验证的文本
        
    Returns:
        str: 医学验证上下文
    """
    return medical_rag.get_medical_context(text) 