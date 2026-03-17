#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 27
策略名称: 跨资产风险平价策略
生成日期: 2026-03-17
仓库地址: https://github.com/helgejaystea/tqsdk-portfolio
================================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【TqSdk 简介】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TqSdk（天勤量化 SDK）是由信易科技（北京）有限公司开发的专业期货量化交易框架，
完全免费开源（Apache 2.0 协议），基于 Python 语言设计，支持 Python 3.6+ 环境。

TqSdk 核心能力包括：
1. 统一行情接口 - 对接国内全部7大期货交易所
2. 高性能数据推送 - 延迟通常在5ms以内
3. 同步式编程范式 - 无需掌握异步编程
4. 完整回测引擎 - 支持Tick级回测
5. 实盘/模拟一键切换

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】
风险平价（Risk Parity）策略的核心思想是让投资组合中各资产对总风险的
贡献相等。本策略将这一理念应用于跨资产组合，通过动态调整各资产的
权重，使得每个资产对组合总风险的贡献相同。

核心优势：
1. 风险均衡 - 不依赖对收益的预测
2. 分散化 - 降低组合整体波动
3. 适应性 - 根据市场波动自动调整

【策略参数】
- SYMBOLS: 投资品种列表
- LOOKBACK_PERIOD: 波动率计算回看周期
- TARGET_VOLATILITY: 目标波动率
- REBALANCE_FREQ: 调仓频率（小时）
- MAX_WEIGHT: 单品种最大权重
- MIN_WEIGHT: 单品种最小权重

