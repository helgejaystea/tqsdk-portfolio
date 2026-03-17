#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
跨资产轮动策略 (Cross-Asset Rotation Strategy)
基于多资产动量和相关性的动态轮动策略

Author: TqSdk Portfolio
Update: 2026-03-13
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats, optimize
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')


class CrossAssetRotation:
    """跨资产轮动策略"""
    
    def __init__(self, 
                 momentum_period: int = 20,
                 rebalance_period: int = 5,
                 top_n: int = 3,
                 min_momentum: float = -0.1):
        """
        初始化轮动策略
        
        Args:
            momentum_period: 动量计算期（天）
            rebalance_period: 调仓周期（天）
            top_n: 保留动量最强的前N个品种
            min_momentum: 最小动量阈值
        """
        self.momentum_period = momentum_period
        self.rebalance_period = rebalance_period
        self.top_n = top_n
        self.min_momentum = min_momentum
        
        self.price_data = defaultdict(list)
        self.current_positions = {}
        self.rebalance_history = []
        
    def add_price(self, symbol: str, price: float, date: str):
        """添加价格数据"""
        self.price_data[symbol].append({
            'date': date,
            'price': price
        })
        
    def calculate_momentum(self, symbol: str) -> float:
        """计算动量因子"""
        if symbol not in self.price_data:
            return 0.0
            
        prices = self.price_data[symbol]
        
        if len(prices) < self.momentum_period:
            return 0.0
            
        # 计算收益率
        current_price = prices[-1]['price']
        past_price = prices[-self.momentum_period]['price']
        
        momentum = (current_price - past_price) / past_price
        
        return momentum
        
    def calculate_volatility(self, symbol: str) -> float:
        """计算波动率"""
        if symbol not in self.price_data:
            return 0.0
            
        prices = self.price_data[symbol]
        
        if len(prices) < 20:
            return 0.0
            
        returns = []
        for i in range(1, min(21, len(prices))):
            ret = (prices[-i]['price'] - prices[-i-1]['price']) / prices[-i-1]['price']
            returns.append(ret)
            
        return np.std(returns) * np.sqrt(252)
        
    def calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        """计算两个品种的相关性"""
        if symbol1 not in self.price_data or symbol2 not in self.price_data:
            return 0.0
            
        p1 = self.price_data[symbol1]
        p2 = self.price_data[symbol2]
        
        min_len = min(len(p1), len(p2))
        
        if min_len < 20:
            return 0.0
            
        # 对齐价格
        prices1 = [p['price'] for p in p1[-min_len:]]
        prices2 = [p['price'] for p in p2[-min_len:]]
        
        returns1 = np.diff(prices1) / prices1[:-1]
        returns2 = np.diff(prices2) / prices2[:-1]
        
        return np.corrcoef(returns1, returns2)[0, 1]
        
    def rank_assets(self) -> List[Tuple[str, float]]:
        """
        资产排名
        
        Returns:
            [(symbol, score), ...] 按分数降序
        """
        rankings = []
        
        for symbol in self.price_data.keys():
            if len(self.price_data[symbol]) < self.momentum_period:
                continue
                
            momentum = self.calculate_momentum(symbol)
            volatility = self.calculate_volatility(symbol)
            
            # 风险调整动量
            if volatility > 0:
                risk_adjusted_momentum = momentum / volatility
            else:
                risk_adjusted_momentum = momentum
                
            # 动量阈值过滤
            if momentum < self.min_momentum:
                risk_adjusted_momentum = -999  # 排到最后
                
            rankings.append((symbol, risk_adjusted_momentum))
            
        # 排序
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        return rankings
        
    def calculate_correlation_penalty(self, selected_assets: List[str]) -> float:
        """计算相关性惩罚"""
        if len(selected_assets) < 2:
            return 0.0
            
        correlations = []
        for i in range(len(selected_assets)):
            for j in range(i+1, len(selected_assets)):
                corr = self.calculate_correlation(selected_assets[i], selected_assets[j])
                if not np.isnan(corr):
                    correlations.append(corr)
                    
        if not correlations:
            return 0.0
            
        return np.mean(correlations)
        
    def optimize_selection(self) -> Dict:
        """
        优化资产选择
        
        Returns:
            优化结果
        """
        rankings = self.rank_assets()
        
        if len(rankings) == 0:
            return {'status': 'NO_DATA'}
            
        # 选择top N
        selected = [r[0] for r in rankings[:self.top_n]]
        
        # 检查相关性
        avg_corr = self.calculate_correlation_penalty(selected)
        
        # 如果相关性过高，尝试替换
        if avg_corr > 0.7 and len(rankings) > self.top_n:
            # 找到相关性最低的替换
            for i in range(self.top_n, len(rankings)):
                candidate = rankings[i][0]
                
                # 计算候选品种与已选品种的平均相关性
                cand_corrs = []
                for sel in selected:
                    corr = self.calculate_correlation(candidate, sel)
                    if not np.isnan(corr):
                        cand_corrs.append(corr)
                        
                if cand_corrs and np.mean(cand_corrs) < avg_corr:
                    # 替换
                    selected[-1] = candidate
                    avg_corr = self.calculate_correlation_penalty(selected)
                    break
                    
        return {
            'status': 'SUCCESS',
            'selected_assets': selected,
            'average_correlation': avg_corr,
            'momentum_scores': {r[0]: r[1] for r in rankings[:self.top_n]}
        }
        
    def rebalance(self) -> Dict:
        """执行调仓"""
        optimization = self.optimize_selection()
        
        if optimization.get('status') != 'SUCCESS':
            return optimization
            
        # 等权分配
        n = len(optimization['selected_assets'])
        weight = 1.0 / n if n > 0 else 0
        
        new_positions = {}
        for asset in optimization['selected_assets']:
            new_positions[asset] = weight
            
        # 记录调仓
        self.rebalance_history.append({
            'timestamp': datetime.now().isoformat(),
            'previous_positions': self.current_positions.copy(),
            'new_positions': new_positions.copy(),
            'changes': self._calculate_changes(self.current_positions, new_positions)
        })
        
        self.current_positions = new_positions
        
        return {
            'status': 'SUCCESS',
            'positions': new_positions,
            'average_correlation': optimization['average_correlation']
        }
        
    def _calculate_changes(self, old: Dict, new: Dict) -> Dict:
        """计算仓位变化"""
        all_assets = set(old.keys()) | set(new.keys())
        
        changes = {}
        for asset in all_assets:
            old_weight = old.get(asset, 0)
            new_weight = new.get(asset, 0)
            changes[asset] = new_weight - old_weight
            
        return changes
        
    def get_rotation_signal(self) -> str:
        """获取轮动信号"""
        if not self.current_positions:
            return 'INITIALIZE'
            
        # 检查是否需要调仓
        if len(self.rebalance_history) > 0:
            last_rebalance = self.rebalance_history[-1]
            
            # 计算距上次调仓天数
            last_date = datetime.fromisoformat(last_rebalance['timestamp'])
            days_since = (datetime.now() - last_date).days
            
            if days_since >= self.rebalance_period:
                return 'REBALANCE'
                
        # 检查动量是否反转
        rankings = self.rank_assets()
        
        if rankings:
            current_best = rankings[0][0]
            current_positions = list(self.current_positions.keys())
            
            if current_best not in current_positions:
                return 'ROTATE'
                
        return 'HOLD'


