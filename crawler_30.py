#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电子产品价格爬虫 - 京东商品数据
爬取京东商城的电子产品价格：手机、电脑、家电、数码产品等
"""

import requests
import json
import time
import re
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime
import csv
import os
from bs4 import BeautifulSoup
import html

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ElectronicProduct:
    """电子产品数据结构"""
    name: str
    url: str
    sku_id: str  # 商品SKU
    price: float  # 当前价格
    original_price: float  # 原价
    discount: float  # 折扣（百分比）
    brand: str  # 品牌
    category: str  # 分类（手机、电脑等）
    subcategory: str  # 子分类
    rating: float  # 评分（0-5）
    rating_count: int  # 评价数量
    review_count: int  # 评论数量
    sales: int  # 销量（月/累计）
    store: str  # 店铺名称
    store_rating: float  # 店铺评分
    delivery: str  # 配送方式
    warranty: str  # 保修信息
    specs: Dict[str, str]  # 规格参数
    image_url: str  # 商品图片
    promotion: str  # 促销信息


class JDcrawler:
    """京东商城爬虫类"""
    
    def __init__(self):
        self.base_url = "https://www.jd.com"
        self.api_url = "https://api.jd.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.jd.com/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 电子产品分类
        self.categories = {
            'mobile': '手机',
            'computer': '电脑',
            'home_appliance': '家电',
            'digital': '数码',
            'audio': '影音娱乐',
            'camera': '摄影摄像',
            'smart_home': '智能家居',
            'office': '办公设备',
            'gaming': '游戏设备',
            'wearable': '智能穿戴'
        }
        
        # 知名品牌映射
        self.brands = {
            'apple': '苹果',
            'huawei': '华为',
            'xiaomi': '小米',
            'samsung': '三星',
            'oppo': 'OPPO',
            'vivo': 'VIVO',
            'lenovo': '联想',
            'dell': '戴尔',
            'hp': '惠普',
            'asus': '华硕',
            'msi': '微星',
            'sony': '索尼',
            'canon': '佳能',
            'nikon': '尼康',
            'logitech': '罗技',
            'anker': '安克'
        }
    
    def get_products_by_category(self, category: str = None, limit: int = 30) -> List[ElectronicProduct]:
        """
        获取分类商品列表
        
        Args:
            category: 商品分类（可选）
            limit: 获取数量
            
        Returns:
            商品对象列表
        """
        products = []
        page = 1
        
        try:
            category_name = self.categories.get(category, '全部') if category else '全部'
            logger.info(f"正在获取 {category_name} 商品，数量: {limit}")
            
            while len(products) < limit:
                # 构建搜索URL（使用搜索页面模拟分类）
                if category and category in self.categories:
                    search_keyword = self.categories[category]
                    url = f"{self.base_url}/search"
                    params = {
                        'keyword': search_keyword,
                        'page': page
                    }
                else:
                    # 获取热门商品
                    url = f"{self.base_url}/allSort.aspx"
                    params = {'page': page} if page > 1 else {}
                
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找商品列表
                product_elements = soup.select('.gl-item, .goods-item, .product-item')
                
                if not product_elements:
                    # 尝试其他选择器
                    product_elements = soup.select('.item, .p-img, .j-sku-item')
                
                if not product_elements:
                    logger.warning("未找到商品元素，可能页面结构已变化")
                    break
                
                # 解析每个商品
                new_products = 0
                for element in product_elements:
                    if len(products) >= limit:
                        break
                    
                    product = self._parse_product_element(element, category)
                    if product:
                        products.append(product)
                        new_products += 1
                
                if new_products == 0:
                    logger.info(f"第 {page} 页没有新商品，停止翻页")
                    break
                
                logger.info(f"第 {page} 页获取了 {new_products} 个商品，总计 {len(products)} 个")
                page += 1
                
                # 避免请求过快
                time.sleep(2)
            
            logger.info(f"成功获取 {len(products)} 个商品信息")
            return products
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析商品失败: {e}")
            return []
    
    def _parse_product_element(self, element, category: str) -> Optional[ElectronicProduct]:
        """解析商品HTML元素"""
        try:
            # 提取商品名称
            name_element = element.select_one('.p-name, .sku-name, .name')
            name = name_element.get_text(strip=True) if name_element else ''
            
            if not name:
                return None
            
            # 提取链接
            link_element = element.select_one('.p-img a, .pic a')
            if not link_element or not link_element.get('href'):
                return None
            
            product_url = link_element['href']
            if not product_url.startswith('http'):
                product_url = 'https:' + product_url if product_url.startswith('//') else self.base_url + product_url
            
            # 提取SKU ID
            sku_id = self._extract_sku_id(product_url)
            
            # 提取价格
            price_element = element.select_one('.p-price, .price, .J_price')
            price = 0.0
            original_price = 0.0
            discount = 0.0
            
            if price_element:
                price_text = price_element.get_text(strip=True)
                # 提取价格数字
                numbers = re.findall(r'[\d.,]+', price_text)
                if numbers:
                    price = float(numbers[0].replace(',', ''))
                    
                    # 如果有多个价格，第二个可能是原价
                    if len(numbers) > 1:
                        original_price = float(numbers[1].replace(',', ''))
                        if original_price > price:
                            discount = (1 - price / original_price) * 100
            
            # 提取品牌
            brand = self._extract_brand(name)
            
            # 提取类别
            category_name = self.categories.get(category, '未知')
            
            # 提取评分
            rating_element = element.select_one('.star, .rating, .score')
            rating = 0.0
            rating_count = 0
            
            if rating_element:
                rating_text = rating_element.get_text(strip=True)
                match = re.search(r'[\d.]+', rating_text)
                if match:
                    rating = float(match.group())
            
            # 提取评价数量
            review_element = element.select_one('.comment, .evaluate, .review')
            review_count = 0
            if review_element:
                review_text = review_element.get_text(strip=True)
                match = re.search(r'(\d+)', review_text)
                if match:
                    review_count = int(match.group(1))
            
            # 提取销量
            sales_element = element.select_one('.sale, .sales, .volume')
            sales = 0
            if sales_element:
                sales_text = sales_element.get_text(strip=True)
                # 处理"月销1000+"格式
                match = re.search(r'(\d+)[\+\万]?', sales_text)
                if match:
                    sales = int(match.group(1))
                    if '万' in sales_text:
                        sales *= 10000
            
            # 提取店铺信息
            store_element = element.select_one('.shop, .store, .merchant')
            store = store_element.get_text(strip=True) if store_element else '京东自营'
            
            # 提取图片
            image_element = element.select_one('img')
            image_url = image_element['data-lazy-img'] if image_element and image_element.get('data-lazy-img') else ''
            if not image_url and image_element and image_element.get('src'):
                image_url = image_element['src']
            
            # 提取促销信息
            promo_element = element.select_one('.promo, .tag, .label')
            promotion = promo_element.get_text(strip=True) if promo_element else ''
            
            # 获取商品详细信息
            specs, delivery, warranty, store_rating = self._get_product_details(product_url)
            
            # 确定子分类
            subcategory = self._determine_subcategory(name, specs)
            
            product = ElectronicProduct(
                name=html.unescape(name),
                url=product_url,
                sku_id=sku_id,
                price=price,
                original_price=original_price,
                discount=discount,
                brand=brand,
                category=category_name,
                subcategory=subcategory,
                rating=rating,
                rating_count=rating_count,
                review_count=review_count,
                sales=sales,
                store=html.unescape(store),
                store_rating=store_rating,
                delivery=delivery,
                warranty=warranty,
                specs=specs,
                image_url=image_url,
                promotion=promotion
            )
            
            return product
            
        except Exception as e:
            logger.warning(f"解析商品元素失败: {e}")
            return None
    
    def _extract_sku_id(self, url: str) -> str:
        """从URL中提取SKU ID"""
        try:
            # 京东URL格式通常包含数字SKU
            match = re.search(r'/(\d+)\.html', url)
            if match:
                return match.group(1)
            
            # 另一种格式
            match = re.search(r'item\.jd\.com/(\d+)', url)
            if match:
                return match.group(1)
            
            return ''
        except:
            return ''
    
    def _extract_brand(self, name: str) -> str:
        """从商品名称中提取品牌"""
        brand = '未知'
        
        # 检查常见品牌
        for brand_en, brand_cn in self.brands.items():
            if brand_cn in name:
                brand = brand_cn
                break
        
        # 如果没有匹配，尝试从名称开头提取
        if brand == '未知':
            # 常见品牌模式
            brand_patterns = [
                r'^([A-Za-z]+)\s+',  # 英文品牌开头
                r'^(\w+)\s*[-·]',  # 品牌后跟分隔符
                r'【(\w+)】',  # 品牌在括号中
            ]
            
            for pattern in brand_patterns:
                match = re.search(pattern, name)
                if match:
                    potential_brand = match.group(1)
                    # 检查是否在品牌列表中
                    for brand_cn in self.brands.values():
                        if brand_cn in potential_brand or potential_brand in brand_cn:
                            brand = brand_cn
                            break
                    
                    if brand != '未知':
                        break
        
        return brand
    
    def _determine_subcategory(self, name: str, specs: Dict) -> str:
        """确定商品子分类"""
        subcategory = '其他'
        
        # 根据名称关键词判断
        keywords = {
            '手机': ['手机', 'Phone', '智能手机', '移动电话'],
            '笔记本电脑': ['笔记本', '笔记本电脑', 'Laptop', 'Notebook'],
            '台式机': ['台式机', '台式电脑', 'Desktop'],
            '平板电脑': ['平板', '平板电脑', 'Tablet', 'iPad'],
            '显示器': ['显示器', '显示屏', 'Monitor'],
            '电视': ['电视', '电视机', 'TV', '液晶电视'],
            '冰箱': ['冰箱', '电冰箱'],
            '洗衣机': ['洗衣机'],
            '空调': ['空调'],
            '相机': ['相机', '摄像机', 'Camera'],
            '耳机': ['耳机', '耳麦', 'Headphone'],
            '音响': ['音箱', '音响', 'Speaker'],
            '路由器': ['路由器', 'Router'],
            '智能手表': ['智能手表', '手表', 'Watch'],
            '游戏机': ['游戏机', 'PlayStation', 'Xbox', 'Switch']
        }
        
        name_lower = name.lower()
        for cat, keys in keywords.items():
            for key in keys:
                if key.lower() in name_lower:
                    subcategory = cat
                    return subcategory
        
        # 如果名称中没有，检查规格参数
        for spec_key, spec_value in specs.items():
            spec_lower = spec_value.lower()
            for cat, keys in keywords.items():
                for key in keys:
                    if key.lower() in spec_lower:
                        subcategory = cat
                        return subcategory
        
        return subcategory
    
    def _get_product_details(self, url: str) -> Tuple[Dict[str, str], str, str, float]:
        """获取商品详细信息"""
        specs = {}
        delivery = '普通配送'
        warranty = '官方保修'
        store_rating = 0.0
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取规格参数
            spec_section = soup.select_one('.Ptable, .parameter, .spec-list')
            if spec_section:
                rows = spec_section.select('tr, li')
                for row in rows:
                    label = row.select_one('th, .label, dt')
                    value = row.select_one('td, .value, dd')
                    
                    if label and value:
                        label_text = label.get_text(strip=True)
                        value_text = value.get_text(strip=True)
                        if label_text and value_text:
                            specs[label_text] = value_text
            
            # 提取配送信息
            delivery_section = soup.select_one('.delivery, .logistics')
            if delivery_section:
                delivery_text = delivery_section.get_text(strip=True)
                if '次日达' in delivery_text or '当日达' in delivery_text:
                    delivery = '快速配送'
                elif '自提' in delivery_text:
                    delivery = '门店自提'
            
            # 提取保修信息
            warranty_section = soup.select_one('.warranty, .service')
            if warranty_section:
                warranty_text = warranty_section.get_text(strip=True)
                warranty = warranty_text[:50]  # 截取前50字符
            
            # 提取店铺评分
            store_section = soup.select_one('.store-score, .shop-rating')
            if store_section:
                rating_text = store_section.get_text(strip=True)
                match = re.search(r'[\d.]+', rating_text)
                if match:
                    store_rating = float(match.group())
        
        except Exception as e:
            logger.warning(f"获取商品详情失败 {url}: {e}")
        
        return specs, delivery, warranty, store_rating
    
    def search_products(self, **filters) -> List[ElectronicProduct]:
        """
        搜索商品
        
        Args:
            filters: 筛选条件（关键词、价格、品牌等）
            
        Returns:
            商品对象列表
        """
        search_url = f"{self.base_url}/search"
        
        # 构建查询参数
        params = {}
        
        # 关键词搜索
        if 'keyword' in filters:
            params['keyword'] = filters['keyword']
        
        # 价格筛选
        if 'price_min' in filters and 'price_max' in filters:
            price_min = filters['price_min']
            price_max = filters['price_max']
            params['psort'] = 3  # 价格排序
            # 京东价格区间参数（简化处理）
            params['ev'] = f'price_{price_min}_{price_max}'
        
        # 品牌筛选
        if 'brand' in filters:
            brand = filters['brand']
            # 在关键词中添加品牌
            if 'keyword' in params:
                params['keyword'] = f'{brand} {params["keyword"]}'
            else:
                params['keyword'] = brand
        
        try:
            logger.info(f"正在搜索商品，条件: {filters}")
            
            response = self.session.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            products = []
            product_elements = soup.select('.gl-item, .goods-item')
            
            for element in product_elements[:30]:  # 最多30个结果
                # 使用默认分类
                product = self._parse_product_element(element, None)
                if product:
                    # 进一步筛选
                    if self._match_filters(product, filters):
                        products.append(product)
            
            logger.info(f"搜索到 {len(products)} 个符合条件的商品")
            return products
            
        except Exception as e:
            logger.error(f"搜索商品失败: {e}")
            return []
    
    def _match_filters(self, product: ElectronicProduct, filters: Dict) -> bool:
        """检查商品是否匹配筛选条件"""
        # 品牌筛选
        if 'brand' in filters and filters['brand'] != product.brand:
            return False
        
        # 价格筛选
        if 'price_min' in filters and 'price_max' in filters:
            price_min = filters['price_min']
            price_max = filters['price_max']
            
            if product.price < price_min or product.price > price_max:
                return False
        
        # 评分筛选
        if 'min_rating' in filters and product.rating < filters['min_rating']:
            return False
        
        # 类别筛选
        if 'category' in filters and filters['category'] != product.category:
            return False
        
        return True
    
    def get_price_history(self, sku_id: str, days: int = 30) -> List[Dict]:
        """
        获取商品价格历史（模拟）
        
        Args:
            sku_id: 商品SKU
            days: 历史天数
            
        Returns:
            价格历史列表
        """
        # 注意：京东官方API需要权限，这里使用模拟数据
        logger.info(f"获取商品 {sku_id} 的价格历史（模拟数据）")
        
        price_history = []
        current_date = datetime.now()
        
        # 生成模拟价格数据
        base_price = 1000 + (hash(sku_id) % 1000)  # 基于SKU生成基础价格
        price_trend = 0.95 + (hash(sku_id) % 20) / 100  # 价格趋势
        
        for i in range(days, -1, -1):
            date = current_date - timedelta(days=i)
            
            # 模拟价格波动
            day_factor = 1.0 + (hash(f"{sku_id}{i}") % 10 - 5) / 100  # ±5%
            trend_factor = price_trend ** (i / 10)  # 长期趋势
            
            price = base_price * day_factor * trend_factor
            
            # 模拟促销活动
            if i % 7 == 0:  # 每周有促销
                price *= 0.9  # 9折
            
            if i == 0:  # 今天可能有特别促销
                price *= 0.95
            
            price_history.append({
                'date': date.strftime('%Y-%m-%d'),
                'price': round(price, 2),
                'is_promotion': i % 7 == 0 or i == 0
            })
        
        return price_history
    
    def analyze_products(self, products: List[ElectronicProduct]) -> Dict:
        """
        分析商品数据
        
        Args:
            products: 商品对象列表
            
        Returns:
            分析结果字典
        """
        if not products:
            return {}
        
        try:
            # 统计信息
            total_products = len(products)
            
            # 品牌统计
            brand_counts = {}
            for product in products:
                brand_counts[product.brand] = brand_counts.get(product.brand, 0) + 1
            
            top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 类别统计
            category_counts = {}
            for product in products:
                category_counts[product.category] = category_counts.get(product.category, 0) + 1
            
            top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 价格统计
            prices = [product.price for product in products if product.price > 0]
            avg_price = sum(prices) / len(prices) if prices else 0
            
            # 评分统计
            ratings = [product.rating for product in products if product.rating > 0]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            
            # 销量统计
            sales = [product.sales for product in products if product.sales > 0]
            total_sales = sum(sales) if sales else 0
            avg_sales = total_sales / len(sales) if sales else 0
            
            # 折扣统计
            discounts = [product.discount for product in products if product.discount > 0]
            avg_discount = sum(discounts) / len(discounts) if discounts else 0
            
            # 价格区间统计
            price_ranges = {
                '100元以下': 0,
                '100-500元': 0,
                '500-1000元': 0,
                '1000-3000元': 0,
                '3000-5000元': 0,
                '5000-10000元': 0,
                '10000元以上': 0
            }
            
            for product in products:
                price = product.price
                if price < 100:
                    price_ranges['100元以下'] += 1
                elif price < 500:
                    price_ranges['100-500元'] += 1
                elif price < 1000:
                    price_ranges['500-1000元'] += 1
                elif price < 3000:
                    price_ranges['1000-3000元'] += 1
                elif price < 5000:
                    price_ranges['3000-5000元'] += 1
                elif price < 10000:
                    price_ranges['5000-10000元'] += 1
                else:
                    price_ranges['10000元以上'] += 1
            
            # 最贵和最便宜的商品
            if products:
                sorted_by_price = sorted(products, key=lambda x: x.price, reverse=True)
                most_expensive = sorted_by_price[0] if sorted_by_price else None
                cheapest = sorted_by_price[-1] if sorted_by_price else None
                
                sorted_by_sales = sorted(products, key=lambda x: x.sales, reverse=True)
                best_selling = sorted_by_sales[0] if sorted_by_sales else None
                
                sorted_by_rating = sorted(products, key=lambda x: x.rating, reverse=True)
                highest_rated = sorted_by_rating[0] if sorted_by_rating else None
            else:
                most_expensive = cheapest = best_selling = highest_rated = None
            
            # 店铺类型统计
            store_counts = {}
            for product in products:
                store = product.store
                if '自营' in store:
                    store_type = '京东自营'
                elif '旗舰店' in store:
                    store_type = '品牌旗舰店'
                elif '专卖店' in store:
                    store_type = '专卖店'
                else:
                    store_type = '其他店铺'
                
                store_counts[store_type] = store_counts.get(store_type, 0) + 1
            
            return {
                'total_products': total_products,
                'total_sales': total_sales,
                'avg_price': avg_price,
                'avg_rating': avg_rating,
                'avg_sales': avg_sales,
                'avg_discount': avg_discount,
                'top_brands': top_brands,
                'top_categories': top_categories,
                'price_distribution': price_ranges,
                'store_distribution': store_counts,
                'most_expensive': (most_expensive.name[:30], most_expensive.price) if most_expensive else None,
                'cheapest': (cheapest.name[:30], cheapest.price) if cheapest else None,
                'best_selling': (best_selling.name[:30], best_selling.sales) if best_selling else None,
                'highest_rated': (highest_rated.name[:30], highest_rated.rating) if highest_rated else None
            }
            
        except Exception as e:
            logger.error(f"分析商品数据失败: {e}")
            return {}
    
    def save_to_csv(self, products: List[ElectronicProduct], filename: str = "electronic_products.csv"):
        """
        保存商品数据到CSV文件
        
        Args:
            products: 商品对象列表
            filename: 输出文件名
        """
        if not products:
            logger.warning("没有商品数据可保存")
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = [
                    'name', 'url', 'sku_id', 'price', 'original_price', 'discount',
                    'brand', 'category', 'subcategory', 'rating', 'rating_count',
                    'review_count', 'sales', 'store', 'store_rating', 'delivery',
                    'warranty', 'specs', 'image_url', 'promotion'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for product in products:
                    row = product.__dict__.copy()
                    # 转换规格字典为字符串
                    specs_str = '; '.join([f'{k}: {v}' for k, v in row['specs'].items()][:5])  # 最多5个规格
                    row['specs'] = specs_str
                    writer.writerow(row)
            
            logger.info(f"已保存 {len(products)} 个商品数据到 {filename}")
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")


def main():
    """主函数"""
    print("=" * 50)
    print("京东电子产品价格爬虫 v1.0")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = JDcrawler()
    
    try:
        # 1. 显示商品分类
        print("电子产品分类:")
        print("-" * 30)
        for i, (code, name) in enumerate(crawler.categories.items(), 1):
            print(f"  {code}: {name}", end='  ')
            if i % 3 == 0:
                print()
        print()
        
        # 2. 显示常见品牌
        print("常见品牌:")
        print("-" * 30)
        brands_list = list(crawler.brands.values())
        for i in range(0, len(brands_list), 5):
            print('  ' + ', '.join(brands_list[i:i+5]))
        print()
        
        # 3. 获取商品数据（可选择分类）
        category_choice = input("请输入分类代码（直接回车获取全部）: ").strip().lower()
        
        if category_choice and category_choice not in crawler.categories:
            print(f"无效分类代码，将获取全部商品")
            category_choice = None
        
        print(f"\n正在爬取商品数据...")
        products = crawler.get_products_by_category(category_choice, limit=25)
        
        if not products:
            print("未获取到商品数据，程序退出")
            return
        
        # 4. 显示统计信息
        print(f"\n成功获取 {len(products)} 个商品:")
        print("-" * 50)
        
        # 分析数据
        analysis = crawler.analyze_products(products)
        
        if analysis:
            print(f"总计商品: {analysis['total_products']}")
            print(f"总销量: {analysis['total_sales']:,}")
            print(f"平均价格: ¥{analysis['avg_price']:.2f}")
            print(f"平均评分: {analysis['avg_rating']:.1f}")
            print(f"平均折扣: {analysis['avg_discount']:.1f}%")
            
            if analysis['top_brands']:
                print("\n热门品牌:")
                for brand, count in analysis['top_brands']:
                    print(f"  {brand}: {count} 款")
            
            if analysis['top_categories']:
                print("\n商品分类:")
                for category, count in analysis['top_categories']:
                    print(f"  {category}: {count} 款")
            
            if analysis['price_distribution']:
                print("\n价格分布:")
                for price_range, count in analysis['price_distribution'].items():
                    if count > 0:
                        print(f"  {price_range}: {count} 款")
        
        # 5. 显示前5个商品详情
        print("\n热门商品 TOP 5:")
        print("-" * 30)
        for i, product in enumerate(products[:5], 1):
            print(f"{i}. {product.name}")
            print(f"   品牌: {product.brand}, 价格: ¥{product.price:.2f}")
            if product.original_price > product.price:
                print(f"   原价: ¥{product.original_price:.2f} (-{product.discount:.1f}%)")
            print(f"   评分: {product.rating:.1f}, 评价: {product.review_count:,}")
            print(f"   销量: {product.sales:,}, 店铺: {product.store}")
            print(f"   分类: {product.category} > {product.subcategory}")
            if product.promotion:
                print(f"   促销: {product.promotion}")
            print()
        
        # 6. 保存数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        category_name = crawler.categories.get(category_choice, 'all') if category_choice else 'all'
        csv_file = f"electronic_products_{category_name}_{timestamp}.csv"
        
        crawler.save_to_csv(products, csv_file)
        
        print(f"\n数据已保存到: {csv_file}")
        
        # 7. 展示一个商品的详细内容
        if products:
            sample_product = products[0]
            print(f"\n商品 '{sample_product.name[:20]}...' 的详细参数:")
            print("-" * 30)
            
            print(f"基本信息:")
            print(f"  品牌: {sample_product.brand}")
            print(f"  分类: {sample_product.category}")
            print(f"  子分类: {sample_product.subcategory}")
            print(f"  SKU: {sample_product.sku_id}")
            
            print(f"\n价格信息:")
            print(f"  当前价格: ¥{sample_product.price:.2f}")
            if sample_product.original_price > sample_product.price:
                print(f"  原价: ¥{sample_product.original_price:.2f}")
                print(f"  折扣: {sample_product.discount:.1f}%")
            
            print(f"\n销售信息:")
            print(f"  评分: {sample_product.rating:.1f}")
            print(f"  评价数量: {sample_product.review_count:,}")
            print(f"  销量: {sample_product.sales:,}")
            print(f"  店铺: {sample_product.store}")
            print(f"  店铺评分: {sample_product.store_rating:.1f}")
            
            print(f"\n服务信息:")
            print(f"  配送: {sample_product.delivery}")
            print(f"  保修: {sample_product.warranty[:50]}...")
            
            if sample_product.promotion:
                print(f"  促销: {sample_product.promotion}")
            
            if sample_product.specs:
                print(f"\n主要规格:")
                for i, (key, value) in enumerate(list(sample_product.specs.items())[:5], 1):
                    print(f"  {key}: {value}")
                if len(sample_product.specs) > 5:
                    print(f"  等{len(sample_product.specs)}项规格")
        
        # 8. 演示搜索功能
        print("\n" + "=" * 50)
        print("演示筛选搜索功能:")
        
        print("可选筛选条件:")
        print("  1. 关键词 (例如: 手机)")
        print("  2. 品牌 (例如: 华为)")
        print("  3. 价格范围 (例如: 1000-3000)")
        print("  4. 最低评分 (例如: 4.0)")
        
        filters = {}
        
        # 关键词搜索
        keyword_input = input("请输入关键词（直接回车跳过）: ").strip()
        if keyword_input:
            filters['keyword'] = keyword_input
        
        # 品牌筛选
        brand_input = input("请输入品牌（直接回车跳过）: ").strip()
        if brand_input and brand_input in crawler.brands.values():
            filters['brand'] = brand_input
        
        # 价格筛选
        price_input = input("请输入价格范围 (如: 1000-3000，直接回车跳过): ").strip()
        if price_input and '-' in price_input:
            try:
                price_min, price_max = price_input.split('-')
                filters['price_min'] = float(price_min)
                filters['price_max'] = float(price_max)
            except:
                print("价格格式错误，跳过价格筛选")
        
        # 评分筛选
        rating_input = input("请输入最低评分 (如: 4.0，直接回车跳过): ").strip()
        if rating_input:
            try:
                filters['min_rating'] = float(rating_input)
            except:
                print("评分格式错误，跳过评分筛选")
        
        if filters:
            print(f"\n正在根据条件搜索: {filters}")
            search_results = crawler.search_products(**filters)
            
            if search_results:
                print(f"找到 {len(search_results)} 个符合条件的商品:")
                for i, product in enumerate(search_results[:5], 1):
                    print(f"{i}. {product.name}")
                    print(f"   品牌: {product.brand}, 价格: ¥{product.price:.2f}")
                    print(f"   评分: {product.rating:.1f}, 销量: {product.sales:,}")
            else:
                print("未找到符合条件的商品")
        
        # 9. 演示价格历史功能
        print("\n" + "=" * 50)
        print("演示价格历史功能:")
        
        if products:
            sample_sku = products[0].sku_id
            if sample_sku:
                print(f"\n获取商品 '{products[0].name[:20]}...' 的价格历史:")
                price_history = crawler.get_price_history(sample_sku, days=7)
                
                if price_history:
                    print("\n最近7天价格历史:")
                    print("-" * 40)
                    print("日期       | 价格      | 是否促销")
                    print("-" * 40)
                    for record in price_history:
                        date = record['date']
                        price = f"¥{record['price']:.2f}"
                        promotion = "是" if record['is_promotion'] else "否"
                        print(f"{date} | {price:10s} | {promotion}")
        
        print("\n爬取完成！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()