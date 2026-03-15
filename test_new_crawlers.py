#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新创建的爬虫程序 (crawler_11.py - crawler_20.py)
"""

import os
import sys
import importlib.util
import time
from typing import List, Dict, Tuple

def test_crawler_import(crawler_file: str) -> Tuple[bool, str]:
    """
    测试爬虫文件是否可以成功导入
    
    Args:
        crawler_file: 爬虫文件名
        
    Returns:
        (是否成功, 错误信息)
    """
    try:
        # 构建完整路径
        filepath = os.path.join(os.path.dirname(__file__), crawler_file)
        
        if not os.path.exists(filepath):
            return False, f"文件不存在: {crawler_file}"
        
        # 尝试导入模块
        spec = importlib.util.spec_from_file_location("crawler_module", filepath)
        if spec is None:
            return False, f"无法创建模块规范: {crawler_file}"
        
        module = importlib.util.module_from_spec(spec)
        sys.modules["crawler_module"] = module
        
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            return False, f"导入失败: {str(e)}"
        
        # 检查是否有主类（根据命名约定）
        module_name = crawler_file.replace('.py', '')
        
        # 尝试查找主要类（规则：文件名去掉crawler_和后缀，首字母大写 + Crawler）
        # 例如：crawler_11.py -> WeatherCrawler
        class_name_map = {
            'crawler_11': 'WeatherCrawler',
            'crawler_12': 'StockCrawler',
            'crawler_13': 'MovieCrawler',
            'crawler_14': 'GitHubCrawler',
            'crawler_15': 'RedditCrawler',
            'crawler_16': 'TechBlogCrawler',
            'crawler_17': 'PriceMonitorCrawler',
            'crawler_18': 'JobCrawler',
            'crawler_19': 'PaperCrawler',
            'crawler_20': 'ExchangeRateCrawler',
        }
        
        if module_name in class_name_map:
            class_name = class_name_map[module_name]
            if hasattr(module, class_name):
                return True, f"成功导入 {class_name} 类"
            else:
                return False, f"未找到 {class_name} 类"
        else:
            # 如果不在映射表中，尝试查找包含"Crawler"的类
            crawler_classes = [cls for cls in dir(module) if 'Crawler' in cls and not cls.startswith('_')]
            if crawler_classes:
                return True, f"找到爬虫类: {', '.join(crawler_classes)}"
            else:
                return True, "导入成功，但未找到标准爬虫类"
    
    except Exception as e:
        return False, f"测试过程中发生错误: {str(e)}"

def test_crawler_syntax(crawler_file: str) -> Tuple[bool, str]:
    """
    测试爬虫文件的语法
    
    Args:
        crawler_file: 爬虫文件名
        
    Returns:
        (语法是否正确, 错误信息)
    """
    try:
        filepath = os.path.join(os.path.dirname(__file__), crawler_file)
        
        # 使用Python编译检查语法
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        
        compile(source, crawler_file, 'exec')
        return True, "语法正确"
    
    except SyntaxError as e:
        return False, f"语法错误: {str(e)}"
    except Exception as e:
        return False, f"检查语法时发生错误: {str(e)}"

def test_crawler_dependencies(crawler_file: str) -> Tuple[bool, str]:
    """
    检查爬虫文件的依赖导入
    
    Args:
        crawler_file: 爬虫文件名
        
    Returns:
        (依赖是否正常, 错误信息)
    """
    try:
        filepath = os.path.join(os.path.dirname(__file__), crawler_file)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查常见依赖
        dependencies = []
        
        if 'import requests' in content or 'from requests' in content:
            dependencies.append('requests')
        
        if 'from bs4' in content or 'import BeautifulSoup' in content:
            dependencies.append('beautifulsoup4')
        
        if 'import feedparser' in content:
            dependencies.append('feedparser')
        
        if 'import pandas' in content:
            dependencies.append('pandas')
        
        if dependencies:
            return True, f"依赖库: {', '.join(dependencies)}"
        else:
            return True, "无外部依赖或依赖检查未覆盖"
    
    except Exception as e:
        return False, f"检查依赖时发生错误: {str(e)}"

def analyze_crawler_structure(crawler_file: str) -> Dict:
    """
    分析爬虫文件结构
    
    Args:
        crawler_file: 爬虫文件名
        
    Returns:
        结构分析结果
    """
    analysis = {
        'file': crawler_file,
        'size_bytes': 0,
        'line_count': 0,
        'class_count': 0,
        'function_count': 0,
        'has_main': False,
        'has_docstring': False,
    }
    
    try:
        filepath = os.path.join(os.path.dirname(__file__), crawler_file)
        
        # 获取文件大小
        analysis['size_bytes'] = os.path.getsize(filepath)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        analysis['line_count'] = len(lines)
        
        # 简单分析结构
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 检查是否有main函数
            if 'def main()' in line or 'def main():' in line:
                analysis['has_main'] = True
            
            # 检查是否有文档字符串（简单检查）
            if i == 0 and line.startswith('"""'):
                analysis['has_docstring'] = True
            elif i == 1 and lines[0].strip() == '#!/usr/bin/env python3' and line.startswith('"""'):
                analysis['has_docstring'] = True
            
            # 统计类和函数（简单统计）
            if line.startswith('class '):
                analysis['class_count'] += 1
            
            if line.startswith('def ') and not line.startswith('def __'):
                analysis['function_count'] += 1
    
    except Exception as e:
        analysis['error'] = str(e)
    
    return analysis

