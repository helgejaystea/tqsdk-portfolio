"""
================================================================================
策略编号：02
策略名称：风险平价多品种组合（Risk Parity Portfolio）
文件名称：02_risk_parity_portfolio.py
创建日期：2026-03-02
================================================================================

【TqSdk 简介】
TqSdk（天勤量化 SDK）是由信易科技推出的专业量化交易开发工具包，专为国内商品期货
市场量身设计，基于 Python 语言开发。作为国内最主流的期货量化框架之一，TqSdk 提供
了从行情订阅、合约信息查询、K 线/Tick 数据获取，到实盘交易、账户管理、风险控制的
全流程工具链。

TqSdk 主要技术特点：
1. 异步驱动架构：底层基于 asyncio 协程实现，策略逻辑以事件驱动方式运行，
   行情数据变更立即触发用户代码，微秒级响应延迟；
2. 统一数据模型：K 线、Tick、账户、持仓等数据均以 pandas DataFrame 或
   TqSdk 特定对象形式提供，接口一致性强；
3. 多市场覆盖：支持上期所（SHFE）、大商所（DCE）、郑商所（CZCE）、中金所（CFFEX）、
   上期能源（INE）、广期所（GFEX）全部品种；
4. 连续合约支持：通过 KQ.m@ 前缀订阅主力连续合约，省去手动换月的麻烦；
5. 回测与实盘无缝切换：回测模式（TqBacktest）与实盘/模拟模式共享同一套代码；
6. 技术指标库：内置 tqsdk.ta 模块，包括 MA、MACD、ATR、RSI、BOLL 等常用指标；
7. 完善的生态：配套天勤终端、策略广场、风险监控平台，形成完整的量化生态闭环。

TqSdk 特别适合跨品种组合策略、套利策略和 CTA 策略的开发，本策略即利用其多品种
同步订阅、ATR 计算和多腿下单能力，实现风险平价组合的自动化管理。

================================================================================

【策略逻辑详解】

一、风险平价理论基础
风险平价（Risk Parity）由桥水基金（Bridgewater）于 1996 年首创，核心思想是：
传统等权重组合虽然各品种资金占比相同，但各品种的波动率差异导致组合风险严重集中
于高波动品种。风险平价要求各品种对组合总风险的贡献相等，即"风险均等"。

二、本策略实现方式（ATR 倒数权重法）
ATR（Average True Range，平均真实波动幅度）是衡量品种短期波动率的经典指标：
    TR  = max(high - low, |high - prev_close|, |low - prev_close|)
    ATR = TR 的 N 日指数移动平均

对于风险平价组合，各品种权重与其 ATR 成反比：
    w_i = (1 / ATR_i) / Σ(1 / ATR_j)    （j = 所有品种）

这样，波动率越高的品种分配的仓位越小，波动率越低的品种分配的仓位越大，
使各品种对组合风险的贡献趋于均等。

三、品种选择
本策略选取三个流动性良好、互相相关性较低的商品期货品种：
- 铜（cu）：工业金属，受全球经济周期影响，波动较大
- 螺纹钢（rb）：建筑钢材，受国内基建/地产政策驱动
- 豆粕（m）：农产品，受全球大豆供需及天气影响

三者涵盖金属、黑色、农产品三大类，行业相关性较低，有利于分散化。

四、仓位计算与再平衡
1. 每日（或每 N 根 K 线后）计算各品种 ATR
2. 计算风险平价权重 w_i
3. 将总目标风险预算（以账户净值比例衡量）映射到各品种手数：
       lots_i = floor( 账户净值 × RISK_BUDGET × w_i / (ATR_i × 合约乘数 × 最近价格) )
4. 若实际持仓与目标持仓偏差超过 REBALANCE_THRESHOLD，执行再平衡下单

五、风险管理
- 总风险预算 RISK_BUDGET = 0.02（即账户净值 2% 分配为波动风险）
- 单品种最大手数上限：MAX_LOTS，防止极端情况下仓位过重
- 若 ATR 为零（新合约或数据异常），跳过该品种，不开仓
- 再平衡触发条件：目标手数与实际手数相差 ≥ REBALANCE_THRESHOLD（1手）

六、注意事项
- 合约乘数需根据品种实际设置（cu=5t, rb=10t, m=10t，单位：元/吨）
- 合约换月时连续合约自动切换，但需注意价格跳变对 ATR 的短期干扰
- 实盘时建议增加开收盘时间过滤，避免在集合竞价或流动性差时段下单

================================================================================
"""

import time
import math
import numpy as np
from tqsdk import TqApi, TqAuth, TqAccount
from tqsdk.ta import ATR

# ─────────────────────────────────────────────
# 参数配置区
# ─────────────────────────────────────────────

# 品种配置：(连续合约代码, 合约乘数)
INSTRUMENTS = {
    "cu": ("KQ.m@SHFE.cu", 5),    # 铜，1手=5吨，价格单位：元/吨
    "rb": ("KQ.m@SHFE.rb", 10),   # 螺纹钢，1手=10吨
    "m":  ("KQ.m@DCE.m",   10),   # 豆粕，1手=10吨
}

