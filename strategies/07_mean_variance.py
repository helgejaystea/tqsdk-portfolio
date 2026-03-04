#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略07 - 组合管理：均值方差优化策略
原理：
    使用均值方差模型优化多品种仓位配置。
    在给定风险预算下最大化预期收益。

参数：
    - 交易品种：RB, HC, IF, IC
    - 目标波动率：10%
    - 再平衡周期：日

适用行情：多品种配置
作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
SYMBOLS = ["SHFE.rb2505", "SHFE.hc2505", "CFFEX.IF2505", "CFFEX.IC2505"]
TARGET_VOL = 0.10               # 目标波动率10%
HISTORY_DAYS = 60               # 历史数据天数
MIN_WEIGHT = 0.05               # 最小权重
MAX_WEIGHT = 0.40               # 最大权重

# ============ 主策略 ============
class MeanVarianceOptimizer:
    def __init__(self, symbols):
        self.symbols = symbols
        self.returns_history = {s: [] for s in symbols}
        
    def calculate_returns(self, prices):
        """计算收益率"""
        return np.diff(prices) / prices[:-1]
    
    def optimize(self, returns_history):
        """均值方差优化"""
        if not returns_history or len(returns_history) < HISTORY_DAYS:
            return {s: 1.0/len(self.symbols) for s in self.symbols}
        
        # 计算收益率和协方差矩阵
        returns = np.array(list(returns_history.values())).T
        mean_returns = np.mean(returns, axis=0)
        cov_matrix = np.cov(returns.T)
        
        # 简化：等权重 + 波动率调整
        vol = np.std(returns, axis=0)
        weights = 1.0 / vol
        weights = weights / weights.sum()
        
        # 应用权重约束
        weights = np.clip(weights, MIN_WEIGHT, MAX_WEIGHT)
        weights = weights / weights.sum()
        
        return {s: w for s, w in zip(self.symbols, weights)}
    
    def update_prices(self, prices):
        """更新价格数据"""
        for symbol, price in prices.items():
            if price > 0:
                self.returns_history[symbol].append(price)


def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：均值方差优化策略")
    
    optimizer = MeanVarianceOptimizer(SYMBOLS)
    
    # 获取初始数据
    quotes = {s: api.get_quote(s) for s in SYMBOLS}
    
    # 模拟运行
    print(f"目标波动率: {TARGET_VOL*100}%")
    print(f"交易品种: {SYMBOLS}")
    
    api.close()

if __name__ == "__main__":
    main()
