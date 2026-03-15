#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫测试脚本
用于测试单个爬虫的基本功能
"""

import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(str(Path(__file__).parent.absolute()))

from utils import make_request, save_data, load_data, setup_logger
from config import DATA_DIR, LOG_DIR

# 设置日志
logger = setup_logger("crawler_tester", LOG_DIR / "test.log")

class CrawlerTester:
    """爬虫测试器"""
    
    def __init__(self):
        self.test_results = []
    
    def test_request(self, url: str) -> bool:
        """
        测试HTTP请求功能
        
        Args:
            url: 测试URL
            
        Returns:
            bool: 测试是否成功
        """
        logger.info(f"测试HTTP请求: {url}")
        
        try:
            response = make_request(url)
            if response and response.status_code == 200:
                logger.info(f"HTTP请求测试成功: {url}")
                return True
            else:
                logger.error(f"HTTP请求测试失败: {url}")
                return False
        except Exception as e:
            logger.error(f"HTTP请求测试异常: {e}")
            return False
    
    def test_parsing(self, html_content: str = None) -> bool:
        """
        测试HTML解析功能
        
        Args:
            html_content: HTML内容
            
        Returns:
            bool: 测试是否成功
        """
        logger.info("测试HTML解析功能")
        
        try:
            if html_content is None:
                # 使用示例HTML
                html_content = """
                <html>
                    <head><title>测试页面</title></head>
                    <body>
                        <h1>测试标题</h1>
                        <div class="content">测试内容</div>
                        <a href="/test">测试链接</a>
                    </body>
                </html>
                """
            
            # 测试BeautifulSoup解析
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "lxml")
            
            # 测试元素查找
            title = soup.find("title")
            h1 = soup.find("h1")
            links = soup.find_all("a")
            
            if title and h1:
                logger.info(f"HTML解析测试成功，找到标题: {title.text}")
                return True
            else:
                logger.error("HTML解析测试失败")
                return False
                
        except Exception as e:
            logger.error(f"HTML解析测试异常: {e}")
            return False
    
    def test_data_storage(self) -> bool:
        """
        测试数据存储功能
        
        Returns:
            bool: 测试是否成功
        """
        logger.info("测试数据存储功能")
        
        try:
            # 测试数据
            test_data = {
                "test_id": 1,
                "name": "测试数据",
                "value": 123.45,
                "timestamp": datetime.now().isoformat(),
                "items": ["item1", "item2", "item3"]
            }
            
            # 测试保存和加载
            filename = "test_storage"
            
            # 保存为JSON
            if save_data(test_data, filename, "json"):
                # 加载JSON
                loaded_data = load_data(filename, "json")
                if loaded_data and loaded_data.get("test_id") == 1:
                    logger.info("JSON存储测试成功")
                    
                    # 测试CSV存储（需要列表数据）
                    list_data = [test_data]
                    if save_data(list_data, filename, "csv"):
                        loaded_csv = load_data(filename, "csv")
                        if loaded_csv and len(loaded_csv) == 1:
                            logger.info("CSV存储测试成功")
                            return True
                    
                    return True
            
            logger.error("数据存储测试失败")
            return False
            
        except Exception as e:
            logger.error(f"数据存储测试异常: {e}")
            return False
    
    def test_crawler_module(self, module_path: str) -> bool:
        """
        测试爬虫模块
        
        Args:
            module_path: 模块路径
            
        Returns:
            bool: 测试是否成功
        """
        logger.info(f"测试爬虫模块: {module_path}")
        
        try:
            # 动态导入模块
            import importlib.util
            spec = importlib.util.spec_from_file_location("test_module", module_path)
            if spec is None:
                logger.error(f"无法加载模块: {module_path}")
                return False
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 检查必要的函数
            required_functions = ["main", "run_crawler", "fetch_data"]
            found_functions = []
            
            for func in required_functions:
                if hasattr(module, func):
                    found_functions.append(func)
            
            if found_functions:
                logger.info(f"模块测试成功，找到函数: {', '.join(found_functions)}")
                return True
            else:
                logger.error(f"模块测试失败，未找到必要函数")
                return False
                
        except Exception as e:
            logger.error(f"模块测试异常: {e}")
            return False
    
    def run_all_tests(self) -> Dict:
        """
        运行所有测试
        
        Returns:
            Dict: 测试结果
        """
        logger.info("开始运行所有测试")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {}
        }
        
        # 测试1: HTTP请求
        test1_result = {
            "name": "HTTP请求测试",
            "status": self.test_request("https://httpbin.org/get"),
            "description": "测试HTTP请求功能"
        }
        results["tests"].append(test1_result)
        
        # 测试2: HTML解析
        test2_result = {
            "name": "HTML解析测试",
            "status": self.test_parsing(),
            "description": "测试HTML解析功能"
        }
        results["tests"].append(test2_result)
        
        # 测试3: 数据存储
        test3_result = {
            "name": "数据存储测试",
            "status": self.test_data_storage(),
            "description": "测试数据存储功能"
        }
        results["tests"].append(test3_result)
        
        # 测试4: 查找爬虫模块
        crawler_files = list(Path(__file__).parent.glob("crawler_*.py"))
        if crawler_files:
            test4_result = {
                "name": "爬虫模块测试",
                "status": self.test_crawler_module(str(crawler_files[0])),
                "description": f"测试爬虫模块: {crawler_files[0].name}"
            }
            results["tests"].append(test4_result)
        
        # 计算统计
        total_tests = len(results["tests"])
        passed_tests = sum(1 for test in results["tests"] if test["status"])
        failed_tests = total_tests - passed_tests
        
        results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": f"{(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%"
        }
        
        # 保存测试结果
        self.save_test_results(results)
        
        # 打印结果
        self.print_test_results(results)
        
        return results
    
    def save_test_results(self, results: Dict):
        """保存测试结果"""
        try:
            test_file = DATA_DIR / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(test_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"测试结果已保存到: {test_file}")
            
        except Exception as e:
            logger.error(f"保存测试结果失败: {e}")
    
    def print_test_results(self, results: Dict):
        """打印测试结果"""
        print("\n" + "="*60)
        print("爬虫测试报告")
        print("="*60)
        
        for i, test in enumerate(results["tests"], 1):
            status = "✓ 通过" if test["status"] else "✗ 失败"
            print(f"{i:2d}. {test['name']:30} {status}")
            if not test["status"]:
                print(f"    描述: {test['description']}")
        
        print("\n" + "-"*60)
        summary = results["summary"]
        print(f"测试总数: {summary['total_tests']}")
        print(f"通过数: {summary['passed_tests']}")
        print(f"失败数: {summary['failed_tests']}")
        print(f"成功率: {summary['success_rate']}")
        print("="*60)

def main():
    """主函数"""
    tester = CrawlerTester()
    
    # 运行所有测试
    print("开始运行爬虫测试...")
    results = tester.run_all_tests()
    
    # 根据测试结果返回退出码
    if results["summary"]["failed_tests"] > 0:
        print("\n测试失败，请检查问题！")
        sys.exit(1)
    else:
        print("\n所有测试通过！")
        sys.exit(0)

if __name__ == "__main__":
    main()