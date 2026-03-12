#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
跨品种对冲策略 (Cross-Instrument Hedging Strategy)
基于相关性、协整关系的动态对冲组合

Author: TqSdk Portfolio
Update: 2026-03-12
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from scipy import stats
from statsmodels.tsa.stattools import coint


class CrossInstrumentHedge:
    """跨品种对冲策略"""
    
    def __init__(self, lookback_period: int = 60, hedge_threshold: float = 0.5):
        self.lookback_period = lookback_period
        self.hedge_threshold = hedge_threshold
        self.price_data = {}
        
    def add_price_series(self, symbol: str, prices: pd.Series):
        self.price_data[symbol] = prices.dropna()
        
    def calculate_correlation(self, symbol1: str, symbol2: str) -> float:
        if symbol1 not in self.price_data or symbol2 not in self.price_data:
            return 0.0
        p1 = self.price_data[symbol1]
        p2 = self.price_data[symbol2]
        common_idx = p1.index.intersection(p2.index)
        if len(common_idx) < 10:
            return 0.0
        returns1 = p1.loc[common_idx].pct_change().dropna()
        returns2 = p2.loc[common_idx].pct_change().dropna()
        return returns1.corr(returns2)
        
    def calculate_cointegration(self, symbol1: str, symbol2: str) -> Tuple[float, float, float]:
        if symbol1 not in self.price_data or symbol2 not in self.price_data:
            return (0, 1, 1)
        p1 = self.price_data[symbol1].iloc[-self.lookback_period:]
        p2 = self.price_data[symbol2].iloc[-self.lookback_period:]
        common_idx = p1.index.intersection(p2.index)
        if len(common_idx) < 20:
            return (0, 1, 1)
        p1_aligned = p1.loc[common_idx].values
        p2_aligned = p2.loc[common_idx].values
        try:
            score, pvalue, _ = coint(p1_aligned, p2_aligned)
            hedge_ratio = np.linalg.lstsq(p2_aligned.reshape(-1, 1), p1_aligned, rcond=None)[0][0]
            return (score, pvalue, hedge_ratio)
        except:
            return (0, 1, 1)
            
    def calculate_spread(self, symbol1: str, symbol2: str) -> pd.Series:
        if symbol1 not in self.price_data or symbol2 not in self.price_data:
            return pd.Series()
        p1 = self.price_data[symbol1].iloc[-self.lookback_period:]
        p2 = self.price_data[symbol2].iloc[-self.lookback_period:]
        common_idx = p1.index.intersection(p2.index)
        hedge_ratio = self.calculate_cointegration(symbol1, symbol2)[2]
        spread = p1.loc[common_idx] - hedge_ratio * p2.loc[common_idx]
        return spread
        
    def calculate_zscore(self, spread: pd.Series, lookback: int = 20) -> pd.Series:
        mean = spread.rolling(lookback).mean()
        std = spread.rolling(lookback).std()
        zscore = (spread - mean) / std
        return zscore
        
    def find_optimal_pairs(self, min_correlation: float = 0.5, max_pvalue: float = 0.05) -> List[Dict]:
        symbols = list(self.price_data.keys())
        pairs = []
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                s1, s2 = symbols[i], symbols[j]
                corr = self.calculate_correlation(s1, s2)
                score, pvalue, hedge_ratio = self.calculate_cointegration(s1, s2)
                if abs(corr) >= min_correlation and pvalue <= max_pvalue:
                    pairs.append({
                        'symbol1': s1, 'symbol2': s2,
                        'correlation': corr, 'cointegration_pvalue': pvalue,
                        'hedge_ratio': hedge_ratio, 'score': score
                    })
        pairs.sort(key=lambda x: x['cointegration_pvalue'])
        return pairs
        
    def calculate_hedge_performance(self, symbol1: str, symbol2: str) -> Dict:
        spread = self.calculate_spread(symbol1, symbol2)
        zscore = self.calculate_zscore(spread)
        spread_returns = spread.pct_change().dropna()
        position = 0
        strategy_returns = []
        for i in range(len(zscore)):
            z = zscore.iloc[i]
            ret = spread_returns.iloc[i] if i < len(spread_returns) else 0
            if pd.isna(z):
                strategy_returns.append(0)
                continue
            if z > 2.0:
                position = -1
            elif z < -2.0:
                position = 1
            elif abs(z) < 0.5:
                position = 0
            strategy_returns.append(position * ret)
        strategy_returns = np.array(strategy_returns)
        return {
            'strategy_return': strategy_returns.mean() * 252,
            'strategy_volatility': strategy_returns.std() * np.sqrt(252),
            'sharpe_ratio': (strategy_returns.mean() * 252) / (strategy_returns.std() * np.sqrt(252)) if strategy_returns.std() > 0 else 0
        }
        
    def generate_hedge_report(self) -> Dict:
        optimal_pairs = self.find_optimal_pairs()
        return {
            'timestamp': datetime.now().isoformat(),
            'lookback_period': self.lookback_period,
            'optimal_pairs': optimal_pairs[:5] if len(optimal_pairs) >= 5 else optimal_pairs
        }


def demo():
    np.random.seed(42)
    symbols = ['SHFE.rb', 'SHFE.hc', 'DCE.i', 'DCE.j', 'CZCE.ma', 'CZCE.sf']
    n_days = 120
    
    rb_prices = 5000 + np.cumsum(np.random.normal(5, 80, n_days))
    hc_prices = 4500 + np.cumsum(np.random.normal(4.5, 75, n_days))
    i_prices = 1200 + np.cumsum(np.random.normal(2, 40, n_days))
    j_prices = 2500 + np.cumsum(np.random.normal(3, 50, n_days))
    ma_prices = 2500 + np.cumsum(np.random.normal(0, 60, n_days))
    sf_prices = 22000 + np.cumsum(np.random.normal(-5, 300, n_days))
    
    price_dict = {
        'SHFE.rb': pd.Series(rb_prices, index=pd.date_range('2025-01-01', periods=n_days)),
        'SHFE.hc': pd.Series(hc_prices, index=pd.date_range('2025-01-01', periods=n_days)),
        'DCE.i': pd.Series(i_prices, index=pd.date_range('2025-01-01', periods=n_days)),
        'DCE.j': pd.Series(j_prices, index=pd.date_range('2025-01-01', periods=n_days)),
        'CZCE.ma': pd.Series(ma_prices, index=pd.date_range('2025-01-01', periods=n_days)),
        'CZCE.sf': pd.Series(sf_prices, index=pd.date_range('2025-01-01', periods=n_days))
    }
    
    hedge = CrossInstrumentHedge(lookback_period=60)
    for symbol, prices in price_dict.items():
        hedge.add_price_series(symbol, prices)
    
    pairs = hedge.find_optimal_pairs(min_correlation=0.3, max_pvalue=0.1)
    
    print("=" * 60)
    print("跨品种对冲分析报告")
    print("=" * 60)
    print("\n最优配对:")
    for i, pair in enumerate(pairs[:3], 1):
        print(f"  {i}. {pair['symbol1']} - {pair['symbol2']}")
        print(f"     相关性: {pair['correlation']:.4f}")
        print(f"     协整P值: {pair['cointegration_pvalue']:.4f}")
        print(f"     对冲比率: {pair['hedge_ratio']:.4f}")
    print("\n" + "=" * 60)
    return hedge.generate_hedge_report()


if __name__ == '__main__':
    demo()
