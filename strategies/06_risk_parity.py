#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略06 - 组合策略：风险平价组合策略
原理：
    根据各品种的波动率分配仓位，实现风险均衡。
    波动率高的品种分配较低仓位，波动率低的品种分配较高仓位。

参数：
    - 品种池：螺纹钢、热卷、焦炭
    - 目标波动率：15%
    - 调仓周期：每周

适用行情：所有行情
作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import ATR
import numpy as np

# ============ 参数配置 ============
SYMBOLS = ["SHFE.rb2505", "SHFE.hc2505", "J2505"]
KLINE_DURATION = 60 * 60 * 24   # 日K线
TARGET_VOL = 0.15               # 目标波动率15%
ATR_PERIOD = 20                 # ATR周期

# ============ 主策略 ============
def calculate_volatility(api, symbol, kline_duration):
    """计算品种波动率"""
    
    klines = api.get_kline_serial(symbol, kline_duration, data_length=ATR_PERIOD + 5)
    
    if len(klines) < ATR_PERIOD:
        return 0
        
    atr = ATR(klines, ATR_PERIOD).iloc[-1]
    current_price = klines['close'].iloc[-1]
    
    # 波动率 = ATR / 价格
    vol = atr / current_price
    
    return vol


def calculate_weights(api, symbols, target_vol):
    """计算风险平价权重"""
    
    volatilities = {}
    for symbol in symbols:
        try:
            vol = calculate_volatility(api, symbol, KLINE_DURATION)
            volatilities[symbol] = vol
        except:
            volatilities[symbol] = 0
    
    # 反波动率加权
    total_inv_vol = sum(1/v for v in volatilities.values() if v > 0)
    
    weights = {}
    for symbol, vol in volatilities.items():
        if vol > 0:
            # 权重 = (1/波动率) / 总(1/波动率) * 目标波动率/实际波动率
            raw_weight = (1 / vol) / total_inv_vol
            weights[symbol] = raw_weight * (target_vol / vol)
        else:
            weights[symbol] = 0
            
    return weights


def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：风险平价组合策略")
    
    while True:
        api.wait_update()
        
        weights = calculate_weights(api, SYMBOLS, TARGET_VOL)
        
        print("\n当前仓位权重:")
        for symbol, weight in weights.items():
            print(f"  {symbol}: {weight*100:.2f}%")
        
        # 每周更新（简化）
        import time
        time.sleep(3600 * 24 * 7)
    
    api.close()

if __name__ == "__main__":
    main()
