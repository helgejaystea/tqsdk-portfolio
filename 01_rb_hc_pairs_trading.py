"""
================================================================================
策略编号：01
策略名称：螺纹钢+热卷配对交易（Pairs Trading）
文件名称：01_rb_hc_pairs_trading.py
创建日期：2026-03-02
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技推出的专业量化交易开发工具包，专为国内商品期货
市场量身打造。它基于 Python 语言，提供了从行情订阅、K线获取、实盘/模拟交易下单到
账户资金管理的全套接口，极大地降低了量化策略开发的门槛。

TqSdk 的核心特性包括：
1. 全异步数据驱动：内部采用协程（asyncio）架构，行情更新触发策略逻辑，延迟极低；
2. 实时 Tick/K线：支持任意周期的 K线订阅，数据实时更新，策略可直接访问最新价格；
3. 多账户支持：可同时连接多个期货账户（实盘 / 模拟 / 回测），便于分账户管理；
4. 回测与模拟一体：同一套代码可无缝切换回测（BacktestFinished）与实盘模式；
5. 风控集成：支持持仓限制、止盈止损、追价等常见风控逻辑，且与交易所实时结算同步；
6. 丰富的合约数据库：覆盖上期所、大商所、郑商所、中金所等全部主流品种，合约信息
   自动维护，无需手动更新。

TqSdk 被广泛应用于 CTA 策略、套利策略、组合策略等场景。本策略正是基于 TqSdk 实现
跨品种配对交易（Pairs Trading）的经典应用案例。

================================================================================

【策略逻辑详解】

一、配对交易理论基础
配对交易（Pairs Trading）源自统计套利领域，核心思想是：若两个价格序列存在协整
关系（Cointegration），则它们的线性组合（价差）是平稳序列，长期均值回归。当价差
偏离均值较大时，预期其会回归，从而产生交易机会。

螺纹钢（rb）与热轧卷板（hc）同属黑色金属系列，原料相似（均为铁矿石+焦炭），
生产工艺同为长流程转炉，下游均依赖房地产与基建需求。历史上两者价差长期维持在
一定区间内，具有良好的协整关系，是国内商品期货市场最经典的配对交易组合。

二、价差计算与标准化（Z-Score）
1. 价差序列：spread = close_rb - close_hc
   （简化模型，不做协整系数估计，直接取价格差）
2. 滚动均值：mean = spread.rolling(N).mean()
3. 滚动标准差：std = spread.rolling(N).std()
4. Z-Score：z = (spread - mean) / std
   Z-Score 衡量当前价差偏离历史均值的标准差倍数，具有量纲无关性。

三、入场与平仓规则
- 入场做空价差（rb高估/hc低估）：Z-Score > +ENTRY_THRESHOLD（+1.5σ）
  → 卖空 rb 主力合约，同时买入 hc 主力合约
- 入场做多价差（rb低估/hc高估）：Z-Score < -ENTRY_THRESHOLD（-1.5σ）
  → 买入 rb 主力合约，同时卖空 hc 主力合约
- 平仓信号：Z-Score 回归至 ±EXIT_THRESHOLD（±0.3σ）以内
- 止损信号：Z-Score 超过 ±STOP_THRESHOLD（±3.0σ），强制平仓防止极端行情损失

四、仓位管理
- 每次开仓固定手数（各1手），便于回测验证
- 两腿同步开仓/平仓，确保价差头寸成立
- 同一时刻仅持有一个方向的价差头寸

五、风险提示
- 协整关系可能因市场结构变化而失效（结构性打破）
- 极端行情下两品种可能同向大幅波动，造成双腿亏损
- 实盘需考虑滑点、手续费、资金占用及保证金变动

================================================================================
"""

import time
import numpy as np
from tqsdk import TqApi, TqAuth, TqAccount
from tqsdk.ta import ATR  # 备用，本策略主要用 numpy 计算

# ─────────────────────────────────────────────
# 参数配置区
# ─────────────────────────────────────────────

# 合约代码：使用主力连续合约
SYMBOL_RB = "KQ.m@SHFE.rb"   # 螺纹钢主力连续
SYMBOL_HC = "KQ.m@SHFE.hc"   # 热轧卷板主力连续

