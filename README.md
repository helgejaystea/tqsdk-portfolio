# tqsdk-portfolio

> 基于 [TqSdk（天勤量化）](https://doc.shinnytech.com/tqsdk/latest/) 的**多品种组合 & 配对交易策略库**
>
> 方向：多品种组合 / 配对交易（协整 / 风险平价 / 组合优化）

---

## 📋 策略列表

| 编号 | 文件名 | 策略名称 | 类型 | 品种 | 逻辑摘要 | 上传日期 |
|------|--------|---------|------|------|---------|---------|
| 01 | [01_rb_hc_pairs_trading.py](./strategies/01_rb_hc_pairs_trading.py) | 螺纹钢+热卷配对交易 | Pairs Trading | rb / hc | 协整关系价差 Z-Score（±1.5σ 入场，±0.3σ 平仓） | 2026-03-02 |
| 02 | [02_risk_parity_portfolio.py](./strategies/02_risk_parity_portfolio.py) | 风险平价多品种组合 | Risk Parity | cu / rb / m | ATR 倒数权重，三品种风险均等再平衡 | 2026-03-02 |

---

## 📂 目录结构

```
tqsdk-portfolio/
├── README.md                          # 本文件
└── strategies/
    ├── 01_rb_hc_pairs_trading.py      # 螺纹钢+热卷配对交易
    └── 02_risk_parity_portfolio.py    # 风险平价多品种组合
```

---

## 🚀 快速开始

```bash
# 安装依赖
pip install tqsdk numpy

# 运行策略（以策略01为例）
python strategies/01_rb_hc_pairs_trading.py
```

---

## 📖 策略说明

### 策略01：螺纹钢+热卷配对交易（Pairs Trading）

**核心思想**：螺纹钢（rb）与热轧卷板（hc）同属黑色金属品种，原料、工艺相近，
历史上价差（spread = rb_close - hc_close）具有良好的均值回归特性。

**交易信号**：
- 计算价差的 60 日滚动 Z-Score
- Z-Score > +1.5σ → 做空价差（卖 rb + 买 hc）
- Z-Score < -1.5σ → 做多价差（买 rb + 卖 hc）
- |Z-Score| ≤ 0.3σ → 平仓
- |Z-Score| ≥ 3.0σ → 止损

---

### 策略02：风险平价多品种组合（Risk Parity Portfolio）

**核心思想**：传统等权重组合的风险集中于高波动品种；风险平价要求各品种对
组合总风险的贡献相等，即按 ATR 倒数分配仓位权重。

**覆盖品种**：铜（cu）、螺纹钢（rb）、豆粕（m）——跨金属、黑色、农产品三大类

**权重公式**：
```
w_i = (1/ATR_i) / Σ(1/ATR_j)
lots_i = floor( balance × 2% × w_i / (ATR_i × 合约乘数) )
```

**再平衡触发**：目标手数与实际手数差 ≥ 1 手时自动调仓

---

## ⚠️ 风险提示

1. 配对交易中协整关系可能因市场结构变化而失效
2. 极端行情下各品种可能同向大幅波动，双腿均亏损
3. 实盘需考虑滑点、手续费、保证金及流动性影响
4. 策略代码仅供学习研究，不构成任何投资建议
5. 建议在天勤**模拟账户**中充分验证后再接入实盘

---

## 🔧 TqSdk 资源

- 📚 官方文档：https://doc.shinnytech.com/tqsdk/latest/
- 💻 GitHub：https://github.com/shinnytech/tqsdk-python
- 🏪 天勤终端：https://www.shinnytech.com/tianqin/

---

*本仓库由量化策略机器人自动生成并维护 | Last updated: 2026-03-02*
