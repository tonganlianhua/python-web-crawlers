#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫项目主运行脚本
用于批量运行所有爬虫程序
"""

import os
import sys
import time
import json
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加当前目录到Python路径
sys.path.append(str(Path(__file__).parent.absolute()))

from utils import setup_logger, ensure_directory
from config import DATA_DIR, LOG_DIR

# 设置日志
logger = setup_logger("crawler_runner", LOG_DIR / "run.log")

class CrawlerRunner:
    """爬虫运行器"""
    
    def __init__(self, max_workers: int = 5, timeout: int = 300):
        """
        初始化运行器
        
        Args:
            max_workers: 最大并行数
            timeout: 单个爬虫超时时间（秒）
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.results = []
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None,
            "duration": None
        }
        
        # 确保目录存在
        ensure_directory(DATA_DIR)
        ensure_directory(LOG_DIR)
    
    def find_crawlers(self, directory: Path) -> List[Path]:
        """
        查找爬虫文件
        
        Args:
            directory: 搜索目录
            
        Returns:
            List[Path]: 爬虫文件列表
        """
        crawlers = []
        pattern = "crawler_*.py"
        
        for filepath in directory.glob(pattern):
            if filepath.is_file():
                crawlers.append(filepath)
        
        return sorted(crawlers)
    
    def run_crawler(self, crawler_file: Path) -> Dict:
        """
        运行单个爬虫
        
        Args:
            crawler_file: 爬虫文件路径
            
        Returns:
            Dict: 运行结果
        """
        result = {
            "file": crawler_file.name,
            "status": "pending",
            "output": "",
            "error": "",
            "start_time": None,
            "end_time": None,
            "duration": None
        }
        
        try:
            logger.info(f"开始运行爬虫: {crawler_file.name}")
            result["start_time"] = datetime.now().isoformat()
            
            # 运行爬虫
            cmd = [sys.executable, str(crawler_file)]
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(crawler_file.parent)
            )
            
            result["end_time"] = datetime.now().isoformat()
            result["duration"] = (datetime.fromisoformat(result["end_time"]) - 
                                 datetime.fromisoformat(result["start_time"])).total_seconds()
            
            if process.returncode == 0:
                result["status"] = "success"
                result["output"] = process.stdout
                logger.info(f"爬虫运行成功: {crawler_file.name} (用时: {result['duration']:.2f}秒)")
            else:
                result["status"] = "failed"
                result["error"] = process.stderr
                logger.error(f"爬虫运行失败: {crawler_file.name}, 错误: {process.stderr}")
            
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
            result["error"] = f"爬虫运行超时 ({self.timeout}秒)"
            logger.error(f"爬虫运行超时: {crawler_file.name}")
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"运行爬虫时出错: {crawler_file.name}, 错误: {e}")
        
        return result
    
    def run_all(self, directory: Path = None, pattern: str = None) -> Dict:
        """
        运行所有爬虫
        
        Args:
            directory: 爬虫目录
            pattern: 文件匹配模式
            
        Returns:
            Dict: 运行统计
        """
        if directory is None:
            directory = Path(__file__).parent
        
        # 查找爬虫文件
        crawlers = self.find_crawlers(directory)
        if not crawlers:
            logger.warning(f"在目录 {directory} 中未找到爬虫文件")
            return self.stats
        
        logger.info(f"找到 {len(crawlers)} 个爬虫文件")
        self.stats["total"] = len(crawlers)
        self.stats["start_time"] = datetime.now().isoformat()
        
        # 并行运行爬虫
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_crawler = {
                executor.submit(self.run_crawler, crawler): crawler 
                for crawler in crawlers
            }
            
            # 收集结果
            for future in as_completed(future_to_crawler):
                crawler = future_to_crawler[future]
                try:
                    result = future.result()
                    self.results.append(result)
                    
                    if result["status"] == "success":
                        self.stats["success"] += 1
                    elif result["status"] == "failed":
                        self.stats["failed"] += 1
                    else:
                        self.stats["skipped"] += 1
                        
                except Exception as e:
                    logger.error(f"处理爬虫结果时出错: {crawler.name}, 错误: {e}")
                    self.stats["failed"] += 1
        
        # 更新统计
        self.stats["end_time"] = datetime.now().isoformat()
        start_dt = datetime.fromisoformat(self.stats["start_time"])
        end_dt = datetime.fromisoformat(self.stats["end_time"])
        self.stats["duration"] = (end_dt - start_dt).total_seconds()
        
        # 保存结果
        self.save_results()
        
        return self.stats
    
    def save_results(self):
        """保存运行结果"""
        try:
            result_file = DATA_DIR / f"run_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            result_data = {
                "stats": self.stats,
                "results": self.results,
                "summary": self.get_summary()
            }
            
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"运行结果已保存到: {result_file}")
            
            # 同时保存为CSV格式
            self.save_results_csv()
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
    
    def save_results_csv(self):
        """保存结果为CSV格式"""
        try:
            import pandas as pd
            
            csv_file = DATA_DIR / f"run_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # 转换为DataFrame
            df_data = []
            for result in self.results:
                row = {
                    "file": result["file"],
                    "status": result["status"],
                    "start_time": result.get("start_time", ""),
                    "end_time": result.get("end_time", ""),
                    "duration": result.get("duration", 0),
                    "error": result.get("error", "")[:200]  # 截断错误信息
                }
                df_data.append(row)
            
            df = pd.DataFrame(df_data)
            df.to_csv(csv_file, index=False, encoding="utf-8-sig")
            
            logger.info(f"CSV结果已保存到: {csv_file}")
            
        except Exception as e:
            logger.error(f"保存CSV结果失败: {e}")
    
    def get_summary(self) -> Dict:
        """
        获取运行摘要
        
        Returns:
            Dict: 运行摘要
        """
        success_rate = (self.stats["success"] / self.stats["total"] * 100) if self.stats["total"] > 0 else 0
        
        return {
            "success_rate": f"{success_rate:.1f}%",
            "avg_duration": sum(r.get("duration", 0) for r in self.results) / len(self.results) if self.results else 0,
            "failed_files": [r["file"] for r in self.results if r["status"] != "success"],
            "timestamp": datetime.now().isoformat()
        }
    
    def print_report(self):
        """打印运行报告"""
        print("\n" + "="*60)
        print("爬虫运行报告")
        print("="*60)
        
        print(f"总爬虫数: {self.stats['total']}")
        print(f"成功数: {self.stats['success']}")
        print(f"失败数: {self.stats['failed']}")
        print(f"跳过数: {self.stats['skipped']}")
        
        if self.stats['total'] > 0:
            success_rate = (self.stats["success"] / self.stats["total"] * 100)
            print(f"成功率: {success_rate:.1f}%")
        
        if self.stats['duration']:
            print(f"总用时: {self.stats['duration']:.2f}秒")
        
        print(f"开始时间: {self.stats['start_time']}")
        print(f"结束时间: {self.stats['end_time']}")
        
        # 显示失败的文件
        failed_files = [r["file"] for r in self.results if r["status"] != "success"]
        if failed_files:
            print("\n失败的文件:")
            for file in failed_files:
                print(f"  - {file}")
        
        print("\n" + "="*60)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="爬虫批量运行器")
    parser.add_argument("--dir", "-d", type=str, default=".", help="爬虫目录")
    parser.add_argument("--workers", "-w", type=int, default=5, help="并行工作数")
    parser.add_argument("--timeout", "-t", type=int, default=300, help="单个爬虫超时时间（秒）")
    parser.add_argument("--pattern", "-p", type=str, default="crawler_*.py", help="文件匹配模式")
    parser.add_argument("--output", "-o", type=str, help="输出目录")
    
    args = parser.parse_args()
    
    # 设置输出目录
    if args.output:
        global DATA_DIR, LOG_DIR
        DATA_DIR = Path(args.output) / "data"
        LOG_DIR = Path(args.output) / "logs"
    
    # 创建运行器
    runner = CrawlerRunner(max_workers=args.workers, timeout=args.timeout)
    
    # 运行爬虫
    print(f"开始运行爬虫，目录: {args.dir}, 工作数: {args.workers}")
    stats = runner.run_all(directory=Path(args.dir), pattern=args.pattern)
    
    # 打印报告
    runner.print_report()
    
    # 返回退出码
    if stats["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()