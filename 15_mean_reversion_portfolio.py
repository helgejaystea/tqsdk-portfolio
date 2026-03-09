#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略15 - 均值回归组合
原理：
    多品种均值回归策略
    当价格偏离均值时反向交易

参数：
    - 品种池：螺纹钢、热卷、焦煤、焦炭
    - 周期：30分钟
    - 回归周期：20
    - 仓位：每品种1手

适用行情：震荡行情
作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth, TqSim, TargetPosTask
import pandas as pd
import numpy as np

# ============ 参数配置 ============
SYMBOLS = ["SHFE.rb2505", "SHFE.hc2505", "SHFE.jm2505", "SHFE.j2505"]  # 品种池
KLINE_DURATION = 30 * 60         # 30分钟K线
VOLUME_PER_SYMBOL = 1             # 每品种交易手数
DATA_LENGTH = 50                  # 历史K线数量
MEAN_PERIOD = 20                  # 回归周期
ENTRY_THRESHOLD = 1.5             # 入场阈值（标准差）
EXIT_THRESHOLD = 0.5              # 出场阈值（标准差）


def calculate_bollinger_bands(close, period=20, std_multi=2):
    """计算布林带"""
    ma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    
    upper = ma + std * std_multi
    lower = ma - std * std_multi
    
    return ma, upper, lower


def calculate_z_score(close, period=20):
    """计算Z分数"""
    ma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    
    z_score = (close - ma) / std
    
    return z_score


def main():
    api = TqApi(account=TqSim(), auth=TqAuth("账号", "密码"))
    print("启动：均值回归组合")
    
    # 获取各品种数据
    klines_dict = {}
    for symbol in SYMBOLS:
        klines_dict[symbol] = api.get_kline_serial(symbol, KLINE_DURATION, DATA_LENGTH)
    
    target_pos_dict = {symbol: TargetPosTask(api, symbol) for symbol in SYMBOLS}
    
    print(f"品种数量: {len(SYMBOLS)}")
    print(f"回归周期: {MEAN_PERIOD}")
    print(f"入场阈值: {ENTRY_THRESHOLD}σ")
    print(f"出场阈值: {EXIT_THRESHOLD}σ")
    
    # 记录每个品种的状态
    positions = {symbol: 0 for symbol in SYMBOLS}
    entry_prices = {symbol: None for symbol in SYMBOLS}
    
    while True:
        api.wait_update()
        
        # 检查每个品种
        for symbol in SYMBOLS:
            klines = klines_dict[symbol]
            
            if len(klines) < MEAN_PERIOD + 5:
                continue
            
            if api.is_changing(klines.iloc[-1], "datetime"):
                close = klines["close"]
                current_price = close.iloc[-1]
                
                # 计算Z分数
                z_score = calculate_z_score(close, MEAN_PERIOD).iloc[-1]
                
                # 计算布林带
                ma, upper, lower = calculate_bollinger_bands(close, MEAN_PERIOD)
                
                print(f"\n=== {symbol} 均值回归分析 ===")
                print(f"价格: {current_price:.2f}")
                print(f"均线: {ma.iloc[-1]:.2f}")
                print(f"Z分数: {z_score:.3f}")
                print(f"布林上轨: {upper.iloc[-1]:.2f}")
                print(f"布林下轨: {lower.iloc[-1]:.2f}")
                
                # 交易信号
                position = positions[symbol]
                
                # 做多信号：价格跌破下轨
                if z_score < -ENTRY_THRESHOLD and position == 0:
                    print(f"\n📈 信号: 买入 - 价格跌破下轨")
                    target_pos_dict[symbol].set_target_volume(VOLUME_PER_SYMBOL)
                    positions[symbol] = VOLUME_PER_SYMBOL
                    entry_prices[symbol] = current_price
                
                # 做空信号：价格突破上轨
                elif z_score > ENTRY_THRESHOLD and position == 0:
                    print(f"\n📉 信号: 做空 - 价格突破上轨")
                    target_pos_dict[symbol].set_target_volume(-VOLUME_PER_SYMBOL)
                    positions[symbol] = -VOLUME_PER_SYMBOL
                    entry_prices[symbol] = current_price
                
                # 多头出场：Z分数回归到0附近
                elif position > 0 and abs(z_score) < EXIT_THRESHOLD:
                    print(f"\n✅ 出场: 多头平仓 - 回归均衡")
                    target_pos_dict[symbol].set_target_volume(0)
                    positions[symbol] = 0
                    entry_prices[symbol] = None
                
                # 空头出场
                elif position < 0 and abs(z_score) < EXIT_THRESHOLD:
                    print(f"\n✅ 出场: 空头平仓 - 回归均衡")
                    target_pos_dict[symbol].set_target_volume(0)
                    positions[symbol] = 0
                    entry_prices[symbol] = None
                
                # 状态显示
                if positions[symbol] > 0:
                    pnl = (current_price - entry_prices[symbol]) / entry_prices[symbol] * 100
                    print(f"持仓: 多头 @ {entry_prices[symbol]:.2f}, PnL: {pnl:+.2f}%")
                elif positions[symbol] < 0:
                    pnl = (entry_prices[symbol] - current_price) / entry_prices[symbol] * 100
                    print(f"持仓: 空头 @ {entry_prices[symbol]:.2f}, PnL: {pnl:+.2f}%")
                else:
                    print("状态: 空仓")
    
    api.close()


if __name__ == "__main__":
    main()
