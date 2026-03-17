#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 17
策略名称: 目标波动率组合优化器
生成日期: 2026-03-10
仓库地址: tqsdk-portfolio
================================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【TqSdk 简介】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TqSdk（天勤量化 SDK）是由信易科技（北京）有限公司开发的专业期货量化交易框架，
完全免费开源（Apache 2.0 协议），基于 Python 语言设计，支持 Python 3.6+ 环境。
TqSdk 已服务于数万名国内期货量化投资者，是国内使用最广泛的期货量化框架之一。

TqSdk 核心能力包括：

1. **统一行情接口**：对接国内全部7大期货交易所（SHFE/DCE/CZCE/CFFEX/INE/GFEX）
   及主要期权品种，统一的 get_quote / get_kline_serial 接口，告别繁琐的协议适配；

2. **高性能数据推送**：天勤服务器行情推送延迟通常在5ms以内，Tick 级数据实时到达，
   K线自动合并，支持自定义周期（秒/分钟/小时/日/周/月）；

3. **同步式编程范式**：独特的 wait_update() + is_changing() 设计，策略代码像
   写普通Python一样自然流畅，无需掌握异步编程，大幅降低开发门槛；

4. **完整回测引擎**：内置 TqBacktest 回测模式，历史数据精确到Tick级别，
   支持滑点、手续费等真实市场参数，回测结果可信度高；

5. **实盘/模拟一键切换**：代码结构不变，仅替换 TqApi 初始化参数即可从
   模拟盘切换至实盘，极大降低策略上线风险；

6. **多账户并发**：支持同时连接多个期货账户，适合机构投资者和量化团队；

7. **活跃生态**：官方提供策略示例库、在线文档、量化社区论坛，更新维护活跃。

官网: https://www.shinnytech.com/tianqin/
文档: https://doc.shinnytech.com/tqsdk/latest/
GitHub: https://github.com/shinnytech/tqsdk-python
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

【策略背景与原理】
目标波动率组合（Target Volatility Portfolio）是一种动态调整仓位以维持目标波动率水平的策略。
当市场波动率升高时减少仓位，波动率降低时增加仓位，以实现更稳定的风险调整收益。

【策略参数】
- SYMBOLS: 投资组合合约列表
- TARGET_VOLATILITY: 目标波动率（年化）
- LOOKBACK_VOL: 波动率计算回看期
- MAX_LEVERAGE: 最大杠杆倍数
- MIN_ALLOCATION: 最小配置比例

【风险提示】
本策略仅用于投资组合管理，不构成投资建议。杠杆交易可能放大亏损。
================================================================================
"""

from tqsdk import TqApi, TqAuth
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ============ 参数配置 ============
SYMBOLS = [
    "SHFE.rb2405",  # 螺纹钢
    "SHFE.hc2405",  # 热卷
    "DCE.m2405",    # 豆粕
    "CZCE.rm2405",  # 菜粕
    "CFFEX IF2405"  # 股指期货
]
TARGET_VOLATILITY = 0.15      # 目标年化波动率 15%
LOOKBACK_VOL = 20             # 波动率计算回看20天
MAX_LEVERAGE = 3.0            # 最大杠杆3倍
MIN_ALLOCATION = 0.05          # 最小配置5%
KLINE_DURATION = 60 * 60 * 24 # 日K线


class TargetVolatilityOptimizer:
    """目标波动率组合优化器"""
    
    def __init__(self, api, symbols, target_vol):
        self.api = api
        self.symbols = symbols
        self.target_vol = target_vol
        
    def get_historical_data(self, symbol, days):
        """获取历史K线数据"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days + 30)
        
        klines = self.api.get_kline_serial(
            symbol,
            KLINE_DURATION,
            start_time=int(start_time.timestamp()),
            end_time=int(end_time.timestamp())
        )
        
        df = pd.DataFrame(klines)
        return df
    
    def calculate_volatility(self, returns):
        """计算年化波动率"""
        vol = returns.std() * np.sqrt(252)
        return vol
    
    def calculate_weights(self, volatilities):
        """基于波动率倒数计算权重"""
        # 波动率倒数权重
        inv_vol = 1 / volatilities
        weights = inv_vol / inv_vol.sum()
        
        # 应用最小权重限制
        weights = weights.clip(lower=MIN_ALLOCATION)
        weights = weights / weights.sum()
        
        return weights
    
    def calculate_leverage(self, portfolio_vol):
        """计算目标杠杆"""
        if portfolio_vol == 0:
            return 1.0
        
        leverage = self.target_vol / portfolio_vol
        leverage = min(leverage, MAX_LEVERAGE)
        
        return leverage
    
    def optimize(self):
        """执行组合优化"""
        volatilities = {}
        prices = {}
        
        # 获取每个品种的波动率和价格
        for symbol in self.symbols:
            try:
                df = self.get_historical_data(symbol, LOOKBACK_VOL + 30)
                if len(df) > LOOKBACK_VOL:
                    returns = df['close'].pct_change().dropna()
                    vol = self.calculate_volatility(returns)
                    volatilities[symbol] = vol
                
                quote = self.api.get_quote(symbol)
                prices[symbol] = quote.last_price
            except Exception as e:
                print(f"获取{symbol}数据失败: {e}")
        
        # 计算权重
        vol_series = pd.Series(volatilities)
        weights = self.calculate_weights(vol_series)
        
        # 计算组合波动率
        portfolio_vol = (weights * vol_series).sum()
        
        # 计算杠杆
        leverage = self.calculate_leverage(portfolio_vol)
        
        # 计算最终配置
        final_weights = weights * leverage
        
        return {
            "symbols": self.symbols,
            "volatilities": volatilities,
            "prices": prices,
            "weights": weights.to_dict(),
            "final_weights": final_weights.to_dict(),
            "portfolio_vol": portfolio_vol,
            "leverage": leverage,
            "target_vol": self.target_vol
        }
    
    def generate_report(self, results):
        """生成优化报告"""
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║        目标波动率组合优化报告 - {datetime.now().strftime('%Y-%m-%d')}                       ║
╠══════════════════════════════════════════════════════════════╣
║ 目标波动率: {results['target_vol']:.1%}  组合波动率: {results['portfolio_vol']:.2%}                   ║
║ 当前杠杆: {results['leverage']:.2f}x                                            ║
╠══════════════════════════════════════════════════════════════╣
║ 品种          价格       波动率    基础权重   最终权重        ║
╠══════════════════════════════════════════════════════════════╣"""
        
        for symbol in results['symbols']:
            price = results['prices'].get(symbol, 0)
            vol = results['volatilities'].get(symbol, 0)
            weight = results['weights'].get(symbol, 0)
            final = results['final_weights'].get(symbol, 0)
            
            report += f"\n║ {symbol:14s} {price:8.2f}  {vol:6.2%}   {weight:6.2%}   {final:6.2%}      ║"
        
        report += """
╚══════════════════════════════════════════════════════════════╝"""
        
        return report


def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("=" * 60)
    print("目标波动率组合优化器启动")
    print("=" * 60)
    
    optimizer = TargetVolatilityOptimizer(api, SYMBOLS, TARGET_VOLATILITY)
    
    # 执行优化
    results = optimizer.optimize()
    
    # 生成报告
    report = optimizer.generate_report(results)
    print(report)
    
    api.close()


if __name__ == "__main__":
    main()
