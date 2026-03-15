#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫05: 图片下载爬虫 - 高清壁纸下载
功能: 从壁纸网站批量下载高清图片，支持分类、关键词搜索、自动重命名
"""

import requests
from bs4 import BeautifulSoup
import os
import re
import time
from datetime import datetime
import logging
import threading
from queue import Queue
from typing import List, Dict, Optional
from urllib.parse import urljoin, quote
from PIL import Image
import io

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_05.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WallpaperDownloader:
    """壁纸下载爬虫"""
    
    def __init__(self, download_dir: str = "wallpapers"):
        """
        初始化壁纸下载器
        
        Args:
            download_dir: 下载目录
        """
        self.base_urls = {
            'wallhaven': 'https://wallhaven.cc',
            'unsplash': 'https://unsplash.com',
            'pexels': 'https://www.pexels.com',
            'bing': 'https://www.bing.com'
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 创建下载目录
        self.download_dir = download_dir
        os.makedirs(self.download_dir, exist_ok=True)
        
        # 创建分类目录
        self.category_dirs = {
            'nature': os.path.join(download_dir, 'nature'),
            'anime': os.path.join(download_dir, 'anime'),
            'abstract': os.path.join(download_dir, 'abstract'),
            'city': os.path.join(download_dir, 'city'),
            'space': os.path.join(download_dir, 'space'),
            'other': os.path.join(download_dir, 'other')
        }
        
        for dir_path in self.category_dirs.values():
            os.makedirs(dir_path, exist_ok=True)
        
        # 下载队列
        self.download_queue = Queue()
        self.download_threads = []
        self.max_threads = 5
        
        logger.info(f"壁纸下载器初始化完成，下载目录: {download_dir}")
    
    def search_wallpapers(self, site: str, keyword: str = "", page: int = 1) -> List[Dict]:
        """
        搜索壁纸
        
        Args:
            site: 网站名称 (wallhaven, unsplash, pexels)
            keyword: 搜索关键词
            page: 页码
            
        Returns:
            壁纸信息列表
        """
        wallpapers = []
        
        try:
            if site == 'wallhaven':
                return self._search_wallhaven(keyword, page)
            elif site == 'unsplash':
                return self._search_unsplash(keyword, page)
            elif site == 'pexels':
                return self._search_pexels(keyword, page)
            elif site == 'bing':
                return self._get_bing_daily(page)
            else:
                logger.warning(f"不支持的网站: {site}")
                return []
                
        except Exception as e:
            logger.error(f"搜索壁纸失败: {e}")
            return wallpapers
    
    def _search_wallhaven(self, keyword: str, page: int) -> List[Dict]:
        """搜索Wallhaven壁纸"""
        try:
            search_url = f"{self.base_urls['wallhaven']}/search"
            
            params = {
                'q': keyword,
                'page': page
            }
            
            response = self.session.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找壁纸缩略图
            thumbnails = soup.select('figure.thumb')
            
            for thumb in thumbnails:
                try:
                    wallpaper = {}
                    
                    # 获取壁纸ID
                    link_elem = thumb.find('a', class_='preview')
                    if link_elem:
                        href = link_elem.get('href', '')
                        wallpaper['id'] = href.split('/')[-1]
                        wallpaper['url'] = href
                    
                    # 获取预览图
                    img_elem = thumb.find('img')
                    if img_elem:
                        wallpaper['thumbnail'] = img_elem.get('data-src') or img_elem.get('src')
                        wallpaper['thumbnail'] = 'https:' + wallpaper['thumbnail'] if wallpaper['thumbnail'].startswith('//') else wallpaper['thumbnail']
                    
                    # 获取分辨率
                    resolution_elem = thumb.find('span', class_='wall-res')
                    if resolution_elem:
                        wallpaper['resolution'] = resolution_elem.get_text(strip=True)
                    
                    # 获取文件大小
                    filesize_elem = thumb.find('span', class_='filesize')
                    if filesize_elem:
                        wallpaper['filesize'] = filesize_elem.get_text(strip=True)
                    
                    # 获取分类标签
                    tags = []
                    tag_elems = thumb.select('.tagname')
                    for tag in tag_elems:
                        tags.append(tag.get_text(strip=True))
                    
                    if tags:
                        wallpaper['tags'] = tags
                        # 自动分类
                        wallpaper['category'] = self._auto_categorize(tags)
                    
                    if wallpaper.get('id'):
                        wallpaper['site'] = 'wallhaven'
                        wallpaper['crawled_at'] = datetime.now().isoformat()
                        wallpapers.append(wallpaper)
                        
                except Exception as e:
                    logger.debug(f"处理壁纸条目时出错: {e}")
                    continue
            
            logger.info(f"从Wallhaven找到 {len(wallpapers)} 张壁纸")
            return wallpapers
            
        except Exception as e:
            logger.error(f"搜索Wallhaven失败: {e}")
            return []
    
    def _search_unsplash(self, keyword: str, page: int) -> List[Dict]:
        """搜索Unsplash壁纸"""
        try:
            if keyword:
                search_url = f"{self.base_urls['unsplash']}/search/photos"
                params = {'query': keyword, 'page': page}
            else:
                search_url = f"{self.base_urls['unsplash']}/photos"
                params = {'page': page}
            
            response = self.session.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Unsplash使用JSON数据，尝试解析
            script_tags = soup.find_all('script')
            wallpapers = []
            
            for script in script_tags:
                if 'window.__APOLLO_STATE__' in str(script):
                    # 这是一个简化的解析，实际需要更复杂的JSON解析
                    # 这里我们使用备用方法：直接解析HTML
                    break
            
            # 备用方法：从HTML中解析
            photo_items = soup.select('[data-testid="photo-card"]')
            
            for item in photo_items:
                try:
                    wallpaper = {}
                    
                    # 获取图片链接
                    img_elem = item.find('img')
                    if img_elem:
                        wallpaper['thumbnail'] = img_elem.get('src')
                        # 尝试获取高分辨率版本
                        srcset = img_elem.get('srcset', '')
                        if srcset:
                            # 取最大的那个
                            srcs = srcset.split(',')
                            if srcs:
                                largest = srcs[-1].strip().split(' ')[0]
                                wallpaper['url'] = largest
                    
                    # 获取描述
                    alt_text = img_elem.get('alt', '') if img_elem else ''
                    wallpaper['description'] = alt_text
                    
                    # 获取作者
                    author_elem = item.select_one('[data-testid="author-name"]')
                    if author_elem:
                        wallpaper['author'] = author_elem.get_text(strip=True)
                    
                    if wallpaper.get('url'):
                        wallpaper['id'] = hashlib.md5(wallpaper['url'].encode()).hexdigest()[:8]
                        wallpaper['site'] = 'unsplash'
                        wallpaper['category'] = self._auto_categorize([keyword] if keyword else [])
                        wallpaper['crawled_at'] = datetime.now().isoformat()
                        wallpapers.append(wallpaper)
                        
                except Exception as e:
                    logger.debug(f"处理Unsplash条目时出错: {e}")
                    continue
            
            logger.info(f"从Unsplash找到 {len(wallpapers)} 张壁纸")
            return wallpapers
            
        except Exception as e:
            logger.error(f"搜索Unsplash失败: {e}")
            return []
    
    def _search_pexels(self, keyword: str, page: int) -> List[Dict]:
        """搜索Pexels壁纸"""
        try:
            if keyword:
                search_url = f"{self.base_urls['pexels']}/search/{quote(keyword)}"
            else:
                search_url = f"{self.base_urls['pexels']}/photos/"
            
            if page > 1:
                search_url += f"?page={page}"
            
            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            photo_items = soup.select('article.photo-item')
            wallpapers = []
            
            for item in photo_items:
                try:
                    wallpaper = {}
                    
                    # 获取图片
                    img_elem = item.find('img')
                    if img_elem:
                        wallpaper['thumbnail'] = img_elem.get('src')
                        # Pexels的图片URL在data-big-src属性中
                        data_big = img_elem.get('data-big-src') or img_elem.get('data-src')
                        if data_big:
                            wallpaper['url'] = data_big
                    
                    # 获取描述
                    alt_text = img_elem.get('alt', '') if img_elem else ''
                    wallpaper['description'] = alt_text
                    
                    # 获取作者
                    author_elem = item.select_one('.js-photo-author')
                    if author_elem:
                        wallpaper['author'] = author_elem.get_text(strip=True)
                    
                    # 获取尺寸
                    size_elem = item.select_one('.photo-item__stats')
                    if size_elem:
                        size_text = size_elem.get_text(strip=True)
                        # 提取分辨率
                        res_match = re.search(r'(\d+)\s*×\s*(\d+)', size_text)
                        if res_match:
                            wallpaper['resolution'] = f"{res_match.group(1)}x{res_match.group(2)}"
                    
                    if wallpaper.get('url'):
                        wallpaper['id'] = hashlib.md5(wallpaper['url'].encode()).hexdigest()[:8]
                        wallpaper['site'] = 'pexels'
                        wallpaper['category'] = self._auto_categorize([keyword] if keyword else [])
                        wallpaper['crawled_at'] = datetime.now().isoformat()
                        wallpapers.append(wallpaper)
                        
                except Exception as e:
                    logger.debug(f"处理Pexels条目时出错: {e}")
                    continue
            
            logger.info(f"从Pexels找到 {len(wallpapers)} 张壁纸")
            return wallpapers
            
        except Exception as e:
            logger.error(f"搜索Pexels失败: {e}")
            return []
    
    def _get_bing_daily(self, page: int) -> List[Dict]:
        """获取Bing每日壁纸"""
        try:
            # Bing每日壁纸API
            api_url = "https://www.bing.com/HPImageArchive.aspx"
            
            params = {
                'format': 'js',
                'idx': (page - 1) * 8,  # 偏移量
                'n': 8,  # 获取数量
                'mkt': 'zh-CN'
            }
            
            response = self.session.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            wallpapers = []
            
            for image in data['images']:
                wallpaper = {
                    'id': image['hsh'],
                    'url': f"https://www.bing.com{image['url']}",
                    'thumbnail': f"https://www.bing.com{image['url'].replace('1920x1080', '640x480')}",
                    'title': image['title'],
                    'copyright': image['copyright'],
                    'copyrightlink': image['copyrightlink'],
                    'description': image.get('desc', ''),
                    'site': 'bing',
                    'category': 'nature',  # Bing壁纸多为自然风景
                    'crawled_at': datetime.now().isoformat()
                }
                wallpapers.append(wallpaper)
            
            logger.info(f"从Bing获取到 {len(wallpapers)} 张每日壁纸")
            return wallpapers
            
        except Exception as e:
            logger.error(f"获取Bing每日壁纸失败: {e}")
            return []
    
    def _auto_categorize(self, tags: List[str]) -> str:
        """根据标签自动分类"""
        category_keywords = {
            'nature': ['nature', 'landscape', 'forest', 'mountain', 'sea', 'ocean', 'sky', 'flower', 'tree'],
            'anime': ['anime', 'manga', 'cartoon', 'character', 'game', 'artwork'],
            'abstract': ['abstract', 'pattern', 'texture', 'color', 'gradient'],
            'city': ['city', 'urban', 'building', 'architecture', 'street', 'night'],
            'space': ['space', 'galaxy', 'star', 'planet', 'universe', 'nebula']
        }
        
        tags_lower = [tag.lower() for tag in tags]
        
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                for tag in tags_lower:
                    if keyword in tag:
                        return category
        
        return 'other'
    
    def download_wallpaper(self, wallpaper: Dict, quality: str = 'high') -> bool:
        """
        下载单张壁纸
        
        Args:
            wallpaper: 壁纸信息
            quality: 图片质量 (high, medium, low)
            
        Returns:
            是否下载成功
        """
        try:
            # 获取下载URL
            if quality == 'high' and 'url' in wallpaper:
                download_url = wallpaper['url']
            elif 'thumbnail' in wallpaper:
                download_url = wallpaper['thumbnail']
            else:
                logger.warning("无可用下载链接")
                return False
            
            # 确定保存目录
            category = wallpaper.get('category', 'other')
            save_dir = self.category_dirs.get(category, self.category_dirs['other'])
            
            # 生成文件名
            filename = self._generate_filename(wallpaper)
            save_path = os.path.join(save_dir, filename)
            
            # 检查文件是否已存在
            if os.path.exists(save_path):
                logger.info(f"文件已存在: {filename}")
                return True
            
            logger.info(f"开始下载: {filename}")
            
            # 下载图片
            response = self.session.get(download_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # 检查图片类型
            content_type = response.headers.get('content-type', '')
            if 'image' not in content_type:
                logger.warning(f"非图片内容: {content_type}")
                return False
            
            # 保存图片
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 验证图片
            try:
                with Image.open(save_path) as img:
                    img.verify()
                
                # 获取图片信息
                with Image.open(save_path) as img:
                    wallpaper['actual_width'] = img.width
                    wallpaper['actual_height'] = img.height
                    wallpaper['actual_size'] = os.path.getsize(save_path)
                    wallpaper['format'] = img.format
                
                logger.info(f"下载成功: {filename} ({img.width}x{img.height}, {wallpaper['actual_size']:,} bytes)")
                
                # 保存壁纸信息
                info_path = save_path + '.json'
                with open(info_path, 'w', encoding='utf-8') as f:
                    json.dump(wallpaper, f, ensure_ascii=False, indent=2)
                
                return True
                
            except Exception as e:
                logger.error(f"图片验证失败: {e}")
                os.remove(save_path)  # 删除损坏的文件
                return False
                
        except Exception as e:
            logger.error(f"下载壁纸失败: {e}")
            return False
    
    def _generate_filename(self, wallpaper: Dict) -> str:
        """生成文件名"""
        # 使用ID或创建哈希
        if 'id' in wallpaper:
            base_name = wallpaper['id']
        else:
            import hashlib
            url = wallpaper.get('url', wallpaper.get('thumbnail', ''))
            base_name = hashlib.md5(url.encode()).hexdigest()[:12]
        
        # 添加描述（清理非法字符）
        description = wallpaper.get('description', wallpaper.get('title', ''))
        if description:
            # 清理文件名中的非法字符
            clean_desc = re.sub(r'[<>:"/\\|?*]', '', description)
            clean_desc = clean_desc.replace(' ', '_')[:50]
            base_name = f"{clean_desc}_{base_name}"
        
        # 添加扩展名
        url = wallpaper.get('url', wallpaper.get('thumbnail', ''))
        extension = '.jpg'  # 默认扩展名
        
        if url:
            # 从URL提取扩展名
            ext_match = re.search(r'\.(jpg|jpeg|png|gif|bmp|webp)(?:$|\?)', url.lower())
            if ext_match:
                extension = '.' + ext_match.group(1)
        
        return f"{base_name}{extension}"
    
    def download_worker(self):
        """下载工作线程"""
        while True:
            try:
                wallpaper = self.download_queue.get()
                if wallpaper is None:  # 终止信号
                    break
                
                self.download_wallpaper(wallpaper)
                self.download_queue.task_done()
                
            except Exception as e:
                logger.error(f"下载工作线程出错: {e}")
                self.download_queue.task_done()
    
    def batch_download(self, wallpapers: List[Dict], max_concurrent: int = 5):
        """
        批量下载壁纸
        
        Args:
            wallpapers: 壁纸列表
            max_concurrent: 最大并发数
        """
        if not wallpapers:
            logger.warning("无壁纸可下载")
            return
        
        logger.info(f"开始批量下载 {len(wallpapers)} 张壁纸")
        
        # 启动工作线程
        self.max_threads = min(max_concurrent, 10)  # 限制最大线程数
        self.download_threads = []
        
        for i in range(self.max_threads):
            thread = threading.Thread(target=self.download_worker, daemon=True)
            thread.start()
            self.download_threads.append(thread)
        
        # 添加任务到队列
        for wallpaper in wallpapers:
            self.download_queue.put(wallpaper)
        
        # 等待所有任务完成
        self.download_queue.join()
        
        # 停止工作线程
        for _ in range(self.max_threads):
            self.download_queue.put(None)
        
        for thread in self.download_threads:
            thread.join(timeout=5)
        
        logger.info("批量下载完成")

def main():
    """主函数"""
    try:
        print("=== 高清壁纸下载爬虫 ===")
        
        downloader = WallpaperDownloader()
        
        print("\n选择壁纸来源:")
        print("1. Wallhaven (高质量壁纸)")
        print("2. Unsplash (免费高质量图片)")
        print("3. Pexels (免费素材)")
        print("4. Bing每日壁纸")
        
        site_choice = input("请选择 (1-4): ").strip()
        sites = ['wallhaven', 'unsplash', 'pexels', 'bing']
        
        if site_choice.isdigit() and 1 <= int(site_choice) <= 4:
            site = sites[int(site_choice) - 1]
        else:
            print("无效选择，使用默认: Wallhaven")
            site = 'wallhaven'
        
        keyword = ""
        if site != 'bing':
            keyword = input("请输入搜索关键词 (留空获取热门): ").strip()
        
        page = input("页码 (默认1): ").strip()
        page = int(page) if page.isdigit() else 1
        
        # 搜索壁纸
        print(f"\n正在搜索 {site} 的壁纸...")
        wallpapers = downloader.search_wallpapers(site, keyword, page)
        
        if wallpapers:
            print(f"\n找到 {len(wallpapers)} 张壁纸:")
            for i, wp in enumerate(wallpapers[:10], 1):
                title = wp.get('title') or wp.get('description') or wp.get('id', '未知')
                res = wp.get('resolution', '未知分辨率')
                print(f"{i}. {title[:50]}... ({res})")
            
            # 选择下载方式
            print("\n下载选项:")
            print("1. 下载全部")
            print("2. 选择下载")
            print("3. 仅查看")
            
            dl_choice = input("请选择 (1-3): ").strip()
            
            if dl_choice == '1':
                # 批量下载
                max_dl = input("最大并发数 (默认5): ").strip()
                max_concurrent = int(max_dl) if max_dl.isdigit() else 5
                
                downloader.batch_download(wallpapers, max_concurrent)
                
            elif dl_choice == '2':
                # 选择下载
                selections = input("请输入要下载的编号 (用逗号分隔，如: 1,3,5): ").strip()
                if selections:
                    selected = []
                    for sel in selections.split(','):
                        if sel.strip().isdigit():
                            idx = int(sel.strip()) - 1
                            if 0 <= idx < len(wallpapers):
                                selected.append(wallpapers[idx])
                    
                    if selected:
                        downloader.batch_download(selected, max_concurrent=3)
                    else:
                        print("无有效选择")
                else:
                    print("未选择任何壁纸")
                    
            else:
                print("仅查看模式，不下载")
                
            # 显示统计信息
            print("\n=== 统计信息 ===")
            categories = {}
            for wp in wallpapers:
                cat = wp.get('category', 'other')
                categories[cat] = categories.get(cat, 0) + 1
            
            for cat, count in categories.items():
                print(f"{cat}: {count}张")
            
        else:
            print("未找到壁纸")
            
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()