# tqsdk-portfolio

> 基于 **TqSdk** 的投资组合策略集合，持续更新中。

## 项目简介

本仓库专注于**投资组合策略**，涵盖配对交易、轮动策略、组合优化等方向。  
所有策略使用 [天勤量化 TqSdk](https://github.com/shinnytech/tqsdk-python) 实现，可直接对接实盘账户。

## 策略列表

| # | 策略名称 | 类型 | 文件 |
|---|---------|------|------|
| 01 | 螺纹钢-热卷配对交易 | 配对交易 | [01_rb_hc_pairs_trading.py](01_rb_hc_pairs_trading.py) |
| 02 | 风险平价组合策略 | 组合优化 | [02_risk_parity_portfolio.py](02_risk_parity_portfolio.py) |
| 03 | 动量轮动组合策略 | 动量轮动 | [03_momentum_rotation.py](03_momentum_rotation.py) |
| 04 | 跨品种对冲组合策略 | 对冲策略 | [04_cross_hedge.py](04_cross_hedge.py) |
| 05 | 均线轮动策略 | 动量轮动 | [05_ma_rotation.py](05_ma_rotation.py) |
| 06 | 风险平价优化 | 组合优化 | [06_risk_parity.py](06_risk_parity.py) |
| 07 | 均值-方差优化 | 组合优化 | [07_mean_variance.py](07_mean_variance.py) |
| 08 | 最小方差组合 | 组合优化 | [08_min_variance.py](08_min_variance.py) |
| 09 | Black-Litterman模型 | 组合优化 | [09_black_litterman.py](09_black_litterman.py) |
| 10 | 因子模型组合 | 组合优化 | [10_factor_model.py](10_factor_model.py) |
| 11 | 等权组合 | 组合优化 | [11_equal_weight.py](11_equal_weight.py) |
| 12 | 风险平价配置 | 组合优化 | [12_risk_parity.py](12_risk_parity.py) |
| 13 | 轮动优化器 | 动量轮动 | [13_rotation_optimizer.py](13_rotation_optimizer.py) |
| 14 | 相关性对冲 | 对冲策略 | [14_correlation_hedge.py](14_correlation_hedge.py) |
| 15 | 均值回归组合 | 均值回归 | [15_mean_reversion_portfolio.py](15_mean_reversion_portfolio.py) |
| 16 | 因子轮动组合 | 动量轮动 | [16_factor_rotation_portfolio.py](16_factor_rotation_portfolio.py) |
| 17 | 目标波动率优化 | 组合优化 | [17_target_volatility_optimizer.py](17_target_volatility_optimizer.py) |
| 18 | 行业轮动策略 | 动量轮动 | [18_sector_rotation_strategy.py](18_sector_rotation_strategy.py) |
| 19 | Kelly组合优化 | 组合优化 | [19_kelly_portfolio_optimizer.py](19_kelly_portfolio_optimizer.py) |
| 20 | 均值回归轮动 | 动量轮动 | [20_mean_reversion_rotation.py](20_mean_reversion_rotation.py) |
| 21 | 多因子组合策略 | 多因子 | [21_multi_factor_portfolio.py](21_multi_factor_portfolio.py) |
| 22 | 跨品种对冲 | 对冲策略 | [22_cross_instrument_hedge.py](22_cross_instrument_hedge.py) |
| 23 | 均值-方差优化器 | 组合优化 | [23_mean_variance_optimizer.py](23_mean_variance_optimizer.py) |
| 24 | 跨资产轮动策略 | 动量轮动 | [24_cross_asset_rotation.py](24_cross_asset_rotation.py) |
| 25 | 跨资产相关性管理器 | 组合监控 | [25_cross_asset_correlation_manager.py](25_cross_asset_correlation_manager.py) |
| 26 | 智能再平衡策略 | 组合优化 | [26_smart_rebalancing_strategy.py](26_smart_rebalancing_strategy.py) |
| 27 | 跨资产风险平价策略 | 组合优化 | [27_risk_parity_strategy.py](27_risk_parity_strategy.py) |
| 28 | 机器学习资产配置策略 | 机器学习 | [28_ml_asset_allocator.py](28_ml_asset_allocator.py) |

## 策略分类

### ⚖️ 组合优化
风险平价、均值-方差、最小方差、Black-Litterman、目标波动率等。

### 🔄 动量轮动
动量轮动、均线轮动、行业轮动、因子轮动、跨资产轮动等。

### 🔗 配对交易
螺纹钢-热卷配对、跨品种对冲、相关性对冲等。

### 📊 多因子
多因子组合、因子轮动等。

### 📉 均值回归
均值回归组合等。

### 🤖 机器学习
机器学习资产配置等。

## 环境要求

```bash
pip install tqsdk numpy pandas scipy
```

## 风险提示

- 本仓库仅供研究学习使用
- 过往业绩不代表未来表现
- 组合策略需注意各品种之间的相关性

---

**持续更新中，欢迎 Star ⭐ 关注**

*更新时间：2026-03-17*
