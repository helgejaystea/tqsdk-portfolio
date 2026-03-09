#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略16 - 因子轮动组合
原理：
    多因子模型评估各品种吸引力
    动态轮动到最强因子暴露的品种

参数：
    - 品种池：螺纹钢、热卷、焦煤、焦炭、原油
    - 周期：日线
    - 因子：动量、波动率、趋势强度
    - 轮动周期：5天

适用行情：趋势转换
作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth, TqSim, TargetPosTask
import pandas as pd
import numpy as np

# ============ 参数配置 ============
SYMBOLS = ["SHFE.rb2505", "SHFE.hc2505", "SHFE.jm2505", "SHFE.j2505", "SC2505"]  # 品种池
KLINE_DURATION = 60 * 60 * 24     # 日线
VOLUME_PER_SYMBOL = 1             # 每品种交易手数
DATA_LENGTH = 60                  # 历史K线数量
ROTATION_PERIOD = 5                # 轮动周期（天）
MOMENTUM_PERIOD = 20               # 动量周期
VOLATILITY_PERIOD = 20             # 波动率周期
TREND_PERIOD = 60                  # 趋势周期


def calculate_momentum(close, period=20):
    """计算动量因子"""
    momentum = close.pct_change(period)
    return momentum


def calculate_volatility_factor(close, period=20):
    """计算波动率因子（低波动更优）"""
    returns = close.pct_change()
    volatility = returns.rolling(window=period).std()
    # 返回负的波动率（低波动得分高）
    return -volatility


def calculate_trend_strength(close, period=60):
    """计算趋势强度因子"""
    ma = close.rolling(window=period).mean()
    # 价格与均线的偏离度
    trend = (close - ma) / ma
    return trend


def calculate_factor_score(momentum, volatility, trend):
    """计算综合因子得分"""
    # 标准化各因子
    def normalize(series):
        return (series - series.mean()) / series.std()
    
    mom_norm = normalize(momentum)
    vol_norm = normalize(volatility)
    trend_norm = normalize(trend)
    
    # 综合得分：动量权重40%，波动率权重30%，趋势权重30%
    score = 0.4 * mom_norm + 0.3 * vol_norm + 0.3 * trend_norm
    
    return score


def main():
    api = TqApi(account=TqSim(), auth=TqAuth("账号", "密码"))
    print("启动：因子轮动组合")
    
    # 获取各品种数据
    klines_dict = {}
    for symbol in SYMBOLS:
        klines_dict[symbol] = api.get_kline_serial(symbol, KLINE_DURATION, DATA_LENGTH)
    
    target_pos_dict = {symbol: TargetPosTask(api, symbol) for symbol in SYMBOLS}
    
    print(f"品种数量: {len(SYMBOLS)}")
    print(f"轮动周期: {ROTATION_PERIOD}天")
    print(f"因子权重: 动量40%, 波动率30%, 趋势30%")
    
    day_count = 0
    current_position = None
    
    while True:
        api.wait_update()
        
        # 检查所有品种是否有新数据
        all_updated = False
        
        for symbol in SYMBOLS:
            klines = klines_dict[symbol]
            if len(klines) >= DATA_LENGTH:
                if api.is_changing(klines.iloc[-1], "datetime"):
                    all_updated = True
        
        if not all_updated:
            continue
        
        day_count += 1
        
        # 每天只做一次分析
        if day_count % ROTATION_PERIOD != 0:
            continue
        
        print(f"\n{'='*50}")
        print(f"第 {day_count} 天 - 因子轮动分析")
        print(f"{'='*50}")
        
        # 计算各品种因子得分
        factor_scores = {}
        
        for symbol in SYMBOLS:
            klines = klines_dict[symbol]
            close = klines["close"]
            
            if len(close) < max(MOMENTUM_PERIOD, VOLATILITY_PERIOD, TREND_PERIOD):
                continue
            
            # 计算各因子
            momentum = calculate_momentum(close, MOMENTUM_PERIOD).iloc[-1]
            volatility = calculate_volatility_factor(close, VOLATILITY_PERIOD).iloc[-1]
            trend = calculate_trend_strength(close, TREND_PERIOD).iloc[-1]
            
            # 计算综合得分
            score = calculate_factor_score(
                calculate_momentum(close, MOMENTUM_PERIOD).iloc[-1],
                calculate_volatility_factor(close, VOLATILITY_PERIOD).iloc[-1],
                calculate_trend_strength(close, TREND_PERIOD).iloc[-1]
            )
            
            factor_scores[symbol] = {
                "momentum": momentum,
                "volatility": volatility,
                "trend": trend,
                "score": score
            }
            
            print(f"\n{symbol}:")
            print(f"  动量: {momentum*100:+.2f}%")
            print(f"  波动率: {abs(volatility)*100:.2f}%")
            print(f"  趋势: {trend*100:+.2f}%")
            print(f"  综合得分: {score:.3f}")
        
        if not factor_scores:
            continue
        
        # 选择得分最高的品种
        best_symbol = max(factor_scores.keys(), key=lambda x: factor_scores[x]["score"])
        best_score = factor_scores[best_symbol]["score"]
        
        print(f"\n{'='*50}")
        print(f"🏆 最优品种: {best_symbol}")
        print(f"   得分: {best_score:.3f}")
        print(f"{'='*50}")
        
        # 轮动交易
        if current_position != best_symbol:
            print(f"\n🔄 执行轮动: {current_position} -> {best_symbol}")
            
            # 平掉所有仓位
            for symbol in SYMBOLS:
                target_pos_dict[symbol].set_target_volume(0)
            
            # 买入最优品种
            target_pos_dict[best_symbol].set_target_volume(VOLUME_PER_SYMBOL)
            current_position = best_symbol
            
            print(f"✅ 已切换到: {best_symbol}")
        else:
            print(f"\n📊 保持当前: {best_symbol}")
    
    api.close()


if __name__ == "__main__":
    main()
