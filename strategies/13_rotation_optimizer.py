#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略13 - 轮动组合优化器
原理：
    根据动量指标动态调整品种权重
    定期再平衡，保持最优配置

参数：
    - 品种池：螺纹钢、热卷、焦煤、焦炭
    - 轮动周期：5日
    - 持仓周期：20日
    - 选品种数：2个

适用行情：品种轮动
作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth, TqSim, TargetPosTask
import pandas as pd
import numpy as np

# ============ 参数配置 ============
SYMBOLS = ["SHFE.rb2505", "SHFE.hc2505", "DCE.jm2505", "DCE.j2505"]  # 品种池
KLINE_DURATION = 60 * 60         # 日线
ROTATION_PERIOD = 5              # 轮动周期（天）
HOLDING_PERIOD = 20              # 持仓周期（天）
SELECT_COUNT = 2                 # 选品种数
VOLUME_PER_SYMBOL = 1           # 每品种手数


def calculate_momentum(klines, period=5):
    """计算动量指标"""
    close = klines["close"]
    momentum = (close.iloc[-1] - close.iloc[-period]) / close.iloc[-period]
    return momentum


def main():
    api = TqApi(account=TqSim(), auth=TqAuth("账号", "密码"))
    print("启动：轮动组合优化器")
    
    # 获取各品种数据
    klines_dict = {}
    for symbol in SYMBOLS:
        klines_dict[symbol] = api.get_kline_serial(symbol, KLINE_DURATION, 30)
    
    target_pos_dict = {symbol: TargetPosTask(api, symbol) for symbol in SYMBOLS}
    
    day_count = 0
    selected_symbols = []
    
    while True:
        api.wait_update()
        
        # 检查是否有K线更新
        for symbol, klines in klines_dict.items():
            if api.is_changing(klines.iloc[-1], "datetime"):
                day_count += 1
                
                # 每5天计算一次动量
                if day_count % ROTATION_PERIOD == 0:
                    print(f"\n=== 轮动信号 ({day_count}天) ===")
                    
                    # 计算各品种动量
                    momentum_dict = {}
                    for sym, kl in klines_dict.items():
                        if len(kl) >= ROTATION_PERIOD:
                            mom = calculate_momentum(kl, ROTATION_PERIOD)
                            momentum_dict[sym] = mom
                            print(f"{sym}: 动量 {mom*100:.2f}%")
                    
                    # 选取动量最强的品种
                    sorted_symbols = sorted(momentum_dict.items(), key=lambda x: x[1], reverse=True)
                    selected = [s[0] for s in sorted_symbols[:SELECT_COUNT]]
                    
                    print(f"\n选品种: {selected}")
                    
                    # 调整持仓
                    for sym in SYMBOLS:
                        if sym in selected:
                            target_pos_dict[sym].set_target_volume(VOLUME_PER_SYMBOL)
                            print(f"持有: {sym}")
                        else:
                            target_pos_dict[sym].set_target_volume(0)
                            print(f"平仓: {sym}")
                    
                    selected_symbols = selected
                
                break
    
    api.close()


if __name__ == "__main__":
    main()
