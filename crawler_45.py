"""
爬虫 45: 京东商品评论爬虫
功能: 爬取京东商品评论、评分和用户评价
作者: 专业爬虫开发工程师
日期: 2026-03-15
"""

import requests
import json
import time
import hashlib
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import random
import re
import csv
from urllib.parse import quote


class JDCommentCrawler:
    """京东评论爬虫类"""
    
    def __init__(self, headers: Optional[Dict] = None, proxy: Optional[Dict] = None):
        """
        初始化爬虫
        
        Args:
            headers: 请求头，默认为None时使用默认headers
            proxy: 代理设置，默认为None
        """
        # 京东API相关URL
        self.base_api = "https://api.m.jd.com"
        self.comment_api = f"{self.base_api}/client.action"
        self.product_api = f"{self.base_api}/api"
        self.search_api = f"{self.base_api}/search"
        
        # 默认请求头
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://item.jd.com/',
            'Origin': 'https://item.jd.com',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        }
        
        self.proxy = proxy
        self.session = requests.Session()
        
        # 错误处理
        self.error_count = 0
        self.max_retries = 3
        
        # 缓存
        self.product_cache = {}
        self.comment_cache = {}
        
    def search_products(self, keyword: str, page: int = 1, page_size: int = 20) -> Optional[List[Dict]]:
        """
        搜索京东商品
        
        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
            
        Returns:
            List[Dict]: 商品列表
        """
        try:
            print(f"[{datetime.now()}] 开始搜索京东商品: {keyword} (第{page}页)")
            
            # 京东搜索参数
            params = {
                'keyword': keyword,
                'page': page,
                'pageSize': min(page_size, 60),
                'sort': 'sort_rank_asc',  # 综合排序
                'searchType': 'search',
            }
            
            time.sleep(random.uniform(2, 3))
            
            # 构造搜索URL
            search_url = f"https://search.jd.com/Search"
            
            response = self.session.get(
                search_url,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=15
            )
            
            if response.status_code != 200:
                print(f"搜索商品失败，状态码: {response.status_code}")
                return self._retry_search_products(keyword, page, page_size)
            
            # 解析HTML获取商品信息
            products = self._parse_search_results(response.text)
            
            print(f"[{datetime.now()}] 成功搜索到 {len(products)} 个商品")
            return products
            
        except requests.exceptions.Timeout:
            print("搜索商品请求超时")
            return self._retry_search_products(keyword, page, page_size)
        except requests.exceptions.ConnectionError:
            print("搜索商品连接错误")
            return self._retry_search_products(keyword, page, page_size)
        except Exception as e:
            print(f"搜索商品时发生未知错误: {str(e)}")
            return None
    
    def _parse_search_results(self, html: str) -> List[Dict]:
        """
        解析搜索结果的HTML
        
        Args:
            html: 搜索结果HTML
            
        Returns:
            List[Dict]: 商品列表
        """
        products = []
        
        try:
            # 使用正则表达式提取商品信息
            # 商品列表容器
            import re
            
            # 提取商品信息
            product_pattern = r'<li class="gl-item".*?data-sku="(\d+)".*?>.*?<div class="p-img".*?<a href="(.*?)".*?>.*?<img.*?src="(.*?)".*?>.*?</a>.*?</div>.*?<div class="p-name".*?<a.*?title="(.*?)".*?>.*?</a>.*?</div>.*?<div class="p-price".*?<strong.*?<i>(.*?)</i>.*?</strong>.*?</div>'
            
            matches = re.findall(product_pattern, html, re.DOTALL)
            
            for match in matches:
                try:
                    sku_id, href, img, title, price = match
                    
                    # 清理数据
                    title = re.sub(r'\s+', ' ', title).strip()
                    price = price.replace('¥', '').strip()
                    
                    product = {
                        'sku_id': sku_id,
                        'title': title,
                        'price': float(price) if price.replace('.', '').isdigit() else 0,
                        'image_url': f"https:{img}" if img.startswith('//') else img,
                        'url': f"https:{href}" if href.startswith('//') else f"https://item.jd.com/{sku_id}.html",
                        'search_rank': len(products) + 1,
                    }
                    
                    products.append(product)
                    
                except Exception as e:
                    print(f"解析商品信息时出错: {str(e)}")
                    continue
            
            # 如果没有提取到，尝试另一种模式
            if not products:
                sku_pattern = r'data-sku="(\d+)"'
                sku_matches = re.findall(sku_pattern, html)
                
                for sku_id in sku_matches[:20]:  # 只取前20个
                    try:
                        product = {
                            'sku_id': sku_id,
                            'title': f"商品_{sku_id}",
                            'price': 0,
                            'image_url': '',
                            'url': f"https://item.jd.com/{sku_id}.html",
                            'search_rank': len(products) + 1,
                        }
                        products.append(product)
                    except:
                        continue
            
        except Exception as e:
            print(f"解析搜索结果时出错: {str(e)}")
        
        return products
    
    def _retry_search_products(self, keyword: str, page: int, page_size: int) -> Optional[List[Dict]]:
        """
        重试搜索商品
        
        Returns:
            List[Dict]: 商品列表
        """
        self.error_count += 1
        
        if self.error_count <= self.max_retries:
            wait_time = 2 ** self.error_count
            print(f"第 {self.error_count} 次重试，等待 {wait_time} 秒...")
            time.sleep(wait_time)
            return self.search_products(keyword, page, page_size)
        else:
            print(f"重试 {self.max_retries} 次后仍然失败")
            return None
    
    def get_product_detail(self, sku_id: str) -> Optional[Dict]:
        """
        获取商品详细信息
        
        Args:
            sku_id: 商品SKU ID
            
        Returns:
            Dict: 商品详细信息
        """
        # 检查缓存
        if sku_id in self.product_cache:
            print(f"从缓存获取商品 {sku_id} 的详细信息")
            return self.product_cache[sku_id]
        
        try:
            print(f"[{datetime.now()}] 开始获取商品详细信息: {sku_id}")
            
            # 京东商品详情API
            params = {
                'appid': 'item-v3',
                'functionId': 'pc_club_productPageComments',
                'client': 'pc',
                'clientVersion': '1.0.0',
                'sku': sku_id,
                'score': 0,  # 全部评价
                'sortType': 5,  # 推荐排序
                'page': 0,
                'pageSize': 10,
                'isShadowSku': 0,
                'fold': 1,
            }
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                self.comment_api,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取商品详情失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if not data.get('success'):
                print(f"获取商品详情错误: {data.get('message', '未知错误')}")
                return None
            
            product_data = data.get('productCommentSummary', {})
            
            # 解析商品信息
            detail = {
                'sku_id': sku_id,
                'product_id': product_data.get('productId', ''),
                'product_name': product_data.get('name', ''),
                'good_rate': product_data.get('goodRate', 0),  # 好评率
                'general_rate': product_data.get('generalRate', 0),  # 中评率
                'poor_rate': product_data.get('poorRate', 0),  # 差评率
                'comment_count': product_data.get('commentCount', 0),  # 评价总数
                'good_count': product_data.get('goodCount', 0),  # 好评数
                'general_count': product_data.get('generalCount', 0),  # 中评数
                'poor_count': product_data.get('poorCount', 0),  # 差评数
                'image_list_count': product_data.get('imageListCount', 0),  # 晒图数
                'video_count': product_data.get('videoCount', 0),  # 视频晒单数
                'after_count': product_data.get('afterCount', 0),  # 追评数
                'score': product_data.get('score', 0),  # 综合评分
                'default_good_count': product_data.get('defaultGoodCount', 0),
                'average_score': product_data.get('averageScore', 0),  # 平均分
                'url': f"https://item.jd.com/{sku_id}.html",
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            # 尝试获取更多商品信息
            try:
                # 从商品页面获取更多信息
                product_page = self._get_product_page_info(sku_id)
                if product_page:
                    detail.update(product_page)
            except:
                pass
            
            # 缓存数据
            self.product_cache[sku_id] = detail
            
            print(f"[{datetime.now()}] 成功获取商品详细信息")
            return detail
            
        except Exception as e:
            print(f"获取商品详细信息时出错: {str(e)}")
            return None
    
    def _get_product_page_info(self, sku_id: str) -> Optional[Dict]:
        """
        从商品页面获取更多信息
        
        Args:
            sku_id: 商品SKU ID
            
        Returns:
            Dict: 商品页面信息
        """
        try:
            url = f"https://item.jd.com/{sku_id}.html"
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                url,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                return None
            
            html = response.text
            
            # 提取商品信息
            info = {}
            
            # 提取品牌
            brand_match = re.search(r'品牌：</dt>.*?<dd.*?>(.*?)</dd>', html, re.DOTALL)
            if brand_match:
                info['brand'] = re.sub(r'<.*?>', '', brand_match.group(1)).strip()
            
            # 提取型号
            model_match = re.search(r'商品名称：</dt>.*?<dd.*?>(.*?)</dd>', html, re.DOTALL)
            if model_match:
                info['model'] = re.sub(r'<.*?>', '', model_match.group(1)).strip()
            
            # 提取店铺
            shop_match = re.search(r'店铺：</dt>.*?<dd.*?>(.*?)</dd>', html, re.DOTALL)
            if shop_match:
                info['shop'] = re.sub(r'<.*?>', '', shop_match.group(1)).strip()
            
            return info
            
        except:
            return None
    
    def get_product_comments(self, sku_id: str, page: int = 1, page_size: int = 10, 
                            score_type: int = 0) -> Optional[List[Dict]]:
        """
        获取商品评论
        
        Args:
            sku_id: 商品SKU ID
            page: 页码
            page_size: 每页数量
            score_type: 评价类型 0=全部, 1=好评, 2=中评, 3=差评, 4=晒图, 5=视频
            
        Returns:
            List[Dict]: 评论列表
        """
        try:
            print(f"[{datetime.now()}] 开始获取商品评论: {sku_id} (第{page}页, 类型:{score_type})")
            
            cache_key = f"{sku_id}_{page}_{score_type}"
            if cache_key in self.comment_cache:
                print(f"从缓存获取评论数据")
                return self.comment_cache[cache_key]
            
            params = {
                'appid': 'item-v3',
                'functionId': 'pc_club_productPageComments',
                'client': 'pc',
                'clientVersion': '1.0.0',
                'sku': sku_id,
                'score': score_type,
                'sortType': 5,  # 推荐排序
                'page': page - 1,  # 京东API从0开始
                'pageSize': min(page_size, 100),
                'isShadowSku': 0,
                'fold': 1,
            }
            
            time.sleep(random.uniform(1, 2))
            
            response = self.session.get(
                self.comment_api,
                params=params,
                headers=self.headers,
                proxies=self.proxy,
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"获取评论失败，状态码: {response.status_code}")
                return None
            
            data = response.json()
            
            if not data.get('success'):
                print(f"获取评论错误: {data.get('message', '未知错误')}")
                return None
            
            comments_data = data.get('comments', [])
            comments = []
            
            for comment in comments_data:
                try:
                    comment_info = {
                        'comment_id': comment.get('id', ''),
                        'user_nickname': comment.get('nickname', '匿名用户'),
                        'user_level': comment.get('userLevel', ''),
                        'user_client': comment.get('userClientShow', ''),  # 用户客户端
                        'score': comment.get('score', 5),  # 评分 1-5
                        'content': comment.get('content', ''),  # 评论内容
                        'creation_time': comment.get('creationTime', ''),  # 评论时间
                        'reply_count': comment.get('replyCount', 0),  # 回复数
                        'useful_vote_count': comment.get('usefulVoteCount', 0),  # 有用数
                        'useless_vote_count': comment.get('uselessVoteCount', 0),  # 无用数
                        'after_days': comment.get('afterDays', 0),  # 追评天数
                        'after_user_comment': comment.get('afterUserComment', {}).get('content', ''),  # 追评内容
                        'images': [img.get('imgUrl', '') for img in comment.get('images', [])],  # 晒图
                        'videos': [video.get('mainUrl', '') for video in comment.get('videos', [])],  # 视频
                        'product_color': comment.get('productColor', ''),
                        'product_size': comment.get('productSize', ''),
                        'reference_time': comment.get('referenceTime', ''),  # 参考时间
                        'reference_name': comment.get('referenceName', ''),  # 参考名称
                    }
                    comments.append(comment_info)
                    
                except Exception as e:
                    print(f"处理评论数据时出错: {str(e)}")
                    continue
            
            print(f"[{datetime.now()}] 成功获取 {len(comments)} 条评论")
            
            # 缓存数据
            self.comment_cache[cache_key] = comments
            
            return comments
            
        except Exception as e:
            print(f"获取商品评论时出错: {str(e)}")
            return None
    
    def analyze_comments(self, comments: List[Dict]) -> Dict:
        """
        分析评论数据
        
        Args:
            comments: 评论列表
            
        Returns:
            Dict: 分析结果
        """
        try:
            if not comments:
                return {
                    'total_comments': 0,
                    'avg_score': 0,
                    'score_distribution': {},
                    'image_rate': 0,
                    'video_rate': 0,
                    'word_frequency': {},
                }
            
            total_comments = len(comments)
            total_score = sum(c.get('score', 5) for c in comments)
            avg_score = total_score / total_comments
            
            # 评分分布
            score_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for comment in comments:
                score = comment.get('score', 5)
                if 1 <= score <= 5:
                    score_dist[int(score)] += 1
            
            # 图片/视频比例
            image_comments = sum(1 for c in comments if c.get('images'))
            video_comments = sum(1 for c in comments if c.get('videos'))
            
            image_rate = (image_comments / total_comments) * 100 if total_comments > 0 else 0
            video_rate = (video_comments / total_comments) * 100 if total_comments > 0 else 0
            
            # 关键词分析（简化版）
            word_freq = {}
            for comment in comments:
                content = comment.get('content', '')
                if content:
                    # 简单分词（实际应用中应该使用更复杂的分词）
                    words = re.findall(r'[\u4e00-\u9fa5]{2,}', content)
                    for word in words:
                        word_freq[word] = word_freq.get(word, 0) + 1
            
            # 取前10个高频词
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            
            analysis = {
                'total_comments': total_comments,
                'avg_score': round(avg_score, 2),
                'score_distribution': score_dist,
                'image_rate': round(image_rate, 2),
                'video_rate': round(video_rate, 2),
                'top_keywords': dict(top_words),
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            return analysis
            
        except Exception as e:
            print(f"分析评论时出错: {str(e)}")
            return {}
    
    def save_to_json(self, data: List[Dict], filename: Optional[str] = None):
        """
        保存数据到JSON文件
        
        Args:
            data: 要保存的数据列表
            filename: 文件名，默认为当前时间戳
        """
        if not data:
            print("没有数据可保存")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"jd_comments_{timestamp}.json"
        
        filepath = f"D:/openclaw/workspace/crawlers/data/{filename}"
        
        try:
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"数据已保存到JSON: {filepath}")
            
        except Exception as e:
            print(f"保存数据到JSON时出错: {str(e)}")
    
    def run(self, keywords: List[str] = None, save_to_file: bool = True) -> List[Dict]:
        """
        运行爬虫主程序
        
        Args:
            keywords: 搜索关键词列表
            save_to_file: 是否保存到文件
            
        Returns:
            List[Dict]: 爬取的数据列表
        """
        print("=" * 50)
        print("京东评论爬虫开始运行")
        print("=" * 50)
        
        if keywords is None:
            keywords = ['手机', '笔记本电脑', '耳机']
        
        all_products = []
        
        for keyword in keywords:
            print(f"\n搜索关键词: {keyword}")
            
            # 搜索商品
            products = self.search_products(keyword, page=1, page_size=10)
            
            if not products:
                print(f"未找到关键词 '{keyword}' 的商品")
                continue
            
            for product in products[:5]:  # 每个关键词只处理前5个
                try:
                    sku_id = product.get('sku_id')
                    if not sku_id:
                        continue
                    
                    # 获取商品详情
                    detail = self.get_product_detail(sku_id)
                    if not detail:
                        continue
                    
                    # 获取评论
                    comments = self.get_product_comments(sku_id, page=1, page_size=20)
                    
                    # 分析评论
                    analysis = self.analyze_comments(comments or [])
                    
                    # 合并数据
                    complete_data = {
                        **product,
                        **detail,
                        'comments_count': len(comments) if comments else 0,
                        'sample_comments': comments[:5] if comments else [],  # 保存5条样本评论
                        **analysis,
                        'keyword': keyword,
                    }
                    
                    all_products.append(complete_data)
                    
                    print(f"  已处理: {product.get('title')} (评价: {detail.get('comment_count', 0):,})")
                    
                    # 避免请求过快
                    time.sleep(random.uniform(2, 3))
                    
                except Exception as e:
                    print(f"处理商品 {product.get('title')} 时出错: {str(e)}")
                    continue
        
        # 保存到文件
        if save_to_file and all_products:
            self.save_to_json(all_products)
        
        print("=" * 50)
        print(f"爬虫运行完成，共收集 {len(all_products)} 个商品数据")
        print("=" * 50)
        
        return all_products


def main():
    """主函数"""
    try:
        # 创建爬虫实例
        crawler = JDCommentCrawler()
        
        # 运行爬虫
        products = crawler.run(
            keywords=['手机', '耳机'],  # 可以修改搜索关键词
            save_to_file=True
        )
        
        if products:
            print(f"\n数据统计:")
            print(f"总商品数: {len(products)}")
            
            # 按评价数排序
            sorted_products = sorted(products, key=lambda x: x.get('comment_count', 0), reverse=True)
            
            print(f"\n评价最多的前5个商品:")
            for idx, product in enumerate(sorted_products[:5], 1):
                title = product.get('title', '')[:40]
                if len(product.get('title', '')) > 40:
                    title += "..."
                
                print(f"  {idx}. {title}")
                print(f"     价格: ¥{product.get('price', 0):.2f} | "
                      f"评价数: {product.get('comment_count', 0):,}")
                print(f"     好评率: {product.get('good_rate', 0):.2f}% | "
                      f"平均分: {product.get('avg_score', 0):.2f}")
                
                if product.get('top_keywords'):
                    keywords = list(product['top_keywords'].keys())[:3]
                    print(f"     高频词: {', '.join(keywords)}")
        else:
            print("未能获取商品数据")
            
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行出错: {str(e)}")


if __name__ == "__main__":
    main()