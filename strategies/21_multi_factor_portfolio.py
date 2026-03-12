#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多因子组合策略 (Multi-Factor Portfolio Strategy)
基于多个Alpha因子构建投资组合，因子加权优化

Author: TqSdk Portfolio
Update: 2026-03-12
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats, optimize
import warnings


class MultiFactorPortfolio:
    """多因子组合策略"""
    
    def __init__(self, risk_target: float = 0.15,
                 max_weight: float = 0.3,
                 min_weight: float = 0.05):
        self.risk_target = risk_target
        self.max_weight = max_weight
        self.min_weight = min_weight
        self.factor_signals = {}
        self.factor_returns = {}
        self.factor_cov = None
        self.weights = None
        
    def add_factor_signal(self, factor_name: str, 
                          signals: Dict[str, float],
                          historical_returns: Optional[Dict[str, float]] = None):
        self.factor_signals[factor_name] = signals
        if historical_returns:
            self.factor_returns[factor_name] = historical_returns
            
    def calculate_factor_exposure(self) -> pd.DataFrame:
        if not self.factor_signals:
            raise ValueError("No factor signals")
        symbols = set()
        for signals in self.factor_signals.values():
            symbols.update(signals.keys())
        symbols = sorted(list(symbols))
        exposure = pd.DataFrame(index=symbols, columns=self.factor_signals.keys())
        for factor_name, signals in self.factor_signals.items():
            for symbol in symbols:
                exposure.loc[symbol, factor_name] = signals.get(symbol, 0)
        return exposure.astype(float)
        
    def optimize_portfolio(self, exposure: pd.DataFrame) -> pd.Series:
        symbols = exposure.index.tolist()
        n = len(symbols)
        factor_weights = np.array([1.0 / len(self.factor_signals)] * len(self.factor_signals))
        expected_returns = exposure.dot(pd.Series(factor_weights, index=exposure.columns))
        
        def objective(w):
            port_return = np.dot(w, expected_returns.values)
            port_vol = np.std(expected_returns) * np.sqrt(np.dot(w, w))
            return -(port_return - 0.02) / (port_vol + 1e-10)
            
        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
        bounds = [(self.min_weight, self.max_weight) for _ in range(n)]
        w0 = np.ones(n) / n
        
        result = optimize.minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=constraints, options={'maxiter': 1000})
        if result.success:
            weights = pd.Series(result.x, index=symbols)
            weights = weights.clip(lower=self.min_weight)
            weights = weights / weights.sum()
            return weights
        return pd.Series(1/n, index=symbols)
        
    def get_portfolio_report(self) -> Dict:
        return {
            'timestamp': datetime.now().isoformat(),
            'risk_target': self.risk_target,
            'current_weights': self.weights.to_dict() if self.weights is not None else {}
        }


def demo():
    np.random.seed(42)
    symbols = ['SHFE.rb', 'SHFE.hc', 'DCE.i', 'DCE.j', 'CZCE.ma', 'CZCE.sf']
    momentum_signals = {s: np.random.uniform(-0.5, 0.5) for s in symbols}
    volatility_signals = {s: np.random.uniform(-0.3, 0.3) for s in symbols}
    
    strategy = MultiFactorPortfolio(risk_target=0.15, max_weight=0.3, min_weight=0.05)
    strategy.add_factor_signal('momentum', momentum_signals, {s: np.random.normal(0.001, 0.02) for s in symbols})
    strategy.add_factor_signal('volatility', volatility_signals, {s: np.random.normal(0.001, 0.02) for s in symbols})
    
    exposure = strategy.calculate_factor_exposure()
    weights = strategy.optimize_portfolio(exposure)
    
    print("=" * 60)
    print("多因子组合策略")
    print("=" * 60)
    print("\n优化后的权重:")
    for symbol, weight in weights.items():
        print(f"  {symbol}: {weight:.2%}")
    print("\n" + "=" * 60)
    return strategy.get_portfolio_report()


if __name__ == '__main__':
    demo()
