#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略08 - 组合管理：最小方差组合策略
原理：
    最小方差组合旨在最小化组合整体波动率。
    不追求最高收益，但求最稳的组合。

参数：
    - 交易品种：RB, HC, JM, I
    - 最小权重：5%
    - 最大权重：50%

适用行情：风险厌恶型投资者
作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
SYMBOLS = ["SHFE.rb2505", "SHFE.hc2505", "DCE.jm2505", "DCE.i2505"]
MIN_WEIGHT = 0.05               # 最小权重
MAX_WEIGHT = 0.50               # 最大权重

# ============ 主策略 ============
class MinimumVariancePortfolio:
    def __init__(self, symbols):
        self.symbols = symbols
        self.returns_history = {s: [] for s in symbols}
        
    def calculate_min_variance_weights(self, returns_history):
        """计算最小方差权重"""
        if not returns_history:
            return {s: 1.0/len(self.symbols) for s in self.symbols}
        
        # 计算协方差矩阵
        returns = np.array(list(returns_history.values())).T
        cov_matrix = np.cov(returns.T)
        
        try:
            # 最小方差解析解: w = (Σ^-1 * 1) / (1' * Σ^-1 * 1)
            inv_cov = np.linalg.inv(cov_matrix)
            ones = np.ones(len(self.symbols))
            weights = inv_cov @ ones
            weights = weights / weights.sum()
        except:
            weights = np.ones(len(self.symbols)) / len(self.symbols)
        
        # 应用权重约束
        weights = np.clip(weights, MIN_WEIGHT, MAX_WEIGHT)
        weights = weights / weights.sum()
        
        return {s: w for s, w in zip(self.symbols, weights)}
    
    def get_portfolio_volatility(self, weights, returns_history):
        """计算组合波动率"""
        returns = np.array(list(returns_history.values())).T
        cov_matrix = np.cov(returns.T)
        
        portfolio_vol = np.sqrt(weights @ cov_matrix @ weights)
        return portfolio_vol


def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：最小方差组合策略")
    
    optimizer = MinimumVariancePortfolio(SYMBOLS)
    
    # 获取初始数据
    quotes = {s: api.get_quote(s) for s in SYMBOLS}
    
    print(f"交易品种: {SYMBOLS}")
    
    api.close()

if __name__ == "__main__":
    main()
