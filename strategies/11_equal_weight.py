#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略11 - 等权重投资组合
原理：
    多个品种等权重配置，定期再平衡

参数：
    - 品种列表：RB, HC, IF, IC, IM
    - 周期：日线
    - 再平衡周期：20天

适用行情：所有行情
作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth, TqSim, TargetPosTask
import numpy as np

# ============ 参数配置 ============
SYMBOLS = ["SHFE.rb2505", "SHFE.hc2505", "SHFE.if2505", "SHFE.ic2505", "SHFE.im2505"]
KLINE_DURATION = 24 * 60 * 60   # 日线
REBALANCE_PERIOD = 20           # 再平衡周期
VOLUME_PER_SYMBOL = 1           # 每个品种的手数
DATA_LENGTH = 50                # 历史K线数量


def main():
    api = TqApi(account=TqSim(), auth=TqAuth("账号", "密码"))
    print("启动：等权重投资组合策略")
    
    # 初始化各个品种的仓位
    targets = {}
    for symbol in SYMBOLS:
        targets[symbol] = TargetPosTask(api, symbol)
    
    rebalance_count = 0
    position_opened = False
    
    while True:
        api.wait_update()
        
        # 每20根K线再平衡一次
        rebalance_count += 1
        if rebalance_count >= REBALANCE_PERIOD:
            print(f"[再平衡] 第{rebalance_count}天，执行再平衡")
            
            for symbol in SYMBOLS:
                targets[symbol].set_target_volume(VOLUME_PER_SYMBOL)
            
            rebalance_count = 0
            position_opened = True
    
    api.close()


if __name__ == "__main__":
    main()