# 策略参数
ATR_PERIOD = 14          # ATR 计算周期（日线，14根）
RISK_BUDGET = 0.02       # 总风险预算（账户净值的 2%）
MAX_LOTS = 10            # 单品种最大持仓手数
REBALANCE_THRESHOLD = 1  # 再平衡触发阈值（手数差 ≥ 1 触发）
KLINE_DURATION = 86400   # K线周期：日线
KLINE_DATA_LEN = ATR_PERIOD + 20  # 订阅数据长度，留出足够缓冲

# 账户认证（模拟盘，实盘时替换）
# auth = TqAuth("your_tq_username", "your_tq_password")
# account = TqAccount("your_broker", "your_account", "your_password")


def log(msg: str):
    """带时间戳的日志输出"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def compute_risk_parity_weights(atr_values: dict) -> dict:
    """
    根据各品种 ATR 计算风险平价权重（ATR 倒数归一化）。

    参数
    ----
    atr_values : dict
        {品种代码: 最新ATR值} ，ATR 为 0 的品种将被排除

    返回
    ----
    dict : {品种代码: 权重}，权重之和为 1.0
    """
    valid = {k: v for k, v in atr_values.items() if v > 1e-9}
    if not valid:
        return {}

    inv_atr = {k: 1.0 / v for k, v in valid.items()}
    total_inv = sum(inv_atr.values())
    weights = {k: inv_atr[k] / total_inv for k in inv_atr}

    # 未出现在 valid 中的品种权重为 0
    for k in atr_values:
        if k not in weights:
            weights[k] = 0.0

    return weights


def compute_target_lots(weights: dict, atr_values: dict,
                        account_balance: float,
                        close_prices: dict) -> dict:
    """
    计算各品种目标持仓手数。

    公式：
        lots_i = floor( balance × RISK_BUDGET × w_i
                        / (ATR_i × multiplier_i × close_i) )

    参数
    ----
    weights       : dict  {品种代码: 权重}
    atr_values    : dict  {品种代码: ATR}
    account_balance: float 账户净值
    close_prices  : dict  {品种代码: 最新收盘价}

    返回
    ----
    dict : {品种代码: 目标手数（整数）}
    """
    target_lots = {}
    for sym, (contract, multiplier) in INSTRUMENTS.items():
        w = weights.get(sym, 0.0)
        atr = atr_values.get(sym, 0.0)
        close = close_prices.get(sym, 0.0)

        if w < 1e-9 or atr < 1e-9 or close < 1e-9:
            target_lots[sym] = 0
            continue

        # 目标风险分配额 = 账户净值 × 总风险预算 × 品种权重
        risk_alloc = account_balance * RISK_BUDGET * w
        # 单手风险 = ATR × 合约乘数（忽略价格，ATR 已是绝对价格单位）
        lot_risk = atr * multiplier
        lots = math.floor(risk_alloc / lot_risk)
        lots = min(lots, MAX_LOTS)  # 上限保护
        lots = max(lots, 0)
        target_lots[sym] = lots

    return target_lots


def adjust_position(api, symbol: str, contract: str,
                    target: int, current: int):
    """
    调整单品种持仓至目标手数。

    参数
    ----
    api      : TqApi 实例
    symbol   : 品种代码（如 'cu'）
    contract : 连续合约代码（如 'KQ.m@SHFE.cu'）
    target   : 目标手数（多头净仓，空头为负）
    current  : 当前净仓（多头为正，空头为负）
    """
    diff = target - current
    if diff == 0:
        return

    if diff > 0:
        # 需要增加多头（或减少空头）
        log(f"  [{symbol}] 增加多仓 {diff} 手 → 开多/平空")
        api.insert_order(contract, direction="BUY", offset="OPEN", volume=diff)
    else:
        # 需要减少多头（或增加空头）
        reduce = abs(diff)
        log(f"  [{symbol}] 减少多仓 {reduce} 手 → 平多/开空")
        # 简化：先平多仓
        api.insert_order(contract, direction="SELL", offset="CLOSE", volume=reduce)


def main():
    """
    策略主函数：风险平价多品种组合

    运行流程：
    1. 初始化 TqApi，订阅各品种 K 线数据
    2. 每根新日 K 线收盘后触发再平衡检查
    3. 计算各品种 ATR → 风险平价权重 → 目标手数
    4. 对比实际持仓，差异超过阈值则下单调整
    5. 持续运行，等待下一根 K 线
    """

    # ── 初始化 TqApi（模拟盘）────────────────────────────────
    api = TqApi(auth=TqAuth("sim_user", "sim_password"))
    # 实盘示例：
    # api = TqApi(account=account, auth=auth)

    log("策略启动：风险平价多品种组合（cu + rb + m）")
    log(f"  参数: ATR周期={ATR_PERIOD}, 风险预算={RISK_BUDGET*100:.1f}%, "
        f"最大手数={MAX_LOTS}, 再平衡阈值={REBALANCE_THRESHOLD}手")

    # ── 订阅 K 线数据 ─────────────────────────────────────────
    klines = {}
    for sym, (contract, multiplier) in INSTRUMENTS.items():
        klines[sym] = api.get_kline_serial(contract, KLINE_DURATION,
                                           data_length=KLINE_DATA_LEN)
        log(f"  已订阅 {sym} 日线K线 ({contract})")

    # ── 订阅账户与持仓 ────────────────────────────────────────
    account_info = api.get_account()
    positions = {}
    for sym, (contract, multiplier) in INSTRUMENTS.items():
        positions[sym] = api.get_position(contract)

    last_kline_id = -1
    log("初始化完成，等待日线 K 线更新...")

    # ── 主事件循环 ─────────────────────────────────────────────
    while True:
        api.wait_update()

        # 以 cu 的 K 线 id 变化作为触发基准
        if not api.is_changing(klines["cu"].iloc[-1], "id"):
            continue
        new_id = klines["cu"].iloc[-1]["id"]
        if new_id == last_kline_id:
            continue
        last_kline_id = new_id

        log(f"=== 新 K 线触发再平衡检查 [id={new_id}] ===")

        # ── 计算各品种 ATR ────────────────────────────────────
        atr_values = {}
        close_prices = {}
        for sym, (contract, multiplier) in INSTRUMENTS.items():
            df = klines[sym]
            if len(df) < ATR_PERIOD + 2:
                log(f"  [{sym}] 数据不足 ({len(df)} 根)，跳过")
                atr_values[sym] = 0.0
                close_prices[sym] = 0.0
                continue

            # 使用 tqsdk.ta.ATR 计算，返回 DataFrame
            atr_df = ATR(df, ATR_PERIOD)
            latest_atr = float(atr_df["atr"].iloc[-1])
            latest_close = float(df["close"].iloc[-1])
            atr_values[sym] = latest_atr
            close_prices[sym] = latest_close
            log(f"  [{sym}] close={latest_close:.2f} ATR({ATR_PERIOD})={latest_atr:.2f}")

        # ── 风险平价权重计算 ──────────────────────────────────
        weights = compute_risk_parity_weights(atr_values)
        if not weights:
            log("  警告：所有品种 ATR 为零，本轮跳过再平衡")
            continue

        log(f"  风险平价权重: " +
            " | ".join(f"{sym}={w*100:.1f}%" for sym, w in weights.items()))

        # ── 目标手数计算 ──────────────────────────────────────
        balance = account_info.balance
        if balance < 1:
            log(f"  账户净值异常：{balance}，跳过")
            continue

        target_lots = compute_target_lots(weights, atr_values, balance, close_prices)
        log(f"  账户净值={balance:.2f}，目标手数: " +
            " | ".join(f"{sym}={lots}手" for sym, lots in target_lots.items()))

        # ── 对比实际持仓，执行再平衡 ──────────────────────────
        for sym, (contract, multiplier) in INSTRUMENTS.items():
            pos = positions[sym]
            current_net = pos.pos_long - pos.pos_short  # 当前净多头仓
            target = target_lots.get(sym, 0)
            diff = abs(target - current_net)

            log(f"  [{sym}] 当前净仓={current_net}手, 目标={target}手, 差={diff}手")

            if diff >= REBALANCE_THRESHOLD:
                log(f"  [{sym}] 触发再平衡（差值 {diff} ≥ {REBALANCE_THRESHOLD}）")
                adjust_position(api, sym, contract, target, current_net)
            else:
                log(f"  [{sym}] 无需调仓（差值 {diff} < {REBALANCE_THRESHOLD}）")

        # ── 输出组合整体风险统计 ──────────────────────────────
        total_position_profit = account_info.position_profit
        total_close_profit = account_info.close_profit
        log(f"  组合持仓盈亏={total_position_profit:.2f} "
            f"已实现盈亏={total_close_profit:.2f} "
            f"可用资金={account_info.available:.2f}")
        log("=" * 60)


# ─────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────
if __name__ == "__main__":
    """
    运行说明：
    1. 安装依赖：pip install tqsdk numpy
    2. 替换 TqAuth 中的账户信息（或使用天勤模拟账户）
    3. 如需回测：
       from tqsdk import TqBacktest
       from datetime import date
       api = TqApi(backtest=TqBacktest(
                       start_dt=date(2024,1,1),
                       end_dt=date(2025,1,1)
                   ), auth=...)
    4. python 02_risk_parity_portfolio.py

    说明：
    - 当前策略简化为纯多头风险平价，仅做多操作
    - 实际风险平价组合可包含空头对冲，需根据账户类型选择
    - 建议在天勤模拟账户中充分验证后再接入实盘
    """
    try:
        main()
    except KeyboardInterrupt:
        print("\n策略已手动停止。")
