"""
测试脚本 - 验证10个爬虫程序的基本功能
作者: 专业爬虫开发工程师
日期: 2026-03-15
"""

import os
import sys
import importlib.util
from typing import List, Dict
from datetime import datetime


def test_crawler(crawler_file: str, test_function: str = "main") -> bool:
    """
    测试单个爬虫程序
    
    Args:
        crawler_file: 爬虫文件路径
        test_function: 测试函数名，默认为main
        
    Returns:
        bool: 测试是否成功
    """
    try:
        print(f"\n{'='*60}")
        print(f"测试爬虫: {os.path.basename(crawler_file)}")
        print(f"{'='*60}")
        
        # 获取文件目录并添加到系统路径
        file_dir = os.path.dirname(crawler_file)
        if file_dir not in sys.path:
            sys.path.insert(0, file_dir)
        
        # 动态导入模块
        module_name = os.path.splitext(os.path.basename(crawler_file))[0]
        spec = importlib.util.spec_from_file_location(module_name, crawler_file)
        if spec is None:
            print(f"错误: 无法加载模块 {module_name}")
            return False
        
        module = importlib.util.module_from_spec(spec)
        
        # 设置超时，防止无限执行
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("测试超时")
        
        # 设置超时（60秒）
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(60)
        
        try:
            spec.loader.exec_module(module)
            
            # 检查是否有测试函数
            if hasattr(module, test_function):
                print(f"执行 {test_function}() 函数...")
                
                # 运行爬虫的主函数
                result = module.main()
                
                if result is not None:
                    print(f"爬虫执行成功，返回数据: {type(result)}")
                    if isinstance(result, list):
                        print(f"数据条数: {len(result)}")
                        if len(result) > 0:
                            print(f"第一条数据预览: {str(result[0])[:100]}...")
                else:
                    print("爬虫执行完成，但未返回数据")
                
                signal.alarm(0)  # 取消超时
                return True
            else:
                print(f"警告: 模块中没有 {test_function} 函数")
                print(f"可用函数: {[name for name in dir(module) if not name.startswith('_')]}")
                
                # 尝试创建实例并调用run方法
                if hasattr(module, 'run'):
                    print("尝试创建实例并调用run方法...")
                    for name in dir(module):
                        if not name.startswith('_') and name[0].isupper():
                            print(f"找到类: {name}")
                            cls = getattr(module, name)
                            if hasattr(cls, '__init__'):
                                try:
                                    # 创建实例
                                    instance = cls()
                                    if hasattr(instance, 'run'):
                                        print("调用run方法...")
                                        result = instance.run(save_to_file=False)
                                        print(f"爬虫执行成功，返回数据: {type(result)}")
                                        signal.alarm(0)
                                        return True
                                except Exception as e:
                                    print(f"创建实例时出错: {str(e)}")
                
                signal.alarm(0)
                return False
                
        except TimeoutError:
            print("错误: 测试超时（60秒）")
            return False
        except Exception as e:
            print(f"执行爬虫时出错: {str(e)}")
            signal.alarm(0)
            return False
            
    except Exception as e:
        print(f"测试爬虫时发生未知错误: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("开始测试10个爬虫程序...")
    print("="*60)
    
    crawlers_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 测试的爬虫文件列表
    crawler_files = [
        os.path.join(crawlers_dir, f"crawler_{i}.py") for i in range(41, 51)
    ]
    
    results = []
    
    for crawler_file in crawler_files:
        if os.path.exists(crawler_file):
            success = test_crawler(crawler_file)
            results.append((os.path.basename(crawler_file), success))
        else:
            print(f"错误: 文件不存在 {crawler_file}")
            results.append((os.path.basename(crawler_file), False))
    
    # 输出测试结果
    print("\n" + "="*60)
    print("测试结果汇总:")
    print("="*60)
    
    successful = 0
    failed = 0
    
    for filename, success in results:
        status = "✓ 成功" if success else "✗ 失败"
        print(f"{filename}: {status}")
        if success:
            successful += 1
        else:
            failed += 1
    
    print(f"\n总计: {len(results)} 个爬虫")
    print(f"成功: {successful} 个")
    print(f"失败: {failed} 个")
    
    # 生成测试报告
    report_file = os.path.join(crawlers_dir, "data", "test_report.txt")
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"爬虫测试报告 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
            
            for filename, success in results:
                status = "成功" if success else "失败"
                f.write(f"{filename}: {status}\n")
            
            f.write(f"\n总计: {len(results)} 个爬虫\n")
            f.write(f"成功: {successful} 个\n")
            f.write(f"失败: {failed} 个\n")
            f.write(f"成功率: {(successful/len(results))*100:.1f}%\n")
        
        print(f"\n测试报告已保存到: {report_file}")
    except Exception as e:
        print(f"保存测试报告时出错: {str(e)}")
    
    if failed > 0:
        print("\n警告: 有爬虫测试失败，请检查相关代码")
        sys.exit(1)
    else:
        print("\n所有爬虫测试成功！")
        sys.exit(0)


if __name__ == "__main__":
    main()