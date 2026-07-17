#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
医学RAG系统独立测试脚本
该脚本用于测试医学RAG系统的功能，不依赖UI界面
可以通过命令行参数控制测试行为
"""

import os
import sys
import argparse
import logging
from typing import List, Dict, Any
import time

# 确保可以导入项目模块
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入项目模块
from src.utils.rag_utils import MedicalRAG, MEDICAL_DOCS_DIR
from config import path_manager

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MedicalRAGTester:
    """医学RAG系统测试类"""

    def __init__(self, docs_dir=None, verbose=False):
        """初始化测试器
        
        Args:
            docs_dir: 医学文档目录，如果为None则使用默认目录
            verbose: 是否显示详细日志
        """
        self.verbose = verbose
        self.docs_dir = docs_dir or MEDICAL_DOCS_DIR
        
        # 日志级别设置
        if self.verbose:
            logger.setLevel(logging.DEBUG)
        
        logger.info(f"使用医学文档目录: {self.docs_dir}")
        
        # 初始化RAG系统
        self.rag = MedicalRAG(docs_dir=self.docs_dir)
    
    def test_document_loading(self) -> bool:
        """测试文档加载功能
        
        Returns:
            bool: 测试是否通过
        """
        logger.info("测试: 文档加载")
        
        # 检查文档目录是否存在且包含文件
        if not os.path.exists(self.docs_dir):
            logger.error(f"文档目录不存在: {self.docs_dir}")
            return False
        
        files = os.listdir(self.docs_dir)
        supported_files = [f for f in files if f.lower().endswith(('.pdf', '.txt', '.csv'))]
        
        if not supported_files:
            logger.warning(f"目录中没有支持的文档文件: {self.docs_dir}")
            logger.info("请添加一些.pdf, .txt或.csv文件到此目录")
            return False
        
        logger.info(f"找到 {len(supported_files)} 个支持的文档文件")
        
        # 尝试加载文档
        try:
            start_time = time.time()
            documents = self.rag.load_documents()
            end_time = time.time()
            
            if documents:
                logger.info(f"成功加载 {len(documents)} 个文档片段，耗时 {end_time - start_time:.2f} 秒")
                return True
            else:
                logger.error("文档加载失败或没有文档内容")
                return False
        except Exception as e:
            logger.error(f"文档加载过程中出现错误: {str(e)}")
            return False
    
    def test_initialization(self) -> bool:
        """测试RAG系统初始化
        
        Returns:
            bool: 测试是否通过
        """
        logger.info("测试: RAG系统初始化")
        
        try:
            start_time = time.time()
            self.rag.initialize()
            end_time = time.time()
            
            if self.rag.vector_store:
                logger.info(f"成功初始化向量存储，耗时 {end_time - start_time:.2f} 秒")
                return True
            else:
                logger.error("向量存储初始化失败")
                return False
        except Exception as e:
            logger.error(f"RAG系统初始化过程中出现错误: {str(e)}")
            return False
    
    def test_search(self, query: str) -> bool:
        """测试搜索功能
        
        Args:
            query: 搜索查询文本
            
        Returns:
            bool: 测试是否通过
        """
        logger.info(f"测试: 搜索功能 - 查询: '{query}'")
        
        try:
            start_time = time.time()
            results = self.rag.search_medical_context(query)
            end_time = time.time()
            
            if results:
                logger.info(f"成功找到 {len(results)} 个相关结果，耗时 {end_time - start_time:.2f} 秒")
                
                if self.verbose:
                    for i, result in enumerate(results, 1):
                        logger.debug(f"结果 {i}:")
                        logger.debug(f"内容: {result['content'][:100]}...")
                        logger.debug(f"相似度得分: {result['score']}")
                        logger.debug(f"元数据: {result['metadata']}")
                        logger.debug("-" * 50)
                
                return True
            else:
                logger.warning(f"未找到与查询 '{query}' 相关的结果")
                return False
        except Exception as e:
            logger.error(f"搜索过程中出现错误: {str(e)}")
            return False
    
    def test_medical_context(self, text: str) -> bool:
        """测试获取医学上下文功能
        
        Args:
            text: 需要查找上下文的文本
            
        Returns:
            bool: 测试是否通过
        """
        logger.info(f"测试: 获取医学上下文 - 文本: '{text[:50]}...'")
        
        try:
            start_time = time.time()
            context = self.rag.get_medical_context(text)
            end_time = time.time()
            
            if context and context != "未找到相关医学参考信息。":
                logger.info(f"成功获取医学上下文，耗时 {end_time - start_time:.2f} 秒")
                
                if self.verbose:
                    logger.debug(f"医学上下文:\n{context[:500]}...")
                
                return True
            else:
                logger.warning(f"未找到与文本相关的医学上下文")
                logger.debug(f"返回结果: {context}")
                return False
        except Exception as e:
            logger.error(f"获取医学上下文过程中出现错误: {str(e)}")
            return False
    
    def run_all_tests(self, test_queries: List[str]) -> Dict[str, bool]:
        """运行所有测试
        
        Args:
            test_queries: 测试查询列表
            
        Returns:
            Dict[str, bool]: 测试结果字典
        """
        results = {}
        
        # 测试文档加载
        results["document_loading"] = self.test_document_loading()
        
        # 测试初始化
        results["initialization"] = self.test_initialization()
        
        # 如果初始化成功，进行搜索和上下文测试
        if results["initialization"]:
            # 测试搜索功能
            search_results = []
            for query in test_queries:
                search_results.append(self.test_search(query))
            results["search"] = any(search_results)
            
            # 测试获取医学上下文
            context_results = []
            for query in test_queries:
                context_results.append(self.test_medical_context(query))
            results["medical_context"] = any(context_results)
        
        return results

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="医学RAG系统独立测试工具")
    parser.add_argument("--docs-dir", help="医学文档目录路径", default=None)
    parser.add_argument("--queries", nargs="+", help="测试查询列表", 
                        default=["糖尿病的症状和治疗", "高血压的病因", "心脏病的预防措施"])
    parser.add_argument("--verbose", action="store_true", help="显示详细日志")
    parser.add_argument("--test", help="单独运行某个测试(document_loading/initialization/search/medical_context)", default=None)
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = MedicalRAGTester(docs_dir=args.docs_dir, verbose=args.verbose)
    
    # 运行测试
    if args.test:
        if args.test == "document_loading":
            result = tester.test_document_loading()
        elif args.test == "initialization":
            result = tester.test_initialization()
        elif args.test == "search":
            results = [tester.test_search(query) for query in args.queries]
            result = any(results)
        elif args.test == "medical_context":
            results = [tester.test_medical_context(query) for query in args.queries]
            result = any(results)
        else:
            logger.error(f"未知的测试类型: {args.test}")
            sys.exit(1)
        
        logger.info(f"测试 '{args.test}' {'通过' if result else '失败'}")
        sys.exit(0 if result else 1)
    else:
        # 运行所有测试
        results = tester.run_all_tests(args.queries)
        
        # 打印测试结果摘要
        logger.info("\n" + "=" * 50)
        logger.info("测试结果摘要:")
        logger.info("=" * 50)
        
        for test_name, result in results.items():
            status = "通过" if result else "失败"
            logger.info(f"{test_name:20}: {status}")
        
        all_passed = all(results.values())
        logger.info("=" * 50)
        logger.info(f"总体结果: {'全部通过' if all_passed else '部分测试失败'}")
        logger.info("=" * 50)
        
        sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main() 