class SectorRotation:
    """行业轮动策略"""
    
    def __init__(self, 
                 sectors: Optional[Dict[str, List[str]]] = None,
                 momentum_period: int = 20):
        """
        初始化行业轮动
        
        Args:
            sectors: 行业定义 {sector_name: [symbols]}
            momentum_period: 动量周期
        """
        self.sectors = sectors or {
            '黑色金属': ['SHFE.rb', 'SHFE.hc', 'SHFE.i'],
            '化工': ['DCE.m', 'DCE.pp', 'DCE.l'],
            '农产品': ['DCE.a', 'DCE.b', 'CZCE.CF', 'CZCE.SR'],
            '有色金属': ['SHFE.cu', 'SHFE.al', 'SHFE.zn'],
            '能源': ['SHFE.fu', 'CZCE.sc', 'DCE.jm']
        }
        
        self.momentum_period = momentum_period
        self.sector_prices = defaultdict(list)
        self.sector_momentum = {}
        
    def add_sector_price(self, sector: str, price: float):
        """添加行业指数价格"""
        self.sector_prices[sector].append(price)
        
    def calculate_sector_momentum(self, sector: str) -> float:
        """计算行业动量"""
        if sector not in self.sector_prices:
            return 0.0
            
        prices = self.sector_prices[sector]
        
        if len(prices) < self.momentum_period:
            return 0.0
            
        return (prices[-1] - prices[-self.momentum_period]) / prices[-self.momentum_period]
        
    def rank_sectors(self) -> List[Tuple[str, float]]:
        """行业排名"""
        rankings = []
        
        for sector in self.sectors.keys():
            momentum = self.calculate_sector_momentum(sector)
            rankings.append((sector, momentum))
            
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        return rankings
        
    def generate_sector_weights(self, 
                               top_n: int = 3,
                               momentum_threshold: float = 0.0) -> Dict:
        """
        生成行业权重
        
        Args:
            top_n: 保留前N个行业
            momentum_threshold: 动量阈值
            
        Returns:
            {sector: weight}
        """
        rankings = self.rank_sectors()
        
        # 过滤动量阈值
        filtered = [(s, m) for s, m in rankings if m > momentum_threshold]
        
        if not filtered:
            # 如果没有满足阈值的，返回最安全的配置
            n = min(3, len(rankings))
            filtered = rankings[:n]
            
        # 等权分配
        n = len(filtered)
        weight = 1.0 / n
        
        weights = {sector: weight for sector, _ in filtered}
        
        return weights
        
    def get_sector_attribution(self, 
                             portfolio_return: float,
                             sector_weights: Dict[str, float]) -> Dict:
        """
        计算行业归因
        
        Args:
            portfolio_return: 组合收益
            sector_weights: 行业权重
            
        Returns:
            归因分析
        """
        attributions = {}
        
        for sector, weight in sector_weights.items():
            momentum = self.calculate_sector_momentum(sector)
            
            # 简化归因
            attributions[sector] = {
                'weight': weight,
                'momentum': momentum,
                'contribution': weight * momentum
            }
            
        total_contribution = sum(a['contribution'] for a in attributions.values())
        
        return {
            'attributions': attributions,
            'total_contribution': total_contribution,
            'portfolio_return': portfolio_return
        }


