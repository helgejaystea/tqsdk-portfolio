#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略12 - 风险平价组合
原理：
    各品种风险贡献相等，实现组合整体风险最小化

参数：
    - 品种列表：RB, HC, IF
    - 周期：日线
    - 目标波动率：15%

适用行情：所有行情
作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth, TqSim, TargetPosTask
import numpy as np
import pandas as pd

# ============ 参数配置 ============
SYMBOLS = ["SHFE.rb2505", "SHFE.hc2505", "SHFE.if2505"]
KLINE_DURATION = 24 * 60 * 60   # 日线
TARGET_VOL = 0.15               # 目标波动率
VOLUME_PER_SYMBOL = 1           # 每个品种的基础手数
DATA_LENGTH = 60                # 历史K线数量


def calc_volatility(returns):
    """计算波动率"""
    return np.std(returns) * np.sqrt(252)


def main():
    api = TqApi(account=TqSim(), auth=TqAuth("账号", "密码"))
    print("启动：风险平价组合策略")
    
    klines_dict = {}
    targets = {}
    for symbol in SYMBOLS:
        klines_dict[symbol] = api.get_kline_serial(symbol, KLINE_DURATION, DATA_LENGTH)
        targets[symbol] = TargetPosTask(api, symbol)
    
    count = 0
    
    while True:
        api.wait_update()
        
        # 获取所有品种的最新价格
        if api.is_changing(klines_dict[SYMBOLS[0]].iloc[-1], "datetime"):
            count += 1
            
            if count < 20:
                continue
            
            # 计算各品种波动率
            vols = {}
            for symbol in SYMBOLS:
                close = klines_dict[symbol]["close"]
                returns = close.pct_change().dropna()
                if len(returns) > 10:
                    vols[symbol] = calc_volatility(returns)
            
            if len(vols) < 2:
                continue
            
            # 风险平价权重（波动率倒数）
            total_inv_vol = sum(1/v for v in vols.values())
            
            print("风险平价权重:")
            for symbol in SYMBOLS:
                weight = (1/vols[symbol]) / total_inv_vol
                vol_adjust = TARGET_VOL / vols[symbol]
                adjusted_vol = weight * vol_adjust
                target_vol = int(adjusted_vol * VOLUME_PER_SYMBOL)
                print(f"  {symbol}: 权重={weight:.2%}, 调整手数={target_vol}")
                targets[symbol].set_target_volume(target_vol)
            
            count = 0
    
    api.close()


if __name__ == "__main__":
    main()
