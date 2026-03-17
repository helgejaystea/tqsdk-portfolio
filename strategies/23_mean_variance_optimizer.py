#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
均值-方差优化器 (Mean-Variance Optimizer)
经典MPT投资组合优化，支持_BLACK_Litterman改进和约束条件

Author: TqSdk Portfolio
Update: 2026-03-13
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime, timedelta
from scipy import optimize, stats
import warnings
warnings.filterwarnings('ignore')


class MeanVarianceOptimizer:
    """均值-方差优化器"""
    
    def __init__(self, 
                 risk_aversion: float = 1.0,
                 allow_short: bool = False):
        """
        初始化优化器
        
        Args:
            risk_aversion: 风险厌恶系数 (0-10)
            allow_short: 是否允许做空
        """
        self.risk_aversion = risk_aversion
        self.allow_short = allow_short
        
        self.expected_returns = None
        self.covariance_matrix = None
        self.asset_names = []
        
    def set_returns_and_cov(self, 
                            returns: Dict[str, float],
                            cov_matrix: pd.DataFrame):
        """
        设置收益率和协方差矩阵
        
        Args:
            returns: 各资产预期收益率
            cov_matrix: 协方差矩阵
        """
        self.asset_names = list(returns.keys())
        self.expected_returns = np.array([returns[k] for k in self.asset_names])
        self.covariance_matrix = cov_matrix.loc[self.asset_names, self.asset_names].values
        
    def portfolio_return(self, weights: np.ndarray) -> float:
        """计算组合预期收益"""
        return np.dot(weights, self.expected_returns)
        
    def portfolio_volatility(self, weights: np.ndarray) -> float:
        """计算组合波动率"""
        return np.sqrt(np.dot(weights.T, np.dot(self.covariance_matrix, weights)))
        
    def portfolio_sharpe(self, weights: np.ndarray, 
                        risk_free_rate: float = 0.03) -> float:
        """计算组合夏普比率"""
        ret = self.portfolio_return(weights)
        vol = self.portfolio_volatility(weights)
        
        if vol == 0:
            return 0.0
            
        return (ret - risk_free_rate) / vol
        
    def optimize_max_sharpe(self, 
                           risk_free_rate: float = 0.03) -> Dict:
        """
        优化最大夏普比率
        
        Args:
            risk_free_rate: 无风险利率
            
        Returns:
            优化结果
        """
        n = len(self.asset_names)
        
        # 目标函数：负夏普比率
        def objective(weights):
            sharpe = self.portfolio_sharpe(weights, risk_free_rate)
            return -sharpe
            
        # 约束条件
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}  # 权重和为1
        ]
        
        # 边界
        if self.allow_short:
            bounds = tuple((-1, 1) for _ in range(n))
        else:
            bounds = tuple((0, 1) for _ in range(n))
            
        # 初始权重
        x0 = np.ones(n) / n
        
        result = optimize.minimize(
            objective, x0, method='SLSQP',
            bounds=bounds, constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            weights = result.x
            return {
                'status': 'SUCCESS',
                'weights': dict(zip(self.asset_names, weights.tolist())),
                'expected_return': self.portfolio_return(weights),
                'volatility': self.portfolio_volatility(weights),
                'sharpe_ratio': self.portfolio_sharpe(weights, risk_free_rate)
            }
        else:
            return {
                'status': 'FAILED',
                'message': result.message
            }
            
    def optimize_min_variance(self) -> Dict:
        """优化最小方差"""
        n = len(self.asset_names)
        
        def objective(weights):
            return self.portfolio_volatility(weights) ** 2
            
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        ]
        
        if self.allow_short:
            bounds = tuple((-1, 1) for _ in range(n))
        else:
            bounds = tuple((0, 1) for _ in range(n))
            
        x0 = np.ones(n) / n
        
        result = optimize.minimize(
            objective, x0, method='SLSQP',
            bounds=bounds, constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            weights = result.x
            return {
                'status': 'SUCCESS',
                'weights': dict(zip(self.asset_names, weights.tolist())),
                'expected_return': self.portfolio_return(weights),
                'volatility': self.portfolio_volatility(weights),
                'sharpe_ratio': self.portfolio_sharpe(weights)
            }
        else:
            return {
                'status': 'FAILED',
                'message': result.message
            }
            
    def optimize_target_return(self, target_return: float) -> Dict:
        """优化目标收益下的最小方差"""
        n = len(self.asset_names)
        
        def objective(weights):
            return self.portfolio_volatility(weights) ** 2
            
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'eq', 'fun': lambda w: self.portfolio_return(w) - target_return}
        ]
        
        if self.allow_short:
            bounds = tuple((-1, 1) for _ in range(n))
        else:
            bounds = tuple((0, 1) for _ in range(n))
            
        x0 = np.ones(n) / n
        
        result = optimize.minimize(
            objective, x0, method='SLSQP',
            bounds=bounds, constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            weights = result.x
            return {
                'status': 'SUCCESS',
                'weights': dict(zip(self.asset_names, weights.tolist())),
                'expected_return': target_return,
                'volatility': self.portfolio_volatility(weights),
                'sharpe_ratio': self.portfolio_sharpe(weights)
            }
        else:
            return {
                'status': 'FAILED',
                'message': result.message
            }
            
    def optimize_target_risk(self, target_vol: float) -> Dict:
        """优化目标风险下的最大收益"""
        n = len(self.asset_names)
        
        def objective(weights):
            return -self.portfolio_return(weights)
            
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1},
            {'type': 'eq', 'fun': lambda w: self.portfolio_volatility(w) - target_vol}
        ]
        
        if self.allow_short:
            bounds = tuple((-1, 1) for _ in range(n))
        else:
            bounds = tuple((0, 1) for _ in range(n))
            
        x0 = np.ones(n) / n
        
        result = optimize.minimize(
            objective, x0, method='SLSQP',
            bounds=bounds, constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            weights = result.x
            return {
                'status': 'SUCCESS',
                'weights': dict(zip(self.asset_names, weights.tolist())),
                'expected_return': self.portfolio_return(weights),
                'volatility': target_vol,
                'sharpe_ratio': self.portfolio_sharpe(weights)
            }
        else:
            return {
                'status': 'FAILED',
                'message': result.message
            }
            
    def generate_efficient_frontier(self, 
                                   num_points: int = 50) -> pd.DataFrame:
        """生成有效前沿"""
        results = []
        
        # 获取收益范围
        min_ret = np.min(self.expected_returns)
        max_ret = np.max(self.expected_returns)
        
        target_returns = np.linspace(min_ret, max_ret, num_points)
        
        for target in target_returns:
            result = self.optimize_target_return(target)
            if result['status'] == 'SUCCESS':
                results.append({
                    'expected_return': result['expected_return'],
                    'volatility': result['volatility'],
                    'sharpe_ratio': result['sharpe_ratio']
                })
                
        return pd.DataFrame(results)


class BlackLittermanOptimizer:
    """Black-Litterman优化器"""
    
    def __init__(self, 
                 risk_aversion: float = 2.5,
                 tau: float = 0.05):
        """
        初始化BL优化器
        
        Args:
            risk_aversion: 市场风险厌恶系数
            tau: 观点不确定性参数
        """
        self.risk_aversion = risk_aversion
        self.tau = tau
        
        self.market_cap_weights = None
        self.market_covariance = None
        self.asset_names = []
        
    def set_market_data(self, 
                       cap_weights: Dict[str, float],
                       cov_matrix: pd.DataFrame):
        """设置市场数据"""
        self.asset_names = list(cap_weights.keys())
        self.market_cap_weights = np.array([cap_weights[k] for k in self.asset_names])
        self.market_covariance = cov_matrix.loc[self.asset_names, self.asset_names].values
        
    def calculate_implied_returns(self) -> np.ndarray:
        """计算隐含超额收益 (reverse-optimization)"""
        # Π = λ * Σ * w_market
        pi = self.risk_aversion * np.dot(self.market_covariance, self.market_cap_weights)
        return pi
        
    def add_view(self, 
                view_assets: List[str],
                view_returns: List[float],
                confidence: float = 0.5):
        """
        添加观点
        
        Args:
            view_assets: 观点涉及的资产
            view_returns: 观点预期收益
            confidence: 置信度 (0-1)
        """
        self.view_assets = view_assets
        self.view_returns = view_returns
        self.view_confidence = confidence
        
    def optimize_bl(self) -> Dict:
        """执行Black-Litterman优化"""
        if self.market_cap_weights is None:
            return {'status': 'ERROR', 'message': 'Need market data first'}
            
        # 隐含收益
        pi = self.calculate_implied_returns()
        
        # 观点矩阵 (简化版：单个观点)
        if hasattr(self, 'view_assets'):
            P = np.zeros((1, len(self.asset_names)))
            Q = np.array([self.view_returns[0]]])
            
            # 置信度调整
            omega = self.tau * np.diag(np.dot(P, np.dot(self.market_covariance, P.T))).flatten()
            
            # BL公式
            tau_sigma = self.tau * self.market_covariance
            inv_tau_sigma = np.linalg.inv(tau_sigma) if np.linalg.det(tau_sigma) > 1e-10 else np.linalg.pinv(tau_sigma)
            
            M = np.linalg.inv(np.linalg.inv(self.market_covariance) + np.dot(P.T, np.linalg.pinv(np.diag(omega)), P))
            
            combined_returns = np.dot(M, 
                np.dot(np.linalg.inv(self.market_covariance), pi) + 
                np.dot(P.T, np.linalg.pinv(omega), Q))
            
            bl_returns = dict(zip(self.asset_names, combined_returns.tolist()))
            
            # 使用均值-方差优化
            mvo = MeanVarianceOptimizer(risk_aversion=self.risk_aversion)
            mvo.set_returns_and_cov(bl_returns, 
                                   pd.DataFrame(self.market_covariance, 
                                               index=self.asset_names,
                                               columns=self.asset_names))
            
            return mvo.optimize_max_sharpe()
        else:
            # 无观点，返回市场组合
            return {
                'status': 'NO_VIEWS',
                'weights': dict(zip(self.asset_names, self.market_cap_weights.tolist()))
            }


