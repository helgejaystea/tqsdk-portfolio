#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略编号: 26
策略名称: 智能再平衡策略
生成日期: 2026-03-16
仓库地址: tqsdk-portfolio

【策略背景与原理】
智能再平衡策略根据市场状态动态决定是否执行再平衡操作。
只在偏离阈值超过设定值且趋势稳定时才触发再平衡，减少不必要的交易成本。

【策略参数】
- REBALANCE_THRESHOLD: 再平衡阈值
- LOOKBACK_PERIOD: 回溯期
- MIN_HOLDING_PERIOD: 最小持有期
"""

from tqsdk import TqApi, TqAuth
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict

REBALANCE_THRESHOLD = 0.15
LOOKBACK_PERIOD = 20
MIN_HOLDING_PERIOD = 5
MAX_TURNOVER = 0.5
RISK_PARITY_ENABLED = True


class SmartRebalancingStrategy:
    """智能再平衡策略"""
    
    def __init__(self, api, target_weights=None):
        self.api = api
        self.target_weights = target_weights or {}
        self.current_weights = {}
        self.positions = {}
        self.last_rebalance = None
        self.rebalance_history = []
        self.lookback_prices = defaultdict(list)
        
    def update_position(self, symbol, volume, avg_price):
        """更新持仓"""
        self.positions[symbol] = {
            'volume': volume,
            'avg_price': avg_price,
            'update_time': datetime.now()
        }
        
    def calculate_current_weights(self, total_value):
        """计算当前权重"""
        if not self.positions:
            return {}
        
        current_weights = {}
        
        for symbol, pos in self.positions.items():
            if pos.get('volume', 0) > 0:
                try:
                    quote = self.api.get_quote(symbol)
                    current_price = quote.get('last_price', 0)
                    if current_price > 0:
                        position_value = pos['volume'] * current_price
                        current_weights[symbol] = position_value / total_value
                except:
                    if pos.get('avg_price', 0) > 0:
                        position_value = pos['volume'] * pos['avg_price']
                        current_weights[symbol] = position_value / total_value
        
        self.current_weights = current_weights
        return current_weights
    
    def calculate_deviation(self):
        """计算偏离度"""
        if not self.target_weights or not self.current_weights:
            return {}
        
        deviations = {}
        all_symbols = set(self.target_weights.keys()) | set(self.current_weights.keys())
        
        for symbol in all_symbols:
            target = self.target_weights.get(symbol, 0)
            current = self.current_weights.get(symbol, 0)
            deviation = current - target
            
            deviations[symbol] = {
                'target': target,
                'current': current,
                'deviation': deviation,
                'abs_deviation': abs(deviation),
            }
        
        return deviations
    
    def check_rebalance_condition(self):
        """检查是否需要再平衡"""
        if self.last_rebalance:
            days_since = (datetime.now() - self.last_rebalance).days
            if days_since < MIN_HOLDING_PERIOD:
                return False, "最小持有期内"
        
        deviations = self.calculate_deviation()
        if not deviations:
            return False, "无偏离数据"
        
        max_deviation = max(d['abs_deviation'] for d in deviations.values())
        
        if max_deviation > REBALANCE_THRESHOLD:
            turnover = sum(max(0, d['deviation']) for d in deviations.values())
            if turnover > MAX_TURNOVER:
                return False, f"换手率过高 ({turnover:.1%})"
            return True, f"偏离度过高 ({max_deviation:.1%})"
        
        return False, "偏离度在阈值内"
    
    def calculate_risk_parity_weights(self, volatilities):
        """计算风险平价权重"""
        if not volatilities:
            return self.target_weights
        
        inv_vol = {s: 1/v if v > 0 else 0 for s, v in volatilities.items()}
        total_inv = sum(inv_vol.values())
        
        if total_inv == 0:
            return self.target_weights
        
        return {s: inv_vol[s] / total_inv for s in volatilities}
    
    def calculate_volatility_for_symbol(self, symbol):
        """计算品种波动率"""
        prices = self.lookback_prices.get(symbol, [])
        if len(prices) < 10:
            return None
        
        returns = pd.Series(prices).pct_change().dropna()
        if len(returns) < 2:
            return None
        
        return returns.std() * np.sqrt(252)
    
    def update_lookback_prices(self, symbol, price):
        """更新回溯价格"""
        self.lookback_prices[symbol].append(price)
        if len(self.lookback_prices[symbol]) > LOOKBACK_PERIOD * 2:
            self.lookback_prices[symbol] = self.lookback_prices[symbol][-LOOKBACK_PERIOD:]
    
    def generate_rebalance_orders(self, total_value):
        """生成再平衡订单"""
        should_rebalance, reason = self.check_rebalance_condition()
        
        if not should_rebalance:
            return [], reason
        
        volatilities = {}
        for symbol in self.target_weights.keys():
            vol = self.calculate_volatility_for_symbol(symbol)
            if vol:
                volatilities[symbol] = vol
        
        target_weights = self.target_weights.copy()
        
        if RISK_PARITY_ENABLED and len(volatilities) == len(self.target_weights):
            target_weights = self.calculate_risk_parity_weights(volatilities)
        
        self.calculate_current_weights(total_value)
        
        orders = []
        
        for symbol, target_weight in target_weights.items():
            target_value = total_value * target_weight
            current_weight = self.current_weights.get(symbol, 0)
            current_value = total_value * current_weight
            diff_value = target_value - current_value
            
            if abs(diff_value) < total_value * 0.01:
                continue
            
            try:
                quote = self.api.get_quote(symbol)
                price = quote.get('last_price', 0)
                if price == 0:
                    continue
                volume = int(diff_value / price)
                if volume != 0:
                    orders.append({
                        'symbol': symbol,
                        'direction': 'buy' if volume > 0 else 'sell',
                        'volume': abs(volume),
                        'price': price,
                    })
            except:
                pass
        
        self.last_rebalance = datetime.now()
        self.rebalance_history.append({
            'time': self.last_rebalance,
            'reason': reason,
            'orders': orders,
        })
        
        return orders, reason
    
    def get_rebalance_preview(self, total_value):
        """预览再平衡结果"""
        self.calculate_current_weights(total_value)
        
        deviations = self.calculate_deviation()
        turnover = sum(max(0, d['deviation']) for d in deviations.values()) if deviations else 0
        
        return {
            'current_weights': self.current_weights,
            'deviations': deviations,
            'estimated_turnover': turnover,
            'should_rebalance': turnover > REBALANCE_THRESHOLD
        }
    
    def generate_report(self):
        """生成再平衡报告"""
        report = "=" * 60 + "\n"
        report += "智能再平衡策略报告\n"
        report += "=" * 60 + "\n"
        
        if not self.target_weights:
            report += "未设置目标权重\n"
            return report
        
        report += f"目标权重: {len(self.target_weights)} 个品种\n"
        report += f"再平衡阈值: {REBALANCE_THRESHOLD:.1%}\n"
        
        if self.last_rebalance:
            days_since = (datetime.now() - self.last_rebalance).days
            report += f"上次再平衡: {self.last_rebalance.strftime('%Y-%m-%d')} ({days_since}天前)\n"
        else:
            report += "上次再平衡: 从未\n"
        
        report += "\n权重偏离:\n"
        for symbol in sorted(self.target_weights.keys()):
            target = self.target_weights.get(symbol, 0)
            current = self.current_weights.get(symbol, 0)
            deviation = current - target
            status = "OK" if abs(deviation) < REBALANCE_THRESHOLD else "WARN"
            report += f"  {symbol}: 目标 {target:.1%} vs 当前 {current:.1%} [{status}]\n"
        
        should_rebalance, reason = self.check_rebalance_condition()
        report += f"\n建议: {'执行再平衡' if should_rebalance else '保持仓位'} ({reason})\n"
        
        return report


def main():
    """测试"""
    import random
    strategy = SmartRebalancingStrategy(None)
    strategy.target_weights = {'CU2401': 0.25, 'RB2401': 0.25, 'IF2401': 0.20, 'AU2401': 0.15, 'AG2401': 0.15}
    strategy.positions = {'CU2401': {'volume': 2, 'avg_price': 68000}, 'RB2401': {'volume': 3, 'avg_price': 3700}, 'IF2401': {'volume': 1, 'avg_price': 3850}}
    base_prices = {'CU2401': 68000, 'RB2401': 3800, 'IF2401': 3800, 'AU2401': 480, 'AG2401': 5800}
    for _ in range(25):
        for symbol, price in base_prices.items():
            strategy.lookback_prices[symbol].append(price * (1 + random.uniform(-0.01, 0.01)))
    print(strategy.generate_report())


if __name__ == "__main__":
    main()
