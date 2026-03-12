# tqsdk-portfolio

> 基于 **TqSdk** 的投资组合策略集合，持续更新中。

## 项目简介

本仓库专注于**投资组合策略**，涵盖配对交易、轮动策略、组合优化等方向。  
所有策略使用 [天勤量化 TqSdk](https://github.com/shinnytech/tqsdk-python) 实现，可直接对接实盘账户。

## 策略列表

| # | 策略名称 | 类型 | 品种 | 文件 |
|---|---------|------|------|------|
| 01 | 螺纹热卷配对交易 | 配对交易 | SHFE.rb/hc | [01_rb_hc_pairs_trading.py](strategies/01_rb_hc_pairs_trading.py) |
| 02 | 风险平价组合策略 | 组合优化 | 多品种 | [02_risk_parity_portfolio.py](strategies/02_risk_parity_portfolio.py) |
| 03 | 动量轮动策略 | 轮动策略 | 多品种 | [03_momentum_rotation.py](strategies/03_momentum_rotation.py) |
| 04 | 跨品种对冲策略 | 对冲策略 | 多品种 | [04_cross_hedge.py](strategies/04_cross_hedge.py) |
| 05 | 均线轮动策略 | 轮动策略 | 多品种 | [05_ma_rotation.py](strategies/05_ma_rotation.py) |
| 06 | 风险平价策略 | 组合优化 | 多品种 | [06_risk_parity.py](strategies/06_risk_parity.py) |
| 07 | 均值方差优化策略 | 组合优化 | 多品种 | [07_mean_variance.py](strategies/07_mean_variance.py) |
| 08 | 最小方差组合策略 | 组合优化 | 多品种 | [08_min_variance.py](strategies/08_min_variance.py) |
| 09 | Black-Litterman策略 | 组合优化 | 多品种 | [09_black_litterman.py](strategies/09_black_litterman.py) |
| 10 | 多因子模型策略 | 多因子 | 多品种 | [10_factor_model.py](strategies/10_factor_model.py) |
| 11 | 等权重组合策略 | 组合优化 | 多品种 | [11_equal_weight.py](strategies/11_equal_weight.py) |
| 12 | 风险预算组合策略 | 组合优化 | 多品种 | [12_risk_parity.py](strategies/12_risk_parity.py) |
| 13 | 轮动优化策略 | 轮动策略 | 多品种 | [13_rotation_optimizer.py](strategies/13_rotation_optimizer.py) |
| 14 | 相关性对冲策略 | 对冲策略 | 多品种 | [14_correlation_hedge.py](strategies/14_correlation_hedge.py) |
| 15 | 均值回归组合 | 组合策略 | 多品种 | [15_mean_reversion_portfolio.py](strategies/15_mean_reversion_portfolio.py) |
| 16 | 因子轮动组合 | 轮动策略 | 多品种 | [16_factor_rotation_portfolio.py](strategies/16_factor_rotation_portfolio.py) |
| 17 | 目标波动率优化 | 组合优化 | 多品种 | [17_target_volatility_optimizer.py](strategies/17_target_volatility_optimizer.py) |
| 18 | 行业轮动策略 | 轮动策略 | 多品种 | [18_sector_rotation_strategy.py](strategies/18_sector_rotation_strategy.py) |
| 19 | Kelly组合优化 | 组合优化 | 多品种 | [19_kelly_portfolio_optimizer.py](strategies/19_kelly_portfolio_optimizer.py) |
| 20 | 均值回归轮动 | 轮动策略 | 多品种 | [20_mean_reversion_rotation.py](strategies/20_mean_reversion_rotation.py) |
| 21 | 多因子组合策略 | 多因子 | 多品种 | [21_multi_factor_portfolio.py](strategies/21_multi_factor_portfolio.py) |
| 22 | 跨品种对冲策略 | 对冲策略 | 多品种 | [22_cross_instrument_hedge.py](strategies/22_cross_instrument_hedge.py) |

## 策略分类

### 🔄 配对交易（Pairs Trading）
基于相关品种的价差进行交易。

### 📊 轮动策略（Rotation Strategy）
基于动量、均线等指标进行品种轮动。

### ⚖️ 组合优化（Portfolio Optimization）
风险平价、均值方差、最小方差等优化方法。

### 🛡️ 对冲策略（Hedging）
跨品种对冲、相关性对冲等。

### 📈 多因子（Multi-Factor）
基于因子模型的投资组合策略。

## 环境要求

```bash
pip install tqsdk numpy pandas scipy cvxpy
```

## 风险提示

- 组合策略需注意各品种之间的相关性
- 杠杆使用需谨慎
- 本仓库策略仅供学习研究，不构成投资建议

---

**持续更新中，欢迎 Star ⭐ 关注**

*更新时间：2026-03-12*