class RiskBudgetOptimizer:
    """风险预算优化器"""
    
    def __init__(self, target_vol: float = 0.15):
        self.target_vol = target_vol
        self.covariance_matrix = None
        self.asset_names = []
        
    def set_covariance(self, cov_matrix: pd.DataFrame):
        """设置协方差矩阵"""
        self.asset_names = list(cov_matrix.columns)
        self.covariance_matrix = cov_matrix.values
        
    def optimize_risk_parity(self) -> Dict:
        """优化风险平价组合"""
        n = len(self.asset_names)
        
        def risk_contribution(weights):
            """计算各资产风险贡献"""
            port_vol = np.sqrt(np.dot(weights.T, np.dot(self.covariance_matrix, weights)))
            marginal_contrib = np.dot(self.covariance_matrix, weights)
            risk_contrib = weights * marginal_contrib / port_vol
            return risk_contrib
            
        def objective(weights):
            """最小化风险贡献差异"""
            rc = risk_contribution(weights)
            target_rc = np.mean(rc)
            return np.sum((rc - target_rc) ** 2)
            
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        ]
        
        bounds = tuple((0.01, 1) for _ in range(n))
        x0 = np.ones(n) / n
        
        result = optimize.minimize(
            objective, x0, method='SLSQP',
            bounds=bounds, constraints=constraints,
            options={'maxiter': 1000}
        )
        
        if result.success:
            weights = result.x
            vol = np.sqrt(np.dot(weights.T, np.dot(self.covariance_matrix, weights)))
            
            # 调整到目标波动率
            if vol > 0:
                weights = weights * (self.target_vol / vol)
                
            return {
                'status': 'SUCCESS',
                'weights': dict(zip(self.asset_names, weights.tolist())),
                'expected_vol': np.sqrt(np.dot(weights.T, np.dot(self.covariance_matrix, weights)))
            }
        else:
            return {
                'status': 'FAILED',
                'message': result.message
            }


