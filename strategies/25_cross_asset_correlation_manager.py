#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 25
策略名称: 跨资产相关性管理器
生成日期: 2026-03-16
仓库地址: tqsdk-portfolio
================================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【TqSdk 简介】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TqSdk（天勤量化 SDK）是由信易科技（北京）有限公司开发的专业期货量化交易框架，
完全免费开源（Apache 2.0 协议），基于 Python 语言设计，支持 Python 3.6+ 环境。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】
跨资产相关性管理器实时监控多资产组合的相关性动态，
在相关性突变时触发预警并提供仓位调整建议，实现分散化投资。

【策略参数】
- LOOKBACK_DAYS: 相关性计算回溯期
- CORRELATION_THRESHOLD: 相关性阈值
- REBALANCE_TRIGGER: 再平衡触发条件
================================================================================
"""

from tqsdk import TqApi, TqAuth
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import json

# ============ 参数配置 ============
LOOKBACK_DAYS = 30             # 相关性计算回溯期
CORRELATION_THRESHOLD = 0.7   # 高相关性阈值
CORRELATION_CHANGE_THRESHOLD = 0.2 # 相关性变化阈值
VOLATILITY_WINDOW = 20         # 波动率窗口


class CrossAssetCorrelationManager:
    """跨资产相关性管理器"""
    
    def __init__(self, api, symbols):
        self.api = api
        self.symbols = symbols
        self.price_history = defaultdict(list)
        self.correlation_matrix = None
        self.previous_correlation = None
        self.alerts = []
        
    def update_prices(self, symbol, price):
        """更新价格历史"""
        self.price_history[symbol].append({
            'time': datetime.now(),
            'price': price
        })
        
        # 保持历史长度
        max_len = LOOKBACK_DAYS + 10
        if len(self.price_history[symbol]) > max_len:
            self.price_history[symbol] = self.price_history[symbol][-max_len:]
    
    def calculate_returns(self, symbol):
        """计算收益率序列"""
        prices = self.price_history.get(symbol, [])
        
        if len(prices) < 5:
            return pd.Series()
        
        price_values = [p['price'] for p in prices]
        returns = pd.Series(price_values).pct_change().dropna()
        
        return returns
    
    def calculate_correlation_matrix(self):
        """计算相关性矩阵"""
        returns_dict = {}
        
        for symbol in self.symbols:
            returns = self.calculate_returns(symbol)
            if len(returns) > 5:
                returns_dict[symbol] = returns
        
        if len(returns_dict) < 2:
            return None
        
        # 创建DataFrame
        returns_df = pd.DataFrame(returns_dict)
        
        # 计算相关性矩阵
        corr_matrix = returns_df.corr()
        
        self.previous_correlation = self.correlation_matrix
        self.correlation_matrix = corr_matrix
        
        return corr_matrix
    
    def calculate_volatility(self, symbol):
        """计算波动率"""
        returns = self.calculate_returns(symbol)
        
        if len(returns) < 2:
            return 0.0
        
        return returns.std() * np.sqrt(252)
    
    def calculate_rolling_correlation(self, symbol1, symbol2, window=20):
        """计算滚动相关性"""
        prices1 = self.price_history.get(symbol1, [])
        prices2 = self.price_history.get(symbol2, [])
        
        if len(prices1) < window or len(prices2) < window:
            return None
        
        returns1 = pd.Series([p['price'] for p in prices1[-window:]]).pct_change().dropna()
        returns2 = pd.Series([p['price'] for p in prices2[-window:]]).pct_change().dropna()
        
        min_len = min(len(returns1), len(returns2))
        
        if min_len < 10:
            return None
        
        return returns1.iloc[:min_len].corr(returns2.iloc[:min_len])
    
    def detect_correlation_change(self):
        """检测相关性变化"""
        if self.previous_correlation is None or self.correlation_matrix is None:
            return []
        
        changes = []
        
        for i, sym1 in enumerate(self.symbols):
            for j, sym2 in enumerate(self.symbols):
                if i >= j:
                    continue
                
                try:
                    prev = self.previous_correlation.loc[sym1, sym2]
                    curr = self.correlation_matrix.loc[sym1, sym2]
                    
                    change = abs(curr - prev)
                    
                    if change > CORRELATION_CHANGE_THRESHOLD:
                        changes.append({
                            'pair': f"{sym1}-{sym2}",
                            'previous': prev,
                            'current': curr,
                            'change': change,
                            'direction': 'increased' if curr > prev else 'decreased'
                        })
                except:
                    continue
        
        self.alerts.extend(changes)
        return changes
    
    def find_high_correlation_pairs(self):
        """找出高相关性品种对"""
        if self.correlation_matrix is None:
            return []
        
        high_corr = []
        
        for i, sym1 in enumerate(self.symbols):
            for j, sym2 in enumerate(self.symbols):
                if i >= j:
                    continue
                
                try:
                    corr = self.correlation_matrix.loc[sym1, sym2]
                    
                    if abs(corr) > CORRELATION_THRESHOLD:
                        vol1 = self.calculate_volatility(sym1)
                        vol2 = self.calculate_volatility(sym2)
                        
                        high_corr.append({
                            'pair': f"{sym1}-{sym2}",
                            'correlation': corr,
                            'volatility_1': vol1,
                            'volatility_2': vol2,
                            '分散化收益': vol1 * vol2 * (1 - abs(corr))
                        })
                except:
                    continue
        
        return sorted(high_corr, key=lambda x: -abs(x['correlation']))
    
    def suggest_rebalancing(self):
        """建议仓位调整"""
        suggestions = []
        
        high_corr_pairs = self.find_high_correlation_pairs()
        
        for pair_info in high_corr_pairs:
            pair = pair_info['pair']
            sym1, sym2 = pair.split('-')
            
            vol1 = pair_info['volatility_1']
            vol2 = pair_info['volatility_2']
            
            # 基于波动率调整仓位
            if vol1 > 0 and vol2 > 0:
                # 风险平价调整
                weight1 = vol2 / (vol1 + vol2)
                weight2 = vol1 / (vol1 + vol2)
                
                suggestions.append({
                    'action': 'reduce',
                    'pair': pair,
                    'reason': f"相关性过高 ({pair_info['correlation']:.2f})",
                    'suggested_weights': {sym1: weight1, sym2: weight2}
                })
        
        return suggestions
    
    def calculate_diversification_benefit(self):
        """计算分散化收益"""
        if self.correlation_matrix is None:
            return 0.0
        
        # 组合波动率估计
        volatilities = {s: self.calculate_volatility(s) for s in self.symbols}
        
        if len(volatilities) < 2:
            return 0.0
        
        avg_vol = np.mean(list(volatilities.values()))
        
        # 平均相关性
        corr_values = []
        for i, s1 in enumerate(self.symbols):
            for j, s2 in enumerate(self.symbols):
                if i < j:
                    try:
                        corr_values.append(abs(self.correlation_matrix.loc[s1, s2]))
                    except:
                        pass
        
        avg_corr = np.mean(corr_values) if corr_values else 0
        
        # 分散化比率
        diversification_ratio = avg_vol * (1 - avg_corr)
        
        return diversification_ratio
    
    def generate_report(self):
        """生成相关性报告"""
        report = "=" * 60 + "\n"
        report += "跨资产相关性管理报告\n"
        report += "=" * 60 + "\n"
        report += f"分析品种数: {len(self.symbols)}\n"
        report += f"回溯期: {LOOKBACK_DAYS} 天\n"
        report += f"高相关阈值: {CORRELATION_THRESHOLD}\n\n"
        
        # 相关性矩阵
        if self.correlation_matrix is not None:
            report += "相关性矩阵:\n"
            report += self.correlation_matrix.round(3).to_string() + "\n\n"
        
        # 高相关对
        high_corr = self.find_high_correlation_pairs()
        
        if high_corr:
            report += "⚠️ 高相关性品种对 (需关注):\n"
            for pair in high_corr:
                report += f"  {pair['pair']}: {pair['correlation']:.3f}\n"
        else:
            report += "✅ 无高相关性品种对\n"
        
        # 相关性变化
        changes = self.detect_correlation_change()
        
        if changes:
            report += "\n⚠️ 相关性突变:\n"
            for change in changes:
                report += f"  {change['pair']}: {change['previous']:.3f} → {change['current']:.3f}\n"
        
        # 分散化收益
        div_benefit = self.calculate_diversification_benefit()
        report += f"\n分散化收益指数: {div_benefit:.4f}\n"
        
        # 调整建议
        suggestions = self.suggest_rebalancing()
        
        if suggestions:
            report += "\n📋 仓位调整建议:\n"
            for sugg in suggestions:
                report += f"  {sugg['action'].upper()}: {sugg['pair']} - {sugg['reason']}\n"
        
        return report


def main():
    """主函数 - 用于测试"""
    print("跨资产相关性管理器")
    print("=" * 50)
    
    # 模拟测试
    import random
    
    manager = CrossAssetCorrelationManager(None, 
        ['CU2401', 'RB2401', 'IF2401', 'AU2401', 'AG2401']
    )
    
    # 模拟价格数据
    base_prices = {'CU2401': 68000, 'RB2401': 3800, 'IF2401': 3800, 
                   'AU2401': 480, 'AG2401': 5800}
    
    for day in range(40):
        for symbol, base_price in base_prices.items():
            price = base_price * (1 + random.uniform(-0.02, 0.02))
            manager.update_prices(symbol, price)
    
    # 计算相关性
    manager.calculate_correlation_matrix()
    
    # 模拟第二次计算
    for day in range(5):
        for symbol, base_price in base_prices.items():
            price = base_price * (1 + random.uniform(-0.03, 0.03))
            manager.update_prices(symbol, price)
    
    manager.calculate_correlation_matrix()
    
    print(manager.generate_report())


if __name__ == "__main__":
    main()
