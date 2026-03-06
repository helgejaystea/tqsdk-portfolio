#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略09 - Black-Litterman模型组合优化
原理：
    结合市场均衡收益和投资者主观观点，计算后验收益率，
    优化投资组合权重。

参数：
    - 标的列表：rb, hc, i, j, ru (螺纹, 热卷, 铁矿, 焦炭, 橡胶)
    - 风险厌恶系数：2.5
    - 观点权重：0.5

适用行情：组合优化
作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
SYMBOLS = ["SHFE.rb2505", "SHFE.hc2505", "DCE.i2505", "DCE.j2505", "SHFE.ru2505"]
RISK_AVERSION = 2.5             # 风险厌恶系数
VIEW_WEIGHT = 0.5               # 观点权重

# ============ Black-Litterman计算 ============
def black_litterman(market_caps, cov_matrix, risk_aversion, views=None, view_weights=None):
    """
    Black-Litterman模型
    market_caps: 市值/权重向量
    cov_matrix: 协方差矩阵
    risk_aversion: 风险厌恶系数
    views: 观点收益向量
    view_weights: 观点权重矩阵
    """
    # 市场均衡收益
    market_returns = risk_aversion * cov_matrix @ market_caps
    
    if views is not None:
        # 结合观点
        posterior = np.linalg.inv(np.linalg.inv(cov_matrix * VIEW_WEIGHT) + 
                                   view_weights.T @ view_weights) @ \
                    (np.linalg.inv(cov_matrix * VIEW_WEIGHT) @ market_returns + 
                     view_weights.T @ views)
        return posterior
    
    return market_returns

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：Black-Litterman模型组合优化")
    
    # 简化示例：使用等权重
    n = len(SYMBOLS)
    market_caps = np.ones(n) / n
    
    # 模拟协方差矩阵（实际应从历史数据计算）
    cov_matrix = np.array([
        [0.04, 0.02, 0.01, 0.01, 0.01],
        [0.02, 0.05, 0.01, 0.01, 0.01],
        [0.01, 0.01, 0.06, 0.02, 0.01],
        [0.01, 0.01, 0.02, 0.07, 0.01],
        [0.01, 0.01, 0.01, 0.01, 0.08]
    ])
    
    # 计算均衡收益
    equilibrium_returns = black_litterman(market_caps, cov_matrix, RISK_AVERSION)
    
    print("===== Black-Litterman优化结果 =====")
    for i, symbol in enumerate(SYMBOLS):
        print(f"{symbol}: 均衡收益 {equilibrium_returns[i]*100:.2f}%")
    
    # 最优化组合权重（简化：均值-方差优化）
    inv_cov = np.linalg.inv(cov_matrix)
    weights = inv_cov @ equilibrium_returns
    weights = weights / np.sum(weights)  # 归一化
    
    # 限制权重范围
    weights = np.clip(weights, 0.05, 0.5)
    weights = weights / np.sum(weights)
    
    print("\n===== 推荐组合权重 =====")
    for i, symbol in enumerate(SYMBOLS):
        print(f"{symbol}: {weights[i]*100:.1f}%")
    
    api.close()

if __name__ == "__main__":
    main()