# 策略参数
LOOKBACK = 60        # 价差滚动窗口（根/根 K 线，此处用日线）
ENTRY_THRESHOLD = 1.5  # 入场 Z-Score 阈值（±1.5σ）
EXIT_THRESHOLD = 0.3   # 平仓 Z-Score 阈值（±0.3σ）
STOP_THRESHOLD = 3.0   # 止损 Z-Score 阈值（±3.0σ）
LOTS = 1             # 每腿开仓手数

# K线周期
KLINE_DURATION = 86400  # 日线（秒）

# 账户认证（实盘时替换为真实账户，模拟盘使用 TqSim）
# auth = TqAuth("your_tq_username", "your_tq_password")
# account = TqAccount("your_broker", "your_account", "your_password")


def calc_zscore(spread_series: np.ndarray, lookback: int) -> float:
    """
    计算最新 Z-Score。

    参数
    ----
    spread_series : np.ndarray
        历史价差序列（至少包含 lookback 个有效数据）
    lookback : int
        滚动窗口长度

    返回
    ----
    float : 最新 Z-Score，若数据不足则返回 0.0
    """
    if len(spread_series) < lookback:
        return 0.0
    # 取最近 lookback 根数据
    window = spread_series[-lookback:]
    mean = np.mean(window)
    std = np.std(window, ddof=1)   # 样本标准差
    if std < 1e-9:
        return 0.0
    current_spread = spread_series[-1]
    return (current_spread - mean) / std