【风险提示】
- 本策略仅供研究学习使用
- 风险平价不等于风险为零
- 实际交易请做好风险控制
================================================================================
"""

from tqsdk import TqApi, TqAuth
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============ 参数配置 ============
SYMBOLS = [
    "SHFE.rb2405",   # 螺纹钢
    "SHFE.cu2405",   # 铜
    "DCE.m2405",     # 豆粕
    "DCE.j2405",     # 焦炭
    "CZCE.SR2405",   # 白糖
    "CFFEX.IF2405",  # 股指期货
]
LOOKBACK_PERIOD = 60        # 回看周期（分钟）
TARGET_VOLATILITY = 0.15   # 目标年化波动率（15%）
REBALANCE_FREQ = 24        # 调仓频率（小时）
MAX_WEIGHT = 0.40          # 单品种最大权重
MIN_WEIGHT = 0.05          # 单品种最小权重


class RiskParityStrategy:
    """跨资产风险平价策略"""
    
    def __init__(self, api):
        self.api = api
        self.symbols = SYMBOLS
        self.lookback = LOOKBACK_PERIOD
        self.target_vol = TARGET_VOLATILITY
        self.max_weight = MAX_WEIGHT
        self.min_weight = MIN_WEIGHT
        self.current_weights = None
        
    def get_historical_data(self, symbol, count):
        """获取历史K线数据"""
        try:
            klines = self.api.get_kline_serial(symbol, 60, count)
            if klines is not None and len(klines) > 0:
                return klines
        except Exception as e:
            print(f"获取 {symbol} 数据失败: {e}")
        return None
    
    def calculate_volatility(self, symbol):
        """计算单个品种的波动率"""
        data = self.get_historical_data(symbol, self.lookback)
        
        if data is None or len(data) < 20:
            return None
        
        closes = list(data.get('close', []))
        
        if len(closes) < 20:
            return None
        
        # 计算收益率
        returns = []
        for i in range(1, len(closes)):
            if closes[i-1] != 0:
                ret = (closes[i] - closes[i-1]) / closes[i-1]
                returns.append(ret)
        
        if len(returns) < 20:
            return None
        
        # 计算年化波动率
        daily_vol = np.std(returns)
        annual_vol = daily_vol * np.sqrt(252)
        
        return annual_vol
    
    def calculate_correlation_matrix(self):
        """计算品种间的相关性矩阵"""
        returns_dict = {}
        
        for symbol in self.symbols:
            data = self.get_historical_data(symbol, self.lookback)
            if data is None:
                continue
            
            closes = list(data.get('close', []))
            
            if len(closes) < 20:
                continue
            
            returns = []
            for i in range(1, len(closes)):
                if closes[i-1] != 0:
                    ret = (closes[i] - closes[i-1]) / closes[i-1]
                    returns.append(ret)
            
            if len(returns) >= 20:
                returns_dict[symbol] = returns
        
        if len(returns_dict) < 2:
            return None, []
        
        # 构建收益率矩阵
        symbols_list = list(returns_dict.keys())
        min_length = min(len(r) for r in returns_dict.values())
        
        returns_matrix = np.array([returns_dict[s][:min_length] for s in symbols_list])
        
        # 计算相关性矩阵
        corr_matrix = np.corrcoef(returns_matrix)
        
        return corr_matrix, symbols_list
    
    def calculate_risk_parity_weights(self, volatilities, correlation_matrix):
        """计算风险平价权重"""
        n = len(volatilities)
        
        if correlation_matrix is None or n < 2:
            return None
        
        # 初始化权重
        weights = np.ones(n) / n
        
        # 迭代计算风险平价权重
        max_iterations = 100
        tolerance = 1e-6
        
        for iteration in range(max_iterations):
            # 计算各资产的风险贡献
            risk_contrib = weights * (correlation_matrix.dot(weights) * volatilities ** 2)
            
            # 目标：使各资产的风险贡献相等
            # 新的权重 = 当前权重 * (平均风险贡献 / 当前风险贡献)
            target_risk = np.mean(risk_contrib)
            
            # 避免除零
            risk_contrib = np.where(risk_contrib > 1e-10, risk_contrib, 1e-10)
            
            new_weights = weights * target_risk / risk_contrib
            
            # 归一化
            new_weights = new_weights / np.sum(new_weights)
            
            # 应用权重限制
            new_weights = np.clip(new_weights, self.min_weight, self.max_weight)
            new_weights = new_weights / np.sum(new_weights)
            
            # 检查收敛
            weight_change = np.max(np.abs(new_weights - weights))
            
            weights = new_weights
            
            if weight_change < tolerance:
                break
        
        return weights
    
    def calculate_portfolio_volatility(self, weights, volatilities, correlation_matrix):
        """计算组合波动率"""
        if weights is None or volatilities is None or correlation_matrix is None:
            return None
        
        # 组合波动率 = sqrt(w' * Cov * w)
        # Cov = diag(vol) * Corr * diag(vol)
        
        vol_matrix = np.outer(volatilities, volatilities)
        covariance_matrix = vol_matrix * correlation_matrix
        
        portfolio_vol = np.sqrt(weights.dot(covariance_matrix).dot(weights))
        
        return portfolio_vol
    
    def run_analysis(self):
        """运行风险平价分析"""
        print("=" * 60)
        print("跨资产风险平价策略")
        print("=" * 60)
        print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"投资品种: {len(self.symbols)} 个")
        print(f"回看周期: {self.lookback} 分钟")
        print(f"目标波动率: {self.target_vol*100:.0f}%")
        print(f"权重范围: {self.min_weight*100:.0f}% - {self.max_weight*100:.0f}%")
        
        # 计算各品种波动率
        print(f"\n【波动率计算】")
        print("-" * 40)
        
        volatilities = {}
        for symbol in self.symbols:
            vol = self.calculate_volatility(symbol)
            if vol:
                volatilities[symbol] = vol
                print(f"  {symbol}: {vol*100:.2f}%")
        
        if len(volatilities) < 2:
            print("数据不足，无法计算风险平价")
            return
        
        # 计算相关性矩阵
        print(f"\n【相关性矩阵】")
        print("-" * 40)
        
        corr_matrix, symbols_list = self.calculate_correlation_matrix()
        
        if corr_matrix is None:
            print("数据不足，无法计算相关性")
            return
        
        print(f"  有效品种数: {len(symbols_list)}")
        
        # 显示相关性矩阵
        print("\n相关性矩阵:")
        header = "        " + " ".join([f"{s[-4:]}" for s in symbols_list])
        print(header)
        for i, symbol in enumerate(symbols_list):
            row = f"{symbol[-4:]}" + "".join([f" {corr_matrix[i][j]:.2f}" for j in range(len(symbols_list))])
            print(row)
        
        # 计算风险平价权重
        print(f"\n【风险平价权重计算】")
        print("-" * 40)
        
        vol_array = np.array([volatilities[s] for s in symbols_list])
        
        rp_weights = self.calculate_risk_parity_weights(vol_array, corr_matrix)
        
        if rp_weights is None:
            print("权重计算失败")
            return
        
        # 显示权重
        print("\n建议权重:")
        weight_data = [(symbols_list[i], rp_weights[i], volatilities[symbols_list[i]]) 
                      for i in range(len(symbols_list))]
        weight_data.sort(key=lambda x: x[1], reverse=True)
        
        print(f"{'品种':<15} {'权重':>10} {'波动率':>10} {'风险贡献':>12}")
        print("-" * 50)
        
        # 计算风险贡献
        risk_contrib = rp_weights * (corr_matrix.dot(rp_weights) * vol_array ** 2)
        total_risk = np.sum(risk_contrib)
        
        for symbol, weight, vol in weight_data:
            idx = symbols_list.index(symbol)
            rc = risk_contrib[idx] / total_risk * 100 if total_risk > 0 else 0
            print(f"{symbol:<15} {weight*100:>9.1f}% {vol*100:>9.2f}% {rc:>11.1f}%")
        
        # 计算组合波动率
        portfolio_vol = self.calculate_portfolio_volatility(rp_weights, vol_array, corr_matrix)
        
        if portfolio_vol:
            print(f"\n组合预期年化波动率: {portfolio_vol*100:.2f}%")
            
            # 调整到目标波动率
            if portfolio_vol > 0 and self.target_vol > 0:
                vol_scalar = self.target_vol / portfolio_vol
                adjusted_weights = rp_weights * vol_scalar
                # 归一化
                adjusted_weights = adjusted_weights / np.sum(adjusted_weights)
                adjusted_weights = np.clip(adjusted_weights, self.min_weight, self.max_weight)
                adjusted_weights = adjusted_weights / np.sum(adjusted_weights)
                
                print(f"\n【调整到目标波动率 {self.target_vol*100:.0f}%】")
                print(f"调整后权重:")
                for i, symbol in enumerate(symbols_list):
                    print(f"  {symbol}: {adjusted_weights[i]*100:.1f}%")
        
        # 汇总
        print("\n" + "=" * 60)
        print("策略汇总")
        print("=" * 60)
        print(f"风险平价策略旨在使各资产对组合风险的贡献相等")
        print(f"当前组合波动率: {portfolio_vol*100:.2f}%" if portfolio_vol else "N/A")
        print(f"建议调仓频率: 每 {REBALANCE_FREQ} 小时")
        
        return {
            'weights': {symbols_list[i]: rp_weights[i] for i in range(len(symbols_list))},
            'volatilities': volatilities,
            'correlation': corr_matrix,
            'portfolio_volatility': portfolio_vol
        }


def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print(f"跨资产风险平价策略启动")
    
    strategy = RiskParityStrategy(api)
    result = strategy.run_analysis()
    
    api.close()


if __name__ == "__main__":
    main()
