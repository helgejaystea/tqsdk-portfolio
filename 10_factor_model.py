#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略10 - 因子模型组合
原理：
    使用多因子模型分析各品种的风险暴露，
    构建因子暴露平衡的组合。

参数：
    - 因子：动量、波动率、流动性、价值
    - 标的：螺纹、铁矿、焦炭、热卷、橡胶

适用行情：因子投资
作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
SYMBOLS = ["SHFE.rb2505", "DCE.i2505", "DCE.j2505", "SHFE.hc2505", "SHFE.ru2505"]

# ============ 因子计算 ============
def calculate_factors(klines):
    """计算因子值"""
    returns = klines['close'].pct_change().dropna()
    
    # 动量因子（20日收益）
    momentum = returns.iloc[-20:].sum() if len(returns) >= 20 else 0
    
    # 波动率因子（20日标准差）
    volatility = returns.iloc[-20:].std() if len(returns) >= 20 else 0.02
    
    # 流动性因子（成交量）
    volume = klines['volume'].iloc[-1]
    
    return {
        'momentum': momentum,
        'volatility': volatility,
        'volume': volume
    }

# ============ 因子模型 ============
def factor_model_optimization(factor_exposures, factor_returns):
    """
    基于因子暴露优化组合
    factor_exposures: 品种-因子暴露矩阵
    factor_returns: 因子收益
    """
    # 预期收益 = 因子暴露 × 因子收益
    expected_returns = factor_exposures @ factor_returns
    
    return expected_returns

# ============ 主策略 ============
def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：因子模型组合优化")
    
    # 获取各品种数据
    klines_list = []
    for symbol in SYMBOLS:
        klines = api.get_kline_serial(symbol, 24*60*60, data_length=30)
        klines_list.append(klines)
    
    print("===== 因子分析 =====")
    
    # 计算各品种因子暴露
    factor_exposures = np.zeros((len(SYMBOLS), 2))  # 动量、波动率
    
    for i, klines in enumerate(klines_list):
        factors = calculate_factors(klines)
        factor_exposures[i, 0] = factors['momentum']
        factor_exposures[i, 1] = factors['volatility']
        print(f"{SYMBOLS[i]}: 动量={factors['momentum']*100:.2f}%, 波动率={factors['volatility']*100:.2f}%")
    
    # 简化因子收益假设
    factor_returns = np.array([0.02, -0.01])  # 动量收益、波动率溢价
    
    # 计算预期收益
    expected_returns = factor_exposures @ factor_returns
    
    print("\n===== 预期收益 =====")
    for i, symbol in enumerate(SYMBOLS):
        print(f"{symbol}: {expected_returns[i]*100:.2f}%")
    
    # 简单的等风险贡献加权
    inv_vol = 1 / (factor_exposures[:, 1] + 0.01)
    weights = inv_vol / np.sum(inv_vol)
    
    print("\n===== 推荐组合权重 =====")
    for i, symbol in enumerate(SYMBOLS):
        print(f"{symbol}: {weights[i]*100:.1f}%")
    
    api.close()

if __name__ == "__main__":
    main()
