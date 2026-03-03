# tqsdk-portfolio

> 基于 **TqSdk** 的多品种组合策略，持续更新中。

## 项目简介

本仓库专注于**组合量化策略**，涵盖协整配对交易、组合优化、动量轮动等领域。  
所有策略使用 [天勤量化 TqSdk](https://github.com/shinnytech/tqsdk-python) 实现。

## 策略列表

| # | 策略名称 | 类型 | 品种 | 文件 |
|---|---------|------|------|------|
| 01 | 螺纹钢-热卷配对交易 | 配对交易 | SHFE.rb + HC | [01_rb_hc_pairs_trading.py](strategies/01_rb_hc_pairs_trading.py) |
| 02 | 风险平价组合策略 | 组合优化 | 多品种 | [02_risk_parity_portfolio.py](strategies/02_risk_parity_portfolio.py) |
| 03 | 动量轮动组合策略 | 动量轮动 | 多品种 | [03_momentum_rotation.py](strategies/03_momentum_rotation.py) |
| 04 | 跨品种对冲组合策略 | 对冲策略 | 多品种 | [04_cross_hedge.py](strategies/04_cross_hedge.py) |

## 更新日志

- 2026-03-03: 新增策略03（动量轮动）、策略04（跨品种对冲）
