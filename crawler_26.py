#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美食菜谱爬虫 - 下厨房菜谱数据
爬取下厨房网站的菜谱信息：菜名、食材、做法、评分、收藏数等
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
class Recipe:
    """菜谱数据结构"""
    title: str
    url: str
    author: str
    difficulty: str  # 难度
    time: str  # 烹饪时间
    servings: str  # 分量（几人份）
    rating: float  # 评分（0-5）
    rating_count: int  # 评分人数
    made_count: int  # 做过人数
    collect_count: int  # 收藏人数
    ingredients: List[str]  # 食材列表
    steps: List[str]  # 步骤列表
    tips: str  # 小贴士
    category: str  # 分类
    tags: List[str]  # 标签
    image_url: str  # 菜谱图片
    calories: str  # 热量（如果可用）


class XiachufangCrawler:
    """下厨房爬虫类"""
    
    def __init__(self):
        self.base_url = "https://www.xiachufang.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 菜谱分类映射
        self.categories = {
            'hot': '热门',
            'new': '最新',
            'breakfast': '早餐',
            'lunch': '午餐', 
            'dinner': '晚餐',
            'dessert': '甜品',
            'snack': '小吃',
            'soup': '汤羹',
            'vegetarian': '素食',
            'quick': '快手菜'
        }
    
    def get_popular_recipes(self, category: str = None, limit: int = 30) -> List[Recipe]:
        """
        获取热门菜谱
        
        Args:
            category: 菜谱分类（可选）
            limit: 获取数量
            
        Returns:
            菜谱对象列表
        """
        recipes = []
        page = 1
        
        try:
            logger.info(f"正在获取菜谱，分类: {category or '热门'}, 数量: {limit}")
            
            while len(recipes) < limit:
                # 构建URL
                if category and category in self.categories:
                    url = f"{self.base_url}/category/{category}"
                else:
                    url = f"{self.base_url}/explore"
                
                params = {'page': page} if page > 1 else {}
                
                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                
                # 解析HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找菜谱列表
                recipe_elements = soup.select('.recipe, .recipe-panel, .normal-recipe-list .recipe')
                
                if not recipe_elements:
                    # 尝试其他选择器
                    recipe_elements = soup.select('.recipe-item, .recipe-card, .list .item')
                
                if not recipe_elements:
                    logger.warning("未找到菜谱元素，可能页面结构已变化")
                    break
                
                # 解析每个菜谱
                new_recipes = 0
                for element in recipe_elements:
                    if len(recipes) >= limit:
                        break
                    
                    recipe = self._parse_recipe_element(element)
                    if recipe:
                        recipes.append(recipe)
                        new_recipes += 1
                
                if new_recipes == 0:
                    logger.info(f"第 {page} 页没有新菜谱，停止翻页")
                    break
                
                logger.info(f"第 {page} 页获取了 {new_recipes} 个菜谱，总计 {len(recipes)} 个")
                page += 1
                
                # 避免请求过快
                time.sleep(1.5)
            
            logger.info(f"成功获取 {len(recipes)} 个菜谱")
            return recipes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析菜谱失败: {e}")
            return []
    
    def _parse_recipe_element(self, element) -> Optional[Recipe]:
        """解析菜谱HTML元素"""
        try:
            # 提取标题
            title_element = element.select_one('.name, .title, .recipe-name')
            title = title_element.get_text(strip=True) if title_element else ''
            
            if not title:
                return None
            
            # 提取链接
            link_element = element.select_one('a')
            if not link_element or not link_element.get('href'):
                return None
            
            recipe_url = link_element['href']
            if not recipe_url.startswith('http'):
                recipe_url = self.base_url + recipe_url
            
            # 提取作者
            author_element = element.select_one('.author, .author-name, .cook')
            author = author_element.get_text(strip=True) if author_element else '未知作者'
            
            # 提取难度、时间、分量
            meta_elements = element.select('.info, .meta, .recipe-info span')
            difficulty = '普通'
            cook_time = '未知'
            servings = '未知'
            
            for meta in meta_elements:
                meta_text = meta.get_text(strip=True)
                if '难度' in meta_text:
                    difficulty = meta_text.replace('难度', '').strip()
                elif '时间' in meta_text:
                    cook_time = meta_text.replace('时间', '').strip()
                elif '人份' in meta_text:
                    servings = meta_text
            
            # 提取评分
            rating_element = element.select_one('.rating, .score, .star-rating')
            rating = 0.0
            rating_count = 0
            
            if rating_element:
                rating_text = rating_element.get_text(strip=True)
                match = re.search(r'[\d.]+', rating_text)
                if match:
                    rating = float(match.group())
            
            # 提取统计数据（做过、收藏）
            stats_elements = element.select('.stats, .numbers, .count')
            made_count = 0
            collect_count = 0
            
            for stats in stats_elements:
                stats_text = stats.get_text()
                if '做过' in stats_text:
                    match = re.search(r'(\d+)', stats_text)
                    if match:
                        made_count = int(match.group(1))
                elif '收藏' in stats_text:
                    match = re.search(r'(\d+)', stats_text)
                    if match:
                        collect_count = int(match.group(1))
            
            # 提取图片
            image_element = element.select_one('img')
            image_url = image_element['src'] if image_element and image_element.get('src') else ''
            
            # 提取分类和标签
            category = ''
            tags = []
            
            category_element = element.select_one('.category, .tag-category')
            if category_element:
                category = category_element.get_text(strip=True)
            
            tag_elements = element.select('.tag, .label, .keyword')
            for tag_element in tag_elements:
                tag_text = tag_element.get_text(strip=True)
                if tag_text and tag_text not in tags:
                    tags.append(tag_text)
            
            # 获取菜谱详情（食材和步骤）
            ingredients, steps, tips = self._get_recipe_details(recipe_url)
            
            recipe = Recipe(
                title=html.unescape(title),
                url=recipe_url,
                author=html.unescape(author),
                difficulty=html.unescape(difficulty),
                time=html.unescape(cook_time),
                servings=html.unescape(servings),
                rating=rating,
                rating_count=rating_count,
                made_count=made_count,
                collect_count=collect_count,
                ingredients=ingredients,
                steps=steps,
                tips=tips,
                category=html.unescape(category),
                tags=[html.unescape(tag) for tag in tags],
                image_url=image_url,
                calories=''  # 需要从详情页获取
            )
            
            return recipe
            
        except Exception as e:
            logger.warning(f"解析菜谱元素失败: {e}")
            return None
    
    def _get_recipe_details(self, url: str) -> Tuple[List[str], List[str], str]:
        """获取菜谱详细内容（食材和步骤）"""
        ingredients = []
        steps = []
        tips = ''
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取食材
            ingredients_section = soup.select_one('.ings, .ingredients, .material')
            if ingredients_section:
                ingredient_items = ingredients_section.select('li, .item, tr')
                for item in ingredient_items:
                    ingredient_text = item.get_text(strip=True)
                    if ingredient_text and '用料' not in ingredient_text:
                        # 清理多余空格和换行
                        ingredient_text = re.sub(r'\s+', ' ', ingredient_text)
                        ingredients.append(ingredient_text)
            
            # 提取步骤
            steps_section = soup.select_one('.steps, .method, .procedure')
            if steps_section:
                step_items = steps_section.select('li, .step, .item')
                for i, item in enumerate(step_items, 1):
                    step_text = item.get_text(strip=True)
                    if step_text and '步骤' not in step_text:
                        # 清理步骤编号
                        step_text = re.sub(r'^步骤?\d*[\.、]?\s*', '', step_text)
                        steps.append(f"{i}. {step_text}")
            
            # 提取小贴士
            tips_section = soup.select_one('.tips, .note, .tips-section')
            if tips_section:
                tips = tips_section.get_text(strip=True)
                # 清理标签
                tips = re.sub(r'小贴士[:：]?\s*', '', tips)
            
            # 如果没找到步骤，尝试其他选择器
            if not steps:
                # 尝试从主要内容中提取步骤
                main_content = soup.select_one('.recipe-instructions, .instructions')
                if main_content:
                    # 按段落分割
                    paragraphs = main_content.select('p')
                    for i, p in enumerate(paragraphs, 1):
                        p_text = p.get_text(strip=True)
                        if p_text and len(p_text) > 10:  # 过滤太短的内容
                            steps.append(f"{i}. {p_text}")
            
            # 限制步骤数量
            steps = steps[:20]
            
        except Exception as e:
            logger.warning(f"获取菜谱详情失败 {url}: {e}")
        
        return ingredients[:20], steps, tips[:500]
    
    def search_recipes(self, query: str, limit: int = 20) -> List[Recipe]:
        """
        搜索菜谱
        
        Args:
            query: 搜索关键词
            limit: 返回数量
            
        Returns:
            菜谱对象列表
        """
        search_url = f"{self.base_url}/search"
        params = {
            'keyword': query,
            'cat': 1001  # 菜谱分类
        }
        
        try:
            logger.info(f"正在搜索菜谱: {query}")
            
            response = self.session.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            recipes = []
            search_results = soup.select('.recipe, .search-result, .result-item')
            
            for result in search_results[:limit]:
                recipe = self._parse_search_result(result)
                if recipe:
                    recipes.append(recipe)
            
            logger.info(f"搜索到 {len(recipes)} 个相关菜谱")
            return recipes
            
        except Exception as e:
            logger.error(f"搜索菜谱失败: {e}")
            return []
    
    def _parse_search_result(self, element) -> Optional[Recipe]:
        """解析搜索结果元素"""
        try:
            # 搜索结果的解析逻辑与普通列表类似
            return self._parse_recipe_element(element)
            
        except Exception as e:
            logger.warning(f"解析搜索结果失败: {e}")
            return None
    
    def get_recipe_by_ingredients(self, ingredients: List[str], limit: int = 15) -> List[Recipe]:
        """
        根据食材搜索菜谱
        
        Args:
            ingredients: 食材列表
            limit: 返回数量
            
        Returns:
            菜谱对象列表
        """
        # 下厨房支持根据食材搜索
        ingredient_query = ' '.join(ingredients[:3])  # 最多使用前3个食材
        
        try:
            logger.info(f"根据食材搜索菜谱: {ingredient_query}")
            
            # 使用搜索功能
            recipes = self.search_recipes(ingredient_query, limit)
            
            # 进一步筛选包含所有指定食材的菜谱
            if ingredients:
                filtered_recipes = []
                for recipe in recipes:
                    # 检查菜谱是否包含所有指定食材
                    recipe_ingredients = ' '.join(recipe.ingredients).lower()
                    query_ingredients = ' '.join(ingredients).lower()
                    
                    # 简单的包含检查
                    all_found = True
                    for ing in ingredients:
                        if ing.lower() not in recipe_ingredients:
                            all_found = False
                            break
                    
                    if all_found or len(filtered_recipes) < 5:  # 至少返回5个结果
                        filtered_recipes.append(recipe)
                    
                    if len(filtered_recipes) >= limit:
                        break
                
                return filtered_recipes
            
            return recipes
            
        except Exception as e:
            logger.error(f"根据食材搜索失败: {e}")
            return []
    
    def analyze_recipes(self, recipes: List[Recipe]) -> Dict:
        """
        分析菜谱数据
        
        Args:
            recipes: 菜谱对象列表
            
        Returns:
            分析结果字典
        """
        if not recipes:
            return {}
        
        try:
            # 统计信息
            total_recipes = len(recipes)
            
            # 分类统计
            difficulty_counts = {}
            time_counts = {}
            category_counts = {}
            tag_counts = {}
            author_counts = {}
            
            total_rating = 0
            total_made = 0
            total_collect = 0
            high_rated_recipes = 0
            
            all_ingredients = []
            
            for recipe in recipes:
                # 难度统计
                difficulty_counts[recipe.difficulty] = difficulty_counts.get(recipe.difficulty, 0) + 1
                
                # 时间统计
                time_counts[recipe.time] = time_counts.get(recipe.time, 0) + 1
                
                # 分类统计
                if recipe.category:
                    category_counts[recipe.category] = category_counts.get(recipe.category, 0) + 1
                
                # 标签统计
                for tag in recipe.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
                # 作者统计
                author_counts[recipe.author] = author_counts.get(recipe.author, 0) + 1
                
                # 统计数据
                total_rating += recipe.rating
                total_made += recipe.made_count
                total_collect += recipe.collect_count
                
                if recipe.rating >= 4.5:
                    high_rated_recipes += 1
                
                # 收集食材
                all_ingredients.extend(recipe.ingredients)
            
            # 最常见的难度、时间、分类、标签、作者
            top_difficulties = sorted(difficulty_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_times = sorted(time_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            # 最常见的食材
            ingredient_counts = {}
            for ingredient in all_ingredients:
                # 提取主要食材（去除数量和单位）
                clean_ingredient = re.sub(r'^\d+[\.\d]*\s*[克gml勺匙个只片瓣根把适量少许]*\s*', '', ingredient)
                clean_ingredient = clean_ingredient.strip()
                if clean_ingredient and len(clean_ingredient) > 1:
                    ingredient_counts[clean_ingredient] = ingredient_counts.get(clean_ingredient, 0) + 1
            
            top_ingredients = sorted(ingredient_counts.items(), key=lambda x: x[1], reverse=True)[:15]
            
            # 平均统计数据
            avg_rating = total_rating / total_recipes if total_recipes > 0 else 0
            avg_made = total_made / total_recipes if total_recipes > 0 else 0
            avg_collect = total_collect / total_recipes if total_recipes > 0 else 0
            
            # 最受欢迎的菜谱（按做过人数）
            top_made_recipes = sorted(recipes, key=lambda x: x.made_count, reverse=True)[:5]
            
            return {
                'total_recipes': total_recipes,
                'total_made': total_made,
                'total_collect': total_collect,
                'avg_rating': avg_rating,
                'avg_made': avg_made,
                'avg_collect': avg_collect,
                'high_rated_percentage': (high_rated_recipes / total_recipes * 100) if total_recipes > 0 else 0,
                'top_difficulties': top_difficulties,
                'top_times': top_times,
                'top_categories': top_categories,
                'top_tags': top_tags,
                'top_authors': top_authors,
                'top_ingredients': top_ingredients,
                'top_made_recipes': [(r.title[:30], r.made_count) for r in top_made_recipes]
            }
            
        except Exception as e:
            logger.error(f"分析菜谱数据失败: {e}")
            return {}
    
    def save_to_csv(self, recipes: List[Recipe], filename: str = "recipes.csv"):
        """
        保存菜谱数据到CSV文件
        
        Args:
            recipes: 菜谱对象列表
            filename: 输出文件名
        """
        if not recipes:
            logger.warning("没有菜谱数据可保存")
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                fieldnames = [
                    'title', 'url', 'author', 'difficulty', 'time', 'servings',
                    'rating', 'rating_count', 'made_count', 'collect_count',
                    'ingredients', 'steps', 'tips', 'category', 'tags',
                    'image_url', 'calories'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for recipe in recipes:
                    row = recipe.__dict__.copy()
                    # 转换列表为字符串
                    row['ingredients'] = ' | '.join(row['ingredients'])
                    row['steps'] = ' | '.join(row['steps'])
                    row['tags'] = ', '.join(row['tags'])
                    writer.writerow(row)
            
            logger.info(f"已保存 {len(recipes)} 个菜谱数据到 {filename}")
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")


def main():
    """主函数"""
    print("=" * 50)
    print("下厨房菜谱爬虫 v1.0")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = XiachufangCrawler()
    
    try:
        # 1. 显示可用分类
        print("可用菜谱分类:")
        print("-" * 30)
        for key, name in crawler.categories.items():
            print(f"  {key}: {name}")
        print()
        
        # 2. 获取菜谱（可选择分类）
        category_choice = input("请输入分类代码（直接回车获取热门）: ").strip().lower()
        
        if category_choice and category_choice not in crawler.categories:
            print(f"无效分类代码，将获取热门菜谱")
            category_choice = None
        
        print(f"\n正在爬取菜谱数据...")
        recipes = crawler.get_popular_recipes(category=category_choice, limit=20)
        
        if not recipes:
            print("未获取到菜谱数据，程序退出")
            return
        
        # 3. 显示统计信息
        print(f"\n成功获取 {len(recipes)} 个菜谱:")
        print("-" * 50)
        
        # 分析数据
        analysis = crawler.analyze_recipes(recipes)
        
        if analysis:
            print(f"总计菜谱: {analysis['total_recipes']}")
            print(f"总做过次数: {analysis['total_made']:,}")
            print(f"总收藏次数: {analysis['total_collect']:,}")
            print(f"平均评分: {analysis['avg_rating']:.2f}")
            print(f"高评分菜谱: {analysis['high_rated_percentage']:.1f}%")
            
            if analysis['top_difficulties']:
                print("\n难度分布:")
                for difficulty, count in analysis['top_difficulties']:
                    print(f"  {difficulty}: {count} 个")
            
            if analysis['top_times']:
                print("\n烹饪时间分布:")
                for time, count in analysis['top_times'][:3]:
                    print(f"  {time}: {count} 个")
            
            if analysis['top_ingredients']:
                print("\n常用食材TOP 5:")
                for ingredient, count in analysis['top_ingredients'][:5]:
                    print(f"  {ingredient}: {count} 次")
        
        # 4. 显示前5个菜谱详情
        print("\n热门菜谱 TOP 5:")
        print("-" * 30)
        for i, recipe in enumerate(recipes[:5], 1):
            print(f"{i}. {recipe.title}")
            print(f"   作者: {recipe.author}, 难度: {recipe.difficulty}, 时间: {recipe.time}")
            print(f"   评分: {recipe.rating:.1f}, 做过: {recipe.made_count:,}, 收藏: {recipe.collect_count:,}")
            
            if recipe.ingredients:
                print(f"   主要食材: {', '.join(recipe.ingredients[:3])}...")
            
            if recipe.tags:
                print(f"   标签: {', '.join(recipe.tags[:3])}")
            
            print()
        
        # 5. 保存数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"recipes_{timestamp}.csv"
        
        crawler.save_to_csv(recipes, csv_file)
        
        print(f"\n数据已保存到: {csv_file}")
        
        # 6. 展示一个菜谱的详细内容
        if recipes:
            sample_recipe = recipes[0]
            print(f"\n菜谱 '{sample_recipe.title[:20]}...' 的详细内容:")
            print("-" * 30)
            
            print(f"难度: {sample_recipe.difficulty}")
            print(f"时间: {sample_recipe.time}")
            print(f"分量: {sample_recipe.servings}")
            print()
            
            if sample_recipe.ingredients:
                print("食材:")
                for ingredient in sample_recipe.ingredients[:8]:
                    print(f"  - {ingredient}")
                if len(sample_recipe.ingredients) > 8:
                    print(f"  等{len(sample_recipe.ingredients)}种食材")
                print()
            
            if sample_recipe.steps:
                print("步骤:")
                for step in sample_recipe.steps[:5]:
                    print(f"  {step}")
                if len(sample_recipe.steps) > 5:
                    print(f"  共{len(sample_recipe.steps)}个步骤")
                print()
            
            if sample_recipe.tips:
                print(f"小贴士: {sample_recipe.tips[:100]}...")
        
        # 7. 演示根据食材搜索功能
        print("\n" + "=" * 50)
        print("演示根据食材搜索功能:")
        ingredients_input = input("请输入食材（用空格分隔，直接回车跳过）: ").strip()
        
        if ingredients_input:
            ingredients = [ing.strip() for ing in ingredients_input.split() if ing.strip()]
            
            if ingredients:
                print(f"\n正在搜索包含 {', '.join(ingredients)} 的菜谱...")
                ingredient_recipes = crawler.get_recipe_by_ingredients(ingredients, limit=10)
                
                if ingredient_recipes:
                    print(f"找到 {len(ingredient_recipes)} 个相关菜谱:")
                    for i, recipe in enumerate(ingredient_recipes[:5], 1):
                        print(f"{i}. {recipe.title}")
                        print(f"   作者: {recipe.author}, 难度: {recipe.difficulty}")
                        print(f"   评分: {recipe.rating:.1f}, 做过: {recipe.made_count:,}")
                else:
                    print("未找到相关菜谱")
        
        print("\n爬取完成！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()