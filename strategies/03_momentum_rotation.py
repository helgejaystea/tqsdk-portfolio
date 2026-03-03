#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略03 - 动量轮动组合策略
原理：
    在多个品种间轮动，选择近期动量最强的品种：
    1. 计算多个品种的N日收益率
    2. 排序选出最强品种
    3. 持有最强品种，下一周期重新轮动

参数：
    - 候选品种列表
    - 动量周期：20天
    - 轮动周期：5天

作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth
import pandas as pd
import numpy as np

# ============ 参数配置 ============
SYMBOLS = [
    "SHFE.rb2405",   # 螺纹钢
    "SHFE.i2405",    # 铁矿石
    "SHFE.cu2405",   # 铜
    "SHFE.m2409",    # 豆粕
]
KLINE_DURATION = 60 * 60 * 24  # 日K线
MOMENTUM_PERIOD = 20          # 动量周期
ROTATION_PERIOD = 5 * 60 * 60 # 轮动周期（5小时）
LOT_SIZE = 1                   # 开仓手数

def calc_momentum(klines, period):
    """计算动量（收益率）"""
    if len(klines) < period:
        return 0
    start_price = klines[-period]['close']
    end_price = klines[-1]['close']
    return (end_price - start_price) / start_price

def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print(f"启动：动量轮动组合策略")
    print(f"候选品种: {SYMBOLS}")
    
    # 获取各品种K线
    klines_dict = {}
    for symbol in SYMBOLS:
        klines_dict[symbol] = api.get_kline_serial(symbol, KLINE_DURATION, data_length=MOMENTUM_PERIOD + 5)
    
    current_position = None
    last_rotation_time = None
    
    while True:
        # 等待更新
        for k in klines_dict.values():
            api.wait_update(k)
        
        # 计算各品种动量
        momenta = {}
        for symbol, klines in klines_dict.items():
            if len(klines) >= MOMENTUM_PERIOD:
                momenta[symbol] = calc_momentum(klines, MOMENTUM_PERIOD)
        
        if not momenta:
            continue
        
        # 选出最强动量品种
        best_symbol = max(momenta, key=momenta.get)
        
        print(f"动量排名: {', '.join([f'{k}:{v:.2%}' for k,v in sorted(momenta.items(), key=lambda x:-x[1])])}")
        print(f"最强品种: {best_symbol} (动量: {momenta[best_symbol]:.2%})")
        
        # 轮动交易
        if current_position != best_symbol:
            # 平掉原有仓位
            if current_position:
                print(f"轮动平仓: {current_position}")
                # 平仓逻辑
            
            # 开新仓位
            print(f"轮动开仓: {best_symbol}")
            # 开仓逻辑
            current_position = best_symbol
    
    api.close()

if __name__ == "__main__":
    main()
