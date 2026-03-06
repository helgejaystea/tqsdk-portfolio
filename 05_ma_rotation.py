#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略05 - 组合策略：双均线轮动策略
原理：
    在多个品种间轮动，选择短期趋势最强的品种持仓。
    每月调仓一次。

参数：
    - 品种池：螺纹钢、热卷、焦炭、焦煤
    - 短期MA：5
    - 长期MA：20
    - 持仓周期：1个月

适用行情：趋势明显的行情
作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth
from tqsdk.ta import MA
import numpy as np

# ============ 参数配置 ============
SYMBOLS = [
    "SHFE.rb2505",   # 螺纹钢
    "SHFE.hc2505",   # 热卷
    "J2505",         # 焦炭
    "J2505"          # 焦煤
]
KLINE_DURATION = 60 * 60 * 24  # 日K线
MA_SHORT = 5
MA_LONG = 20

# ============ 主策略 ============
def calculate_trend_strength(api, symbol, kline_duration):
    """计算品种趋势强度"""
    
    klines = api.get_kline_serial(symbol, kline_duration, data_length=MA_LONG + 5)
    
    if len(klines) < MA_LONG:
        return 0
        
    ma_s = MA(klines, MA_SHORT).iloc[-1]
    ma_l = MA(klines, MA_LONG).iloc[-1]
    
    # 趋势强度 = (短期MA - 长期MA) / 长期MA
    strength = (ma_s - ma_l) / ma_l
    
    return strength


def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("启动：双均线轮动策略")
    
    # 初始化K线数据
    kline_dict = {}
    for symbol in SYMBOLS:
        kline_dict[symbol] = api.get_kline_serial(symbol, KLINE_DURATION, data_length=MA_LONG + 5)
    
    current_symbol = None
    
    while True:
        api.wait_update()
        
        # 每月调仓（简化：每小时检查）
        strengths = []
        for symbol in SYMBOLS:
            try:
                strength = calculate_trend_strength(api, symbol, KLINE_DURATION)
                strengths.append((symbol, strength))
            except:
                pass
                
        if strengths:
            # 选择最强趋势的品种
            best = max(strengths, key=lambda x: x[1])
            
            if best[1] > 0:  # 只做多
                if current_symbol != best[0]:
                    current_symbol = best[0]
                    print(f"[调仓] 切换到 {current_symbol}, 趋势强度: {best[1]:.4f}")
    
    api.close()

if __name__ == "__main__":
    main()
