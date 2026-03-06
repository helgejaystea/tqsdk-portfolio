#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略04 - 跨品种对冲组合策略
原理：
    利用相关性较高的品种进行对冲：
    1. 选择相关性高的品种对（如螺纹钢/热卷）
    2. 根据价格偏离历史价差比例开仓
    3. 价差回归时平仓获利

参数：
    - 品种对：螺纹钢-热卷
    - 价差周期：60天
    - 开仓阈值：2倍标准差

作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth
import numpy as np

# ============ 参数配置 ============
SYMBOL_A = "SHFE.rb2405"     # 螺纹钢
SYMBOL_B = "HC2405"          # 热卷
KLINE_DURATION = 60 * 60 * 24  # 日K线
WINDOW = 60                   # 价差窗口
STD_THRESHOLD = 2.0          # 开仓标准差倍数
LOT_A = 1                     # 螺纹钢手数
LOT_B = 1                     # 热卷手数

def calc_spread_ratio(a_prices, b_prices):
    """计算价格比例序列"""
    return [a / b for a, b in zip(a_prices[-WINDOW:], b_prices[-WINDOW:])]

def calc_zscore(series):
    """计算Z分数"""
    mean = np.mean(series)
    std = np.std(series)
    if std == 0:
        return 0
    return (series[-1] - mean) / std

def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print(f"启动：跨品种对冲组合策略")
    print(f"品种对: {SYMBOL_A} vs {SYMBOL_B}")
    
    klines_a = api.get_kline_serial(SYMBOL_A, KLINE_DURATION, data_length=WINDOW + 1)
    klines_b = api.get_kline_serial(SYMBOL_B, KLINE_DURATION, data_length=WINDOW + 1)
    
    position = 0  # 1: 多A空B, -1: 空A多B, 0: 空仓
    
    while True:
        api.wait_update()
        
        if len(klines_a) < WINDOW or len(klines_b) < WINDOW:
            continue
        
        # 计算价差比例
        a_prices = [k['close'] for k in klines_a[-WINDOW:]]
        b_prices = [k['close'] for k in klines_b[-WINDOW:]]
        
        ratios = [a/b for a, b in zip(a_prices, b_prices)]
        zscore = calc_zscore(ratios)
        
        current_ratio = ratios[-1]
        
        print(f"价差比例: {current_ratio:.4f}, Z: {zscore:.2f}")
        
        # 交易信号
        if position == 0:
            # Z分数过低：螺纹钢相对便宜
            if zscore < -STD_THRESHOLD:
                print(f"做多价差: 多{SYMBOL_A}空{SYMBOL_B}")
                api.insert_order(symbol=SYMBOL_A, direction="long", offset="open", volume=LOT_A)
                api.insert_order(symbol=SYMBOL_B, direction="short", offset="open", volume=LOT_B)
                position = 1
            
            # Z分数过高：螺纹钢相对昂贵
            elif zscore > STD_THRESHOLD:
                print(f"做空价差: 空{SYMBOL_A}多{SYMBOL_B}")
                api.insert_order(symbol=SYMBOL_A, direction="short", offset="open", volume=LOT_A)
                api.insert_order(symbol=SYMBOL_B, direction="long", offset="open", volume=LOT_B)
                position = -1
        
        elif position == 1:
            # 价差回归
            if zscore > -0.3:
                print(f"平仓: 价差回归")
                api.insert_order(symbol=SYMBOL_A, direction="short", offset="close", volume=LOT_A)
                api.insert_order(symbol=SYMBOL_B, direction="long", offset="close", volume=LOT_B)
                position = 0
        
        elif position == -1:
            if zscore < 0.3:
                print(f"平仓: 价差回归")
                api.insert_order(symbol=SYMBOL_A, direction="long", offset="close", volume=LOT_A)
                api.insert_order(symbol=SYMBOL_B, direction="short", offset="close", volume=LOT_B)
                position = 0
    
    api.close()

if __name__ == "__main__":
    main()
