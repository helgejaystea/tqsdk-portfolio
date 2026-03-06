#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略14 - 跨资产相关性对冲
原理：
    多资产组合中利用相关性进行对冲
    降低组合整体风险

参数：
    - 品种池：螺纹钢、热卷、铜、铝
    - 对冲阈值：相关性 > 0.7
    - 对冲比例：50%

适用行情：风险对冲
作者：helgejaystea / tqsdk-portfolio
"""

from tqsdk import TqApi, TqAuth, TqSim, TargetPosTask
import pandas as pd
import numpy as np

# ============ 参数配置 ============
SYMBOLS = ["SHFE.rb2505", "SHFE.hc2505", "SHFE.cu2505", "SHFE.al2505"]  # 品种池
KLINE_DURATION = 60 * 60         # 日线
CORRELATION_THRESHOLD = 0.7      # 相关性阈值
HEDGE_RATIO = 0.5                # 对冲比例
VOLUME_PER_SYMBOL = 1            # 每品种手数
DATA_LENGTH = 30                 # 历史数据数量


def calculate_correlation_matrix(price_dict):
    """计算价格相关性矩阵"""
    # 构建价格DataFrame
    price_df = pd.DataFrame(price_dict)
    
    # 计算收益率
    returns = price_df.pct_change().dropna()
    
    # 计算相关性矩阵
    corr_matrix = returns.corr()
    
    return corr_matrix


def main():
    api = TqApi(account=TqSim(), auth=TqAuth("账号", "密码"))
    print("启动：跨资产相关性对冲")
    
    # 获取各品种数据
    klines_dict = {}
    for symbol in SYMBOLS:
        klines_dict[symbol] = api.get_kline_serial(symbol, KLINE_DURATION, DATA_LENGTH)
    
    target_pos_dict = {symbol: TargetPosTask(api, symbol) for symbol in SYMBOLS}
    
    # 初始建仓：等权重
    print("\n=== 初始建仓 ===")
    for symbol in SYMBOLS:
        target_pos_dict[symbol].set_target_volume(VOLUME_PER_SYMBOL)
        print(f"建仓: {symbol}")
    
    correlation_calculated = False
    hedge_pairs = []
    
    while True:
        api.wait_update()
        
        # 等待数据加载完成后计算相关性
        all_loaded = all(len(klines) >= DATA_LENGTH for klines in klines_dict.values())
        
        if all_loaded and not correlation_calculated:
            print("\n=== 计算相关性矩阵 ===")
            
            # 提取收盘价
            price_dict = {}
            for symbol, klines in klines_dict.items():
                price_dict[symbol] = klines["close"].values
            
            # 计算相关性
            corr_matrix = calculate_correlation_matrix(price_dict)
            
            print("\n相关性矩阵:")
            print(corr_matrix.round(3))
            
            # 找出高相关性的品种对
            hedge_pairs = []
            for i, sym1 in enumerate(SYMBOLS):
                for j, sym2 in enumerate(SYMBOLS):
                    if i < j:  # 避免重复
                        corr = corr_matrix.loc[sym1, sym2]
                        if abs(corr) > CORRELATION_THRESHOLD:
                            hedge_pairs.append((sym1, sym2, corr))
                            print(f"\n发现高相关性: {sym1} <-> {sym2}: {corr:.3f}")
            
            if hedge_pairs:
                print(f"\n=== 执行对冲 ===")
                for sym1, sym2, corr in hedge_pairs:
                    print(f"对冲: {sym1} 和 {sym2}")
                    # 减少其中一个品种的仓位
                    target_pos_dict[sym2].set_target_volume(int(VOLUME_PER_SYMBOL * (1 - HEDGE_RATIO)))
            
            correlation_calculated = True
    
    api.close()


if __name__ == "__main__":
    main()