def main():
    """主测试函数"""
    print("测试新创建的爬虫程序 (crawler_11.py - crawler_20.py)")
    print("=" * 70)
    
    # 要测试的爬虫文件
    crawler_files = [f'crawler_{i}.py' for i in range(11, 21)]
    
    results = []
    
    for crawler_file in crawler_files:
        print(f"\n测试: {crawler_file}")
        print("-" * 50)
        
        # 检查文件是否存在
        filepath = os.path.join(os.path.dirname(__file__), crawler_file)
        if not os.path.exists(filepath):
            print(f"  [ERROR] 文件不存在")
            results.append((crawler_file, False, "文件不存在"))
            continue
        
        # 测试语法
        syntax_ok, syntax_msg = test_crawler_syntax(crawler_file)
        print(f"  语法检查: {'[OK]' if syntax_ok else '[ERROR]'} {syntax_msg}")
        
        # 测试导入
        import_ok, import_msg = test_crawler_import(crawler_file)
        print(f"  导入测试: {'[OK]' if import_ok else '[ERROR]'} {import_msg}")
        
        # 检查依赖
        dep_ok, dep_msg = test_crawler_dependencies(crawler_file)
        print(f"  依赖检查: {'[OK]' if dep_ok else '[ERROR]'} {dep_msg}")
        
        # 分析结构
        structure = analyze_crawler_structure(crawler_file)
        print(f"  结构分析: {structure['line_count']} 行, {structure['size_bytes']} 字节")
        print(f"            类: {structure['class_count']}, 函数: {structure['function_count']}")
        print(f"            main函数: {'有' if structure['has_main'] else '无'}")
        print(f"            文档字符串: {'有' if structure['has_docstring'] else '无'}")
        
        # 汇总结果
        overall_ok = syntax_ok and import_ok and dep_ok
        results.append((crawler_file, overall_ok, ""))
        
        # 添加延迟，避免输出太快
        time.sleep(0.1)
    
    # 打印汇总结果
    print("\n" + "=" * 70)
    print("测试结果汇总:")
    print("-" * 70)
    
    success_count = 0
    for crawler_file, overall_ok, _ in results:
        status = "[OK] 通过" if overall_ok else "[ERROR] 失败"
        print(f"  {crawler_file:15} {status}")
        if overall_ok:
            success_count += 1
    
    print("-" * 70)
    print(f"总计: {len(crawler_files)} 个爬虫")
    print(f"通过: {success_count} 个")
    print(f"失败: {len(crawler_files) - success_count} 个")
    
    if success_count == len(crawler_files):
        print("\n[SUCCESS] 所有爬虫程序测试通过!")
    else:
        print(f"\n[WARNING] {len(crawler_files) - success_count} 个爬虫需要检查")
    
    # 提供运行建议
    print("\n" + "=" * 70)
    print("运行建议:")
    print("1. 安装依赖: pip install requests beautifulsoup4 feedparser pandas")
    print("2. 运行单个爬虫演示: python crawler_11.py")
    print("3. 查看详细文档: 查看 README_NEW_CRAWLERS.md")
    print("4. 注意遵守各网站的robots.txt和使用条款")

if __name__ == "__main__":
    main()