class DualMomentumRotation:
    """双动量轮动策略"""
    
    def __init__(self, 
                 short_period: int = 10,
                 long_period: int = 60,
                 relative_period: int = 20):
        """
        初始化双动量策略
        
        Args:
            short_period: 短期动量周期
            long_period: 长期动量周期
            relative_period: 相对动量周期
        """
        self.short_period = short_period
        self.long_period = long_period
        self.relative_period = relative_period
        
        self.assets_data = defaultdict(list)
        
    def add_asset_data(self, symbol: str, price: float):
        """添加资产数据"""
        self.assets_data[symbol].append(price)
        
    def calculate_absolute_momentum(self, symbol: str, period: int) -> float:
        """计算绝对动量"""
        if symbol not in self.assets_data:
            return 0.0
            
        prices = self.assets_data[symbol]
        
        if len(prices) < period + 1:
            return 0.0
            
        return (prices[-1] - prices[-period]) / prices[-period]
        
    def calculate_relative_momentum(self, symbol: str, 
                                   benchmark: str) -> float:
        """计算相对动量"""
        symbol_mom = self.calculate_absolute_momentum(symbol, self.relative_period)
        bench_mom = self.calculate_absolute_momentum(benchmark, self.relative_period)
        
        return symbol_mom - bench_mom
        
    def dual_momentum_signal(self, symbol: str, benchmark: str) -> Dict:
        """
        双动量信号
        
        Args:
            symbol: 目标品种
            benchmark: 基准品种
            
        Returns:
            动量信号
        """
        short_mom = self.calculate_absolute_momentum(symbol, self.short_period)
        long_mom = self.calculate_absolute_momentum(symbol, self.long_period)
        relative_mom = self.calculate_relative_momentum(symbol, benchmark)
        
        # 信号判断
        if long_mom > 0 and relative_mom > 0:
            signal = 'BUY'
        elif long_mom < -0.1:
            signal = 'SELL'
        elif short_mom < 0 and relative_mom < 0:
            signal = 'SHORT'
        elif abs(relative_mom) < 0.01:
            signal = 'NEUTRAL'
        else:
            signal = 'MONITOR'
            
        return {
            'symbol': symbol,
            'short_momentum': short_mom,
            'long_momentum': long_mom,
            'relative_momentum': relative_mom,
            'signal': signal
        }


def main():
    """主函数 - 演示用法"""
    # 创建跨资产轮动策略
    rotation = CrossAssetRotation(
        momentum_period=20,
        rebalance_period=5,
        top_n=3
    )
    
    # 添加模拟数据
    np.random.seed(42)
    symbols = ['SHFE.rb', 'DCE.m', 'CZCE.CF', 'DCE.y', 'CZCE.SR', 'SHFE.cu']
    
    for day in range(100):
        for symbol in symbols:
            # 模拟不同趋势
            if symbol == 'SHFE.rb':
                price = 3800 + day * 2 + np.random.randn() * 10
            elif symbol == 'DCE.m':
                price = 2800 + day * 1 + np.random.randn() * 8
            else:
                price = 1000 + np.random.randn() * 20
                
            rotation.add_price(symbol, price, f"2024-01-{day+1:02d}")
            
    # 资产排名
    rankings = rotation.rank_assets()
    print("=== 资产排名 ===")
    for symbol, score in rankings:
        print(f"{symbol}: {score:.4f}")
        
    # 优化选择
    optimization = rotation.optimize_selection()
    print(f"\n=== 优化选择 ===")
    print(f"选中资产: {optimization.get('selected_assets')}")
    print(f"平均相关性: {optimization.get('average_correlation', 0):.4f}")
    
    # 调仓
    result = rotation.rebalance()
    print(f"\n=== 调仓结果 ===")
    print(f"新仓位: {result.get('positions')}")
    
    # 轮动信号
    signal = rotation.get_rotation_signal()
    print(f"\n轮动信号: {signal}")
    
    # 行业轮动
    print("\n=== 行业轮动 ===")
    sector_rot = SectorRotation()
    
    sectors_data = {
        '黑色金属': [3800 + i * 3 for i in range(60)],
        '化工': [2800 + i * 1 for i in range(60)],
        '农产品': [1000 + i * 0.5 for i in range(60)]
    }
    
    for sector, prices in sectors_data.items():
        for price in prices:
            sector_rot.add_sector_price(sector, price)
            
    sector_rankings = sector_rot.rank_sectors()
    print("行业排名:")
    for sector, momentum in sector_rankings:
        print(f"  {sector}: {momentum:.4f}")
        
    sector_weights = sector_rot.generate_sector_weights(top_n=2)
    print(f"行业权重: {sector_weights}")


if __name__ == "__main__":
    main()