def main():
    """主函数 - 演示用法"""
    # 创建资产数据
    assets = ['SHFE.rb', 'DCE.m', 'CZCE.CF', 'DCE.y', 'CZCE.SR']
    
    # 预期收益率 (年化)
    expected_returns = {
        'SHFE.rb': 0.08,
        'DCE.m': 0.10,
        'CZCE.CF': 0.06,
        'DCE.y': 0.12,
        'CZCE.SR': 0.07
    }
    
    # 协方差矩阵
    cov_data = {
        'SHFE.rb': [0.0400, 0.0150, 0.0080, 0.0120, 0.0060],
        'DCE.m':  [0.0150, 0.0225, 0.0090, 0.0100, 0.0070],
        'CZCE.CF':[0.0080, 0.0090, 0.0100, 0.0050, 0.0040],
        'DCE.y':  [0.0120, 0.0100, 0.0050, 0.0300, 0.0060],
        'CZCE.SR':[0.0060, 0.0070, 0.0040, 0.0060, 0.0080]
    }
    cov_matrix = pd.DataFrame(cov_data, index=assets, columns=assets)
    
    # 均值-方差优化
    mvo = MeanVarianceOptimizer(risk_aversion=2.0)
    mvo.set_returns_and_cov(expected_returns, cov_matrix)
    
    print("=== 最大夏普比率组合 ===")
    result = mvo.optimize_max_sharpe()
    if result['status'] == 'SUCCESS':
        for asset, weight in result['weights'].items():
            if weight > 0.001:
                print(f"{asset}: {weight:.2%}")
        print(f"预期收益: {result['expected_return']:.2%}")
        print(f"波动率: {result['volatility']:.2%}")
        print(f"夏普比率: {result['sharpe_ratio']:.2f}")
        
    print("\n=== 最小方差组合 ===")
    result = mvo.optimize_min_variance()
    if result['status'] == 'SUCCESS':
        for asset, weight in result['weights'].items():
            if weight > 0.001:
                print(f"{asset}: {weight:.2%}")
        print(f"波动率: {result['volatility']:.2%}")
        
    # 风险平价优化
    print("\n=== 风险平价组合 ===")
    rbo = RiskBudgetOptimizer(target_vol=0.10)
    rbo.set_covariance(cov_matrix)
    result = rbo.optimize_risk_parity()
    if result['status'] == 'SUCCESS':
        for asset, weight in result['weights'].items():
            if weight > 0.001:
                print(f"{asset}: {weight:.2%}")


if __name__ == "__main__":
    main()
