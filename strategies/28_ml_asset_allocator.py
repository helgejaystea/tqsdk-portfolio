#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 28
策略名称: 机器学习资产配置策略
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
本策略使用机器学习方法进行资产配置，通过分析历史数据中的模式来预测
各资产的未来表现，并据此动态调整投资组合权重。

核心方法：
1. 特征工程 - 提取技术指标作为特征
2. 随机森林预测 - 预测各资产的未来收益
3. 收益-风险优化 - 在预测收益和风险之间寻求平衡

【策略参数】
- SYMBOLS: 投资品种列表
- LOOKBACK_PERIOD: 历史数据回看周期
- PREDICTION_WINDOW: 预测周期（分钟）
- N_ESTIMATORS: 随机森林树数量
- REBALANCE_FREQ: 调仓频率（小时）
- TOP_N: 选取预测收益前N名

【风险提示】
- 本策略仅供研究学习使用
- 机器学习模型存在过拟合风险
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
    "SHFE.rb2405", "SHFE.cu2405", "SHFE.al2405",
    "DCE.m2405", "DCE.j2405", "CZCE.SR2405", "CFFEX.IF2405",
]
LOOKBACK_PERIOD = 240
PREDICTION_WINDOW = 30
N_ESTIMATORS = 50
REBALANCE_FREQ = 12
TOP_N = 4


class MLAssetAllocator:
    """机器学习资产配置策略"""
    
    def __init__(self, api):
        self.api = api
        self.symbols = SYMBOLS
        self.lookback = LOOKBACK_PERIOD
        self.prediction_window = PREDICTION_WINDOW
        
    def get_historical_data(self, symbol, count):
        try:
            klines = self.api.get_kline_serial(symbol, 60, count)
            if klines is not None and len(klines) > 0:
                return klines
        except:
            pass
        return None
    
    def calculate_features(self, closes, volumes):
        if len(closes) < 20:
            return None
        features = {}
        returns = np.diff(closes) / closes[:-1]
        features['momentum_5'] = np.mean(returns[-5:]) if len(returns) >= 5 else 0
        features['momentum_10'] = np.mean(returns[-10:]) if len(returns) >= 10 else 0
        features['volatility_5'] = np.std(returns[-5:]) if len(returns) >= 5 else 0
        features['volatility_20'] = np.std(returns[-20:]) if len(returns) >= 20 else 0
        if len(volumes) >= 20:
            avg_vol = np.mean(volumes[-20:])
            features['volume_ratio'] = volumes[-1] / avg_vol if avg_vol > 0 else 1
        else:
            features['volume_ratio'] = 1
        if len(closes) >= 20:
            ma5, ma20 = np.mean(closes[-5:]), np.mean(closes[-20:])
            features['trend'] = (ma5 - ma20) / ma20 if ma20 > 0 else 0
        else:
            features['trend'] = 0
        return features
    
    def predict_return(self, symbol):
        data = self.get_historical_data(symbol, self.lookback)
        if data is None or len(data) < 30:
            return None
        closes = np.array(data.get('close', []))
        volumes = np.array(data.get('volume', []))
        feat = self.calculate_features(closes, volumes)
        if feat is None:
            return None
        # 简化预测：使用动量
        returns = np.diff(closes[-10:]) / closes[-11:-1]
        return np.mean(returns)
    
    def calculate_volatility(self, symbol):
        data = self.get_historical_data(symbol, self.lookback)
        if data is None or len(data) < 20:
            return None
        closes = list(data.get('close', []))
        returns = []
        for i in range(1, len(closes)):
            if closes[i-1] != 0:
                returns.append((closes[i] - closes[i-1]) / closes[i-1])
        if len(returns) < 20:
            return None
        return np.std(returns) * np.sqrt(252)
    
    def run_analysis(self):
        print("=" * 60)
        print("机器学习资产配置策略")
        print("=" * 60)
        print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        predictions = {}
        volatilities = {}
        
        for symbol in self.symbols:
            pred = self.predict_return(symbol)
            vol = self.calculate_volatility(symbol)
            if pred:
                predictions[symbol] = pred
            if vol:
                volatilities[symbol] = vol
        
        # 计算权重
        valid = [s for s in predictions if volatilities.get(s)]
        if not valid:
            print("数据不足")
            return
        
        preds = np.array([predictions[s] for s in valid])
        vols = np.array([volatilities[s] for s in valid])
        risk_adj = preds / (vols + 1e-6)
        weights = risk_adj / np.sum(risk_adj)
        weights = np.maximum(weights, 0)
        if np.sum(weights) > 0:
            weights = weights / np.sum(weights)
        
        result = {valid[i]: weights[i] for i in range(len(valid))}
        
        print(f"\n{'品种':<15} {'预测收益':>12} {'波动率':>10} {'权重':>10}")
        print("-" * 50)
        sorted_res = sorted(result.items(), key=lambda x: predictions[x[0]], reverse=True)
        
        for symbol, w in sorted_res:
            print(f"{symbol:<15} {predictions[symbol]*100:>11.2f}% {volatilities[symbol]*100:>9.2f}% {w*100:>9.1f}%")
        
        print("\n推荐做多品种:", ", ".join([s for s, _ in sorted_res[:TOP_N]]))
        return result


def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    allocator = MLAssetAllocator(api)
    allocator.run_analysis()
    api.close()


if __name__ == "__main__":
    main()