def log(msg: str):
    """带时间戳的日志输出"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def main():
    """
    策略主函数：螺纹钢+热卷配对交易

    运行流程：
    1. 连接 TqSdk 获取行情与账户接口
    2. 订阅 rb、hc 日线 K 线数据
    3. 每根 K 线收盘后计算价差 Z-Score
    4. 依据 Z-Score 信号执行开仓/平仓/止损操作
    5. 循环监控，直到程序退出
    """

    # ── 初始化 TqApi ──────────────────────────────────────────
    # 模拟盘运行（不需要真实账户，适合策略验证）
    api = TqApi(auth=TqAuth("sim_user", "sim_password"))
    # 实盘示例（取消注释）：
    # api = TqApi(account=account, auth=auth)

    log(f"策略启动：螺纹钢(rb) + 热卷(hc) 配对交易")
    log(f"  合约: {SYMBOL_RB} | {SYMBOL_HC}")
    log(f"  参数: lookback={LOOKBACK}, entry={ENTRY_THRESHOLD}σ, "
        f"exit={EXIT_THRESHOLD}σ, stop={STOP_THRESHOLD}σ, lots={LOTS}")

    # ── 订阅 K 线 ────────────────────────────────────────────
    klines_rb = api.get_kline_serial(SYMBOL_RB, KLINE_DURATION, data_length=LOOKBACK + 10)
    klines_hc = api.get_kline_serial(SYMBOL_HC, KLINE_DURATION, data_length=LOOKBACK + 10)

    # ── 订阅账户与持仓信息 ────────────────────────────────────
    account_info = api.get_account()
    position_rb = api.get_position(SYMBOL_RB)
    position_hc = api.get_position(SYMBOL_HC)

    # ── 策略状态变量 ──────────────────────────────────────────
    # current_side: None=无仓, "long_spread"=多价差(rb多hc空), "short_spread"=空价差(rb空hc多)
    current_side = None
    last_kline_id = -1   # 用于检测新 K 线到来

    log("等待 K 线数据就绪...")

    # ── 主事件循环 ────────────────────────────────────────────
    while True:
        api.wait_update()  # 阻塞，直到有任何数据更新

        # 只在新 K 线收盘时触发策略逻辑（id 变化 = 新 K 线确认）
        if not api.is_changing(klines_rb.iloc[-1], "id"):
            continue

        new_id = klines_rb.iloc[-1]["id"]
        if new_id == last_kline_id:
            continue
        last_kline_id = new_id

        # ── 提取收盘价序列，计算价差 ──────────────────────────
        close_rb = np.array(klines_rb["close"])
        close_hc = np.array(klines_hc["close"])

        # 确保数据长度一致
        min_len = min(len(close_rb), len(close_hc))
        if min_len < LOOKBACK:
            log(f"数据不足：当前 {min_len} 根，需要 {LOOKBACK} 根，继续等待...")
            continue

        spread = close_rb[-min_len:] - close_hc[-min_len:]   # 价差序列
        z = calc_zscore(spread, LOOKBACK)
        cur_spread = spread[-1]
        cur_rb = close_rb[-1]
        cur_hc = close_hc[-1]

        log(f"K线[{new_id}] rb={cur_rb:.0f} hc={cur_hc:.0f} "
            f"spread={cur_spread:.0f} Z-Score={z:.3f} 当前仓={current_side}")

        # ── 获取当前持仓净头寸 ────────────────────────────────
        net_rb = position_rb.pos_long - position_rb.pos_short
        net_hc = position_hc.pos_long - position_hc.pos_short

        # ── 平仓 / 止损逻辑 ───────────────────────────────────
        if current_side == "long_spread":
            # 多价差持仓：rb多 + hc空
            if abs(z) <= EXIT_THRESHOLD:
                log(f"平仓信号（Z-Score回归）：z={z:.3f}，平多价差")
                # 平 rb 多头
                api.insert_order(SYMBOL_RB, direction="SELL", offset="CLOSE", volume=LOTS)
                # 平 hc 空头
                api.insert_order(SYMBOL_HC, direction="BUY",  offset="CLOSE", volume=LOTS)
                current_side = None
            elif z < -STOP_THRESHOLD:
                log(f"止损信号：z={z:.3f} < -{STOP_THRESHOLD}，强制平多价差")
                api.insert_order(SYMBOL_RB, direction="SELL", offset="CLOSE", volume=LOTS)
                api.insert_order(SYMBOL_HC, direction="BUY",  offset="CLOSE", volume=LOTS)
                current_side = None

        elif current_side == "short_spread":
            # 空价差持仓：rb空 + hc多
            if abs(z) <= EXIT_THRESHOLD:
                log(f"平仓信号（Z-Score回归）：z={z:.3f}，平空价差")
                api.insert_order(SYMBOL_RB, direction="BUY",  offset="CLOSE", volume=LOTS)
                api.insert_order(SYMBOL_HC, direction="SELL", offset="CLOSE", volume=LOTS)
                current_side = None
            elif z > STOP_THRESHOLD:
                log(f"止损信号：z={z:.3f} > +{STOP_THRESHOLD}，强制平空价差")
                api.insert_order(SYMBOL_RB, direction="BUY",  offset="CLOSE", volume=LOTS)
                api.insert_order(SYMBOL_HC, direction="SELL", offset="CLOSE", volume=LOTS)
                current_side = None

        # ── 开仓逻辑 ──────────────────────────────────────────
        if current_side is None:
            if z > ENTRY_THRESHOLD:
                # rb 相对高估，做空价差：卖 rb，买 hc
                log(f"开仓信号：z={z:.3f} > +{ENTRY_THRESHOLD}，做空价差（卖rb+买hc）")
                api.insert_order(SYMBOL_RB, direction="SELL", offset="OPEN", volume=LOTS)
                api.insert_order(SYMBOL_HC, direction="BUY",  offset="OPEN", volume=LOTS)
                current_side = "short_spread"

            elif z < -ENTRY_THRESHOLD:
                # rb 相对低估，做多价差：买 rb，卖 hc
                log(f"开仓信号：z={z:.3f} < -{ENTRY_THRESHOLD}，做多价差（买rb+卖hc）")
                api.insert_order(SYMBOL_RB, direction="BUY",  offset="OPEN", volume=LOTS)
                api.insert_order(SYMBOL_HC, direction="SELL", offset="OPEN", volume=LOTS)
                current_side = "long_spread"

        # ── 账户状态输出 ──────────────────────────────────────
        log(f"账户净值={account_info.balance:.2f} "
            f"可用={account_info.available:.2f} "
            f"持仓盈亏={account_info.position_profit:.2f}")


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────
if __name__ == "__main__":
    """
    运行说明：
    1. 安装依赖：pip install tqsdk numpy
    2. 替换 TqAuth 中的账户信息（或使用模拟账户）
    3. 如需回测，将 TqApi 替换为带 backtest 参数的版本：
       from tqsdk import BacktestFinished
       api = TqApi(backtest=TqBacktest(start_dt=date(2024,1,1), end_dt=date(2025,1,1)), auth=...)
    4. python 01_rb_hc_pairs_trading.py
    """
    try:
        main()
    except KeyboardInterrupt:
        print("\n策略已手动停止。")
