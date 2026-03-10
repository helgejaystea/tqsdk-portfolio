#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
策略编号: 18
策略名称: 行业轮动组合策略
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
行业轮动策略基于动量效应原理，定期评估各品种的相对强弱，将资金配置到近期表现最强的品种。
该策略假设趋势会延续一段时间强者恒强。

【策略参数】
- SYMBOLS: 候选合约列表
- LOOKBACK_PERIOD: 动量评估回看期
- TOP_N: 保留最强N个品种
- REBALANCE_FREQ: 再平衡频率（天）
- MIN_MOMENTUM: 最小动量阈值

【风险提示】
本策略仅用于投资组合管理，不构成投资建议。动量策略可能在市场反转时遭受较大亏损。
================================================================================
"""

from tqsdk import TqApi, TqAuth
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ============ 参数配置 ============
SYMBOLS = [
    "SHFE.rb2405",  # 螺纹钢 - 建材
    "SHFE.hc2405",  # 热卷 - 板材
    "DCE.m2405",    # 豆粕 - 饲料
    "CZCE.rm2405",  # 菜粕 - 饲料
    "DCE.y2405",    # 豆油 - 油脂
    "DCE.p2405",    # 棕榈油 - 油脂
    "DCE.j2405",    # 焦炭 - 黑色
    "DCE.jm2405",   # 焦煤 - 黑色
    "CFFEX IF2405", # 股指期货 - 金融
    "CFFEX T2405"   # 国债期货 - 金融
]
LOOKBACK_PERIOD = 20            # 动量评估回看20天
TOP_N = 4                       # 保留最强4个品种
REBALANCE_FREQ = 5              # 每5天再平衡
MIN_MOMENTUM = -0.10            # 最小动量阈值 -10%
KLINE_DURATION = 60 * 60 * 24  # 日K线


class SectorRotationStrategy:
    """行业轮动组合策略"""
    
    def __init__(self, api, symbols, lookback, top_n):
        self.api = api
        self.symbols = symbols
        self.lookback = lookback
        self.top_n = top_n
        
    def get_historical_data(self, symbol, days):
        """获取历史K线数据"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days + 30)
        
        try:
            klines = self.api.get_kline_serial(
                symbol,
                KLINE_DURATION,
                start_time=int(start_time.timestamp()),
                end_time=int(end_time.timestamp())
            )
            
            df = pd.DataFrame(klines)
            return df
        except Exception as e:
            print(f"获取{symbol}数据失败: {e}")
            return None
    
    def calculate_momentum(self, df):
        """计算动量指标"""
        if df is None or len(df) < self.lookback:
            return None
        
        # 计算期间收益率
        start_price = df['close'].iloc[-self.lookback]
        end_price = df['close'].iloc[-1]
        momentum = (end_price - start_price) / start_price
        
        # 计算年化收益率
        annual_return = momentum * (252 / self.lookback)
        
        # 计算波动率
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)
        
        # 计算夏普比率
        sharpe = annual_return / volatility if volatility > 0 else 0
        
        return {
            'momentum': momentum,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe': sharpe
        }
    
    def rank_symbols(self):
        """对品种进行排名"""
        results = {}
        
        for symbol in self.symbols:
            df = self.get_historical_data(symbol, self.lookback + 30)
            momentum_data = self.calculate_momentum(df)
            
            if momentum_data:
                results[symbol] = momentum_data
        
        # 按动量排序
        sorted_symbols = sorted(
            results.items(),
            key=lambda x: x[1]['momentum'],
            reverse=True
        )
        
        return sorted_symbols
    
    def select_top(self, ranked_symbols):
        """选择最强N个品种"""
        # 过滤掉动量过低的品种
        filtered = [
            (s, d) for s, d in ranked_symbols 
            if d['momentum'] >= MIN_MOMENTUM
        ]
        
        # 选择前N个
        top = filtered[:self.top_n]
        
        # 等权重配置
        if len(top) > 0:
            weight = 1.0 / len(top)
        else:
            weight = 0.0
        
        allocations = {s: weight for s, d in top}
        
        return allocations, top
    
    def generate_report(self, allocations, ranked):
        """生成策略报告"""
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║          行业轮动组合策略报告 - {datetime.now().strftime('%Y-%m-%d')}                         ║
╠══════════════════════════════════════════════════════════════╣
║ 轮动参数: 回看{self.lookback}天  选取TOP{self.top_n}个  最低动量{MIN_MOMENTUM:.1%}               ║
╠══════════════════════════════════════════════════════════════╣
║ 排名  合约           动量      年化收益   波动率    夏普比率   ║
╠══════════════════════════════════════════════════════════════╣"""
        
        for i, (symbol, data) in enumerate(ranked, 1):
            mom = data['momentum']
            ret = data['annual_return']
            vol = data['volatility']
            shr = data['sharpe']
            alloc = allocations.get(symbol, 0)
            
            marker = "✓" if symbol in allocations else " "
            
            report += f"\n║ {i:2d}. {marker} {symbol:13s} {mom:+7.2%}  {ret:+7.2%}   {vol:6.2%}   {shr:+6.3f}  ║"
        
        report += """
╠══════════════════════════════════════════════════════════════╣
║ 配置建议:                                                     ║"""
        
        for symbol, weight in allocations.items():
            report += f"\n║   {symbol:14s} → 权重: {weight:5.1%}                               ║"
        
        report += """
╚══════════════════════════════════════════════════════════════╝"""
        
        return report
    
    def run(self):
        """运行策略"""
        # 排名
        ranked = self.rank_symbols()
        
        # 选择
        allocations, top = self.select_top(ranked)
        
        # 生成报告
        report = self.generate_report(allocations, ranked)
        
        return allocations, report


def main():
    api = TqApi(auth=TqAuth("账号", "密码"))
    
    print("=" * 60)
    print("行业轮动组合策略启动")
    print("=" * 60)
    
    strategy = SectorRotationStrategy(api, SYMBOLS, LOOKBACK_PERIOD, TOP_N)
    
    # 运行策略
    allocations, report = strategy.run()
    
    # 打印报告
    print(report)
    
    api.close()


if __name__ == "__main__":
    main()
