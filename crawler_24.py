#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
体育赛事数据爬虫 - NBA比赛信息和球员数据
爬取NBA比赛数据：赛程、比分、球员统计、球队排名等
"""

import requests
import json
import time
import re
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
import csv
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class NBAGame:
    """NBA比赛数据结构"""
    game_id: str
    date: str  # 比赛日期
    time: str  # 比赛时间
    status: str  # 比赛状态: scheduled, in_progress, finished
    home_team: str  # 主队
    away_team: str  # 客队
    home_score: int  # 主队得分
    away_score: int  # 客队得分
    period: str  # 当前节次/加时
    arena: str  # 比赛场馆
    tv_broadcast: str  # 电视转播
    home_record: str  # 主队战绩
    away_record: str  # 客队战绩


@dataclass
class NBAPlayer:
    """NBA球员数据结构"""
    name: str
    team: str
    position: str  # 位置
    jersey_number: int  # 球衣号码
    points: float  # 场均得分
    rebounds: float  # 场均篮板
    assists: float  # 场均助攻
    steals: float  # 场均抢断
    blocks: float  # 场均盖帽
    field_goal_pct: float  # 投篮命中率
    three_point_pct: float  # 三分命中率
    free_throw_pct: float  # 罚球命中率
    minutes: float  # 场均上场时间
    games_played: int  # 出场次数


@dataclass
class NBATeam:
    """NBA球队数据结构"""
    name: str
    abbreviation: str  # 缩写
    conference: str  # 分区: East, West
    division: str  # 赛区
    wins: int  # 胜场
    losses: int  # 负场
    win_percentage: float  # 胜率
    games_behind: float  # 胜场差
    streak: str  # 连胜/连败
    home_record: str  # 主场战绩
    road_record: str  # 客场战绩


class NBACrawler:
    """NBA数据爬虫类"""
    
    def __init__(self):
        self.base_url = "https://site.api.espn.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Origin': 'https://www.espn.com',
            'Referer': 'https://www.espn.com/',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # NBA球队映射
        self.team_mapping = {
            'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BKN': 'Brooklyn Nets',
            'CHA': 'Charlotte Hornets', 'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers',
            'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets', 'DET': 'Detroit Pistons',
            'GS': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
            'LAC': 'LA Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies',
            'MIA': 'Miami Heat', 'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves',
            'NO': 'New Orleans Pelicans', 'NY': 'New York Knicks', 'OKC': 'Oklahoma City Thunder',
            'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns',
            'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SA': 'San Antonio Spurs',
            'TOR': 'Toronto Raptors', 'UTAH': 'Utah Jazz', 'WAS': 'Washington Wizards'
        }
    
    def get_schedule(self, days: int = 7) -> List[NBAGame]:
        """
        获取NBA赛程
        
        Args:
            days: 获取未来多少天的赛程
            
        Returns:
            比赛对象列表
        """
        url = f"{self.base_url}/apis/site/v2/sports/basketball/nba/scoreboard"
        
        # 计算日期范围
        all_games = []
        
        for day_offset in range(days):
            try:
                game_date = (datetime.now() + timedelta(days=day_offset)).strftime('%Y%m%d')
                params = {'dates': game_date}
                
                logger.info(f"正在获取 {game_date} 的赛程")
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # 解析比赛数据
                for event in data.get('events', []):
                    game = self._parse_game_event(event)
                    if game:
                        all_games.append(game)
                
                # 避免请求过快
                time.sleep(0.5)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"获取赛程失败: {e}")
                continue
            except Exception as e:
                logger.error(f"解析赛程失败: {e}")
                continue
        
        logger.info(f"成功获取 {len(all_games)} 场比赛")
        return all_games
    
    def _parse_game_event(self, event: Dict) -> Optional[NBAGame]:
        """解析比赛事件数据"""
        try:
            game_id = event.get('id', '')
            
            # 比赛信息
            competition = event.get('competitions', [{}])[0]
            
            # 队伍信息
            competitors = competition.get('competitors', [])
            if len(competitors) < 2:
                return None
            
            # 确定主客队
            home_competitor = None
            away_competitor = None
            
            for competitor in competitors:
                if competitor.get('homeAway') == 'home':
                    home_competitor = competitor
                else:
                    away_competitor = competitor
            
            if not home_competitor or not away_competitor:
                return None
            
            # 球队名称
            home_team = home_competitor.get('team', {}).get('displayName', '')
            away_team = away_competitor.get('team', {}).get('displayName', '')
            
            # 比分
            home_score = int(home_competitor.get('score', 0))
            away_score = int(away_competitor.get('score', 0))
            
            # 比赛状态
            status = event.get('status', {})
            status_type = status.get('type', {}).get('description', 'Scheduled')
            period = status.get('period', 0)
            
            # 转换状态描述
            if status_type == 'STATUS_FINAL':
                game_status = 'finished'
                period_display = 'Final'
            elif status_type == 'STATUS_IN_PROGRESS':
                game_status = 'in_progress'
                period_display = f'Q{period}' if period <= 4 else f'OT{period-4}'
            else:
                game_status = 'scheduled'
                period_display = ''
            
            # 比赛时间
            date_str = event.get('date', '')
            if date_str:
                try:
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    # 转换为本地时间
                    local_dt = dt.astimezone()
                    date_display = local_dt.strftime('%Y-%m-%d')
                    time_display = local_dt.strftime('%H:%M')
                except:
                    date_display = ''
                    time_display = ''
            else:
                date_display = ''
                time_display = ''
            
            # 场馆和转播
            venue = competition.get('venue', {}).get('fullName', '')
            broadcasts = competition.get('broadcasts', [])
            tv_stations = [b.get('names', [])[0] for b in broadcasts if b.get('names')]
            tv_display = ', '.join(tv_stations[:2]) if tv_stations else ''
            
            # 战绩
            home_record = f"{home_competitor.get('records', [{}])[0].get('summary', '0-0')}"
            away_record = f"{away_competitor.get('records', [{}])[0].get('summary', '0-0')}"
            
            game = NBAGame(
                game_id=game_id,
                date=date_display,
                time=time_display,
                status=game_status,
                home_team=home_team,
                away_team=away_team,
                home_score=home_score,
                away_score=away_score,
                period=period_display,
                arena=venue,
                tv_broadcast=tv_display,
                home_record=home_record,
                away_record=away_record
            )
            
            return game
            
        except Exception as e:
            logger.warning(f"解析比赛事件失败: {e}")
            return None
    
    def get_standings(self) -> List[NBATeam]:
        """
        获取NBA球队排名
        
        Returns:
            球队对象列表
        """
        url = f"{self.base_url}/apis/site/v2/sports/basketball/nba/standings"
        
        try:
            logger.info("正在获取NBA球队排名")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            teams = []
            
            # 解析分区数据
            for conference in data.get('children', []):
                conf_name = conference.get('name', '')
                
                for division in conference.get('children', []):
                    for team_data in division.get('standings', {}).get('entries', []):
                        team = self._parse_team_data(team_data, conf_name)
                        if team:
                            teams.append(team)
            
            logger.info(f"成功获取 {len(teams)} 支球队排名")
            return teams
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取排名失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析排名失败: {e}")
            return []
    
    def _parse_team_data(self, team_data: Dict, conference: str) -> Optional[NBATeam]:
        """解析球队数据"""
        try:
            team_info = team_data.get('team', {})
            stats = team_data.get('stats', [])
            
            # 提取统计数据
            stats_dict = {}
            for stat in stats:
                stats_dict[stat.get('name')] = stat.get('value')
            
            # 确定赛区
            division_map = {
                'Atlantic': 'Atlantic',
                'Central': 'Central', 
                'Southeast': 'Southeast',
                'Northwest': 'Northwest',
                'Pacific': 'Pacific',
                'Southwest': 'Southwest'
            }
            
            division = team_info.get('division', {}).get('displayName', '')
            if division not in division_map:
                # 根据球队推断赛区
                team_name = team_info.get('displayName', '')
                if 'Atlantic' in team_name or team_name in ['Celtics', 'Knicks', '76ers', 'Nets', 'Raptors']:
                    division = 'Atlantic'
                elif 'Central' in team_name or team_name in ['Bulls', 'Cavaliers', 'Pistons', 'Pacers', 'Bucks']:
                    division = 'Central'
                elif 'Southeast' in team_name or team_name in ['Hawks', 'Hornets', 'Heat', 'Magic', 'Wizards']:
                    division = 'Southeast'
                elif 'Northwest' in team_name or team_name in ['Nuggets', 'Timberwolves', 'Thunder', 'Trail Blazers', 'Jazz']:
                    division = 'Northwest'
                elif 'Pacific' in team_name or team_name in ['Warriors', 'Clippers', 'Lakers', 'Suns', 'Kings']:
                    division = 'Pacific'
                elif 'Southwest' in team_name or team_name in ['Mavericks', 'Rockets', 'Grizzlies', 'Pelicans', 'Spurs']:
                    division = 'Southwest'
            
            team = NBATeam(
                name=team_info.get('displayName', ''),
                abbreviation=team_info.get('abbreviation', ''),
                conference=conference,
                division=division,
                wins=int(stats_dict.get('wins', 0)),
                losses=int(stats_dict.get('losses', 0)),
                win_percentage=float(stats_dict.get('winPercent', 0)),
                games_behind=float(stats_dict.get('gamesBehind', 0)),
                streak=stats_dict.get('streak', ''),
                home_record=stats_dict.get('homeRecord', '0-0'),
                road_record=stats_dict.get('awayRecord', '0-0')
            )
            
            return team
            
        except Exception as e:
            logger.warning(f"解析球队数据失败: {e}")
            return None
    
    def get_player_stats(self, limit: int = 50) -> List[NBAPlayer]:
        """
        获取NBA球员统计数据
        
        Args:
            limit: 获取球员数量
            
        Returns:
            球员对象列表
        """
        # 注意：ESPN API对球员统计数据的访问有限制
        # 这里使用模拟数据或简化版本
        
        logger.warning("ESPN球员统计API受限，返回模拟数据")
        
        # 模拟球员数据（实际应用中应使用真实API）
        mock_players = [
            NBAPlayer(
                name="Stephen Curry",
                team="Golden State Warriors",
                position="PG",
                jersey_number=30,
                points=26.4,
                rebounds=4.5,
                assists=5.1,
                steals=1.2,
                blocks=0.2,
                field_goal_pct=0.472,
                three_point_pct=0.403,
                free_throw_pct=0.923,
                minutes=34.7,
                games_played=65
            ),
            NBAPlayer(
                name="LeBron James",
                team="Los Angeles Lakers",
                position="SF",
                jersey_number=23,
                points=25.3,
                rebounds=7.3,
                assists=8.1,
                steals=1.2,
                blocks=0.6,
                field_goal_pct=0.503,
                three_point_pct=0.345,
                free_throw_pct=0.741,
                minutes=35.5,
                games_played=62
            ),
            NBAPlayer(
                name="Kevin Durant",
                team="Phoenix Suns",
                position="SF",
                jersey_number=35,
                points=27.1,
                rebounds=6.6,
                assists=5.0,
                steals=0.9,
                blocks=1.2,
                field_goal_pct=0.525,
                three_point_pct=0.416,
                free_throw_pct=0.885,
                minutes=37.2,
                games_played=68
            ),
            NBAPlayer(
                name="Nikola Jokic",
                team="Denver Nuggets",
                position="C",
                jersey_number=15,
                points=26.4,
                rebounds=12.4,
                assists=9.0,
                steals=1.4,
                blocks=0.9,
                field_goal_pct=0.583,
                three_point_pct=0.357,
                free_throw_pct=0.821,
                minutes=34.6,
                games_played=70
            ),
            NBAPlayer(
                name="Giannis Antetokounmpo",
                team="Milwaukee Bucks",
                position="PF",
                jersey_number=34,
                points=30.4,
                rebounds=11.5,
                assists=6.5,
                steals=1.2,
                blocks=1.1,
                field_goal_pct=0.611,
                three_point_pct=0.274,
                free_throw_pct=0.656,
                minutes=32.6,
                games_played=63
            )
        ]
        
        # 只返回指定数量的球员
        return mock_players[:limit]
    
    def analyze_schedule(self, games: List[NBAGame]) -> Dict:
        """
        分析赛程数据
        
        Args:
            games: 比赛对象列表
            
        Returns:
            分析结果字典
        """
        if not games:
            return {}
        
        try:
            # 统计信息
            total_games = len(games)
            scheduled_games = sum(1 for game in games if game.status == 'scheduled')
            in_progress_games = sum(1 for game in games if game.status == 'in_progress')
            finished_games = sum(1 for game in games if game.status == 'finished')
            
            # 按日期分组
            games_by_date = {}
            for game in games:
                date = game.date
                if date not in games_by_date:
                    games_by_date[date] = []
                games_by_date[date].append(game)
            
            # 最忙碌的日期
            busiest_dates = sorted(games_by_date.items(), key=lambda x: len(x[1]), reverse=True)[:3]
            
            # 球队出场次数
            team_appearances = {}
            for game in games:
                for team in [game.home_team, game.away_team]:
                    team_appearances[team] = team_appearances.get(team, 0) + 1
            
            busiest_teams = sorted(team_appearances.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'total_games': total_games,
                'scheduled_games': scheduled_games,
                'in_progress_games': in_progress_games,
                'finished_games': finished_games,
                'busiest_dates': [(date, len(games)) for date, games in busiest_dates],
                'busiest_teams': busiest_teams
            }
            
        except Exception as e:
            logger.error(f"分析赛程数据失败: {e}")
            return {}
    
    def save_to_csv(self, data: List, filename: str, data_type: str = "games"):
        """
        保存数据到CSV文件
        
        Args:
            data: 数据对象列表
            filename: 输出文件名
            data_type: 数据类型 (games, teams, players)
        """
        if not data:
            logger.warning(f"没有{data_type}数据可保存")
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                if data_type == "games":
                    fieldnames = [
                        'game_id', 'date', 'time', 'status', 'home_team', 'away_team',
                        'home_score', 'away_score', 'period', 'arena', 'tv_broadcast',
                        'home_record', 'away_record'
                    ]
                elif data_type == "teams":
                    fieldnames = [
                        'name', 'abbreviation', 'conference', 'division', 'wins', 'losses',
                        'win_percentage', 'games_behind', 'streak', 'home_record', 'road_record'
                    ]
                elif data_type == "players":
                    fieldnames = [
                        'name', 'team', 'position', 'jersey_number', 'points', 'rebounds',
                        'assists', 'steals', 'blocks', 'field_goal_pct', 'three_point_pct',
                        'free_throw_pct', 'minutes', 'games_played'
                    ]
                else:
                    logger.error(f"不支持的数据类型: {data_type}")
                    return
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for item in data:
                    writer.writerow(item.__dict__)
            
            logger.info(f"已保存 {len(data)} 条{data_type}数据到 {filename}")
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")


def main():
    """主函数"""
    print("=" * 50)
    print("NBA数据爬虫 v1.0")
    print("=" * 50)
    
    # 创建爬虫实例
    crawler = NBACrawler()
    
    try:
        # 1. 获取赛程
        print("正在获取NBA赛程...")
        games = crawler.get_schedule(days=3)
        
        # 2. 获取球队排名
        print("正在获取NBA球队排名...")
        teams = crawler.get_standings()
        
        # 3. 获取球员数据
        print("正在获取NBA球员数据...")
        players = crawler.get_player_stats(limit=10)
        
        # 4. 显示统计信息
        if games:
            print(f"\n成功获取 {len(games)} 场比赛:")
            print("-" * 50)
            
            # 分析赛程
            schedule_analysis = crawler.analyze_schedule(games)
            
            if schedule_analysis:
                print(f"总计比赛: {schedule_analysis['total_games']}")
                print(f"已结束: {schedule_analysis['finished_games']}")
                print(f"进行中: {schedule_analysis['in_progress_games']}")
                print(f"未开始: {schedule_analysis['scheduled_games']}")
                
                print("\n比赛最多的日期:")
                for date, count in schedule_analysis['busiest_dates']:
                    print(f"  {date}: {count} 场比赛")
                
                print("\n赛程最密集的球队:")
                for team, count in schedule_analysis['busiest_teams']:
                    print(f"  {team}: {count} 场比赛")
            
            # 显示今日比赛
            today = datetime.now().strftime('%Y-%m-%d')
            today_games = [g for g in games if g.date == today]
            
            if today_games:
                print(f"\n今日比赛 ({today}):")
                print("-" * 30)
                for game in today_games:
                    if game.status == 'finished':
                        print(f"{game.away_team} {game.away_score} - {game.home_score} {game.home_team} (结束)")
                    elif game.status == 'in_progress':
                        print(f"{game.away_team} {game.away_score} - {game.home_score} {game.home_team} ({game.period})")
                    else:
                        print(f"{game.away_team} @ {game.home_team} - {game.time}")
                    print(f"  场馆: {game.arena}, 转播: {game.tv_broadcast}")
                    print()
        
        # 5. 显示球队排名
        if teams:
            print("\nNBA球队排名:")
            print("-" * 50)
            
            # 按分区显示
            for conference in ['Eastern', 'Western']:
                conf_teams = [t for t in teams if t.conference == conference]
                if not conf_teams:
                    continue
                
                print(f"\n{conference} Conference:")
                print("排名 | 球队 | 战绩 | 胜率 | 胜场差 | 连胜")
                print("-" * 60)
                
                sorted_teams = sorted(conf_teams, key=lambda x: x.win_percentage, reverse=True)
                
                for i, team in enumerate(sorted_teams[:8], 1):
                    print(f"{i:2d}. {team.name:20s} {team.wins}-{team.losses} "
                          f"{team.win_percentage:.3f} {team.games_behind:5.1f} {team.streak}")
        
        # 6. 显示球员数据
        if players:
            print("\nNBA球员数据 (TOP 5):")
            print("-" * 50)
            print("球员 | 球队 | 位置 | 得分 | 篮板 | 助攻 | 命中率%")
            print("-" * 60)
            
            for i, player in enumerate(players[:5], 1):
                print(f"{i}. {player.name:15s} {player.team:20s} {player.position:3s} "
                      f"{player.points:5.1f} {player.rebounds:5.1f} {player.assists:5.1f} "
                      f"{player.field_goal_pct*100:5.1f}")
        
        # 7. 保存数据
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if games:
            csv_file = f"nba_games_{timestamp}.csv"
            crawler.save_to_csv(games, csv_file, "games")
            print(f"\n赛程数据已保存到: {csv_file}")
        
        if teams:
            csv_file = f"nba_teams_{timestamp}.csv"
            crawler.save_to_csv(teams, csv_file, "teams")
            print(f"球队数据已保存到: {csv_file}")
        
        if players:
            csv_file = f"nba_players_{timestamp}.csv"
            crawler.save_to_csv(players, csv_file, "players")
            print(f"球员数据已保存到: {csv_file}")
        
        print("\n爬取完成！")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"程序运行出错: {e}")


if __name__ == "__main__":
    main()