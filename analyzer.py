"""
期权策略分析器
根据用户策略筛选合适的期权并计算风险收益
"""

import config
from typing import List, Dict, Optional
from datetime import datetime


class StrategyAnalyzer:
    """策略分析器"""
    
    def __init__(self, market_data: Dict):
        self.data = market_data
        self.current_price = market_data["current_price"]
        self.strike_threshold = market_data["strike_threshold"]
        self.expiry = market_data["target_expiry"]
    
    def filter_puts(self) -> List[Dict]:
        """筛选符合策略条件的看跌期权"""
        filtered = []
        
        for put in self.data.get("puts", []):
            # 获取关键字段
            strike = put.get('strike', 0)
            bid = put.get('bid', 0)
            ask = put.get('ask', 0)
            volume = put.get('volume', 0)
            open_interest = put.get('openInterest', 0)
            iv = put.get('impliedVolatility', 0)
            
            # 跳过无效数据
            if strike <= 0 or bid <= 0:
                continue
            
            # 计算权利金
            premium = (bid + ask) / 2  # 中间价
            premium_pct = premium / self.current_price * 100  # 权利金比例
            
            # 筛选条件
            if strike >= self.strike_threshold:  # 行权价低于现价20%
                continue
            
            if premium < config.MIN_PREMIUM:  # 最小权利金
                continue
            
            # 计算关键指标
            delta = put.get('delta', 0)
            theta = put.get('theta', 0)
            gamma = put.get('gamma', 0)
            rho = put.get('rho', 0)
            
            # 计算风险指标
            risk_reward = self._calc_risk_reward(premium, strike)
            max_loss = strike - premium  # 最大亏损（如果不接股被行权）
            break_even = strike - premium  # 盈亏平衡点
            
            # 保证金估算 (SP 需要缴纳保证金)
            margin = self._estimate_margin(strike, premium)
            
            filtered.append({
                "strike": strike,
                "premium": premium,
                "premium_pct": premium_pct,
                "bid": bid,
                "ask": ask,
                "volume": volume,
                "open_interest": open_interest,
                "iv": iv,
                "delta": delta,
                "theta": theta,
                "gamma": gamma,
                "rho": rho,
                "risk_reward": risk_reward,
                "max_loss": max_loss,
                "break_even": break_even,
                "margin": margin,
                "days_to_expiry": self._days_to_expiry(),
            })
        
        # 按权利金排序（从高到低）
        filtered.sort(key=lambda x: x["premium"], reverse=True)
        
        return filtered
    
    def _calc_risk_reward(self, premium: float, strike: float) -> float:
        """计算风险收益比"""
        max_loss = strike - premium
        if max_loss > 0:
            return premium / max_loss
        return 0
    
    def _estimate_margin(self, strike: float, premium: float) -> float:
        """估算保证金 (简化版)"""
        # SP 保证金通常为期权价值或 20% 行权价 - OTM 金额
        # 这里用简化公式
        return min(strike * 100 * 0.20, strike * 100 - premium * 100)
    
    def _days_to_expiry(self) -> int:
        """计算到期天数"""
        if not self.expiry:
            return 0
        try:
            expiry_date = datetime.strptime(self.expiry, "%Y-%m-%d")
            today = datetime.now()
            return max(0, (expiry_date - today).days)
        except:
            return 0
    
    def rank_options(self, puts: List[Dict]) -> List[Dict]:
        """对期权进行排名打分"""
        scored = []
        
        for put in puts:
            score = 0
            reasons = []
            
            # 权利金得分 (越高越好)
            if put["premium"] >= 200:
                score += 30
                reasons.append("权利金高")
            elif put["premium"] >= 100:
                score += 20
                reasons.append("权利金中等")
            else:
                score += 10
            
            # Delta 得分 (越接近 -0.3 越好，表示有支撑)
            delta = abs(put.get("delta", 0))
            if 0.15 <= delta <= 0.30:
                score += 20
                reasons.append("Delta 适中")
            elif delta < 0.15:
                score += 10
                reasons.append("Delta 低 (更安全)")
            
            # 流动性得分 (成交量和未平仓)
            oi = put.get("open_interest", 0)
            if oi >= 1000:
                score += 20
                reasons.append("流动性好")
            elif oi >= 100:
                score += 10
            
            # IV 得分 (IV 高 = 权利金高，但风险大)
            iv = put.get("iv", 0)
            if iv > 0.8:
                score += 10
                reasons.append("IV 高 (波动大)")
            elif 0.4 <= iv <= 0.8:
                score += 15
                reasons.append("IV 适中")
            
            # 风险收益比得分
            if put["risk_reward"] >= 0.15:
                score += 20
                reasons.append("风险收益比好")
            
            scored.append({
                **put,
                "score": score,
                "reasons": reasons
            })
        
        # 按得分排序
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored
    
    def generate_recommendation(self) -> Dict:
        """生成推荐报告"""
        puts = self.filter_puts()
        
        if not puts:
            return {
                "has_opportunity": False,
                "message": "当前没有符合条件的期权",
                "details": {
                    "current_price": self.current_price,
                    "strike_threshold": self.strike_threshold,
                    "expiry": self.expiry
                }
            }
        
        ranked = self.rank_options(puts)
        top_pick = ranked[0]
        
        # 风险检查
        warnings = []
        
        # 检查是否超过每周最大亏损
        if top_pick["max_loss"] > config.MAX_WEEKLY_LOSS_AMOUNT:
            warnings.append(f"⚠️ 单笔最大亏损 ${top_pick['max_loss']:.0f} 超过每周限制 ${config.MAX_WEEKLY_LOSS_AMOUNT:.0f}")
        
        # 检查保证金是否足够
        if top_pick["margin"] > config.CAPITAL * 0.5:
            warnings.append(f"⚠️ 保证金占比 {(top_pick['margin']/config.CAPITAL*100):.0f}% 较高")
        
        # 检查流动性
        if top_pick.get("open_interest", 0) < 100:
            warnings.append("⚠️ 流动性较低")
        
        return {
            "has_opportunity": True,
            "top_pick": top_pick,
            "alternatives": ranked[1:4] if len(ranked) > 1 else [],
            "warnings": warnings,
            "strategy_summary": {
                "ticker": config.TICKER,
                "strategy": "Short Put",
                "expiry": self.expiry,
                "target_strike": f"${top_pick['strike']:.2f} (低于现价 {(1-top_pick['strike']/self.current_price)*100:.1f}%)",
                "premium": f"${top_pick['premium']:.2f}",
                "max_loss": f"${top_pick['max_loss']:.2f}",
                "break_even": f"${top_pick['break_even']:.2f}",
                "risk_reward": f"1:{top_pick['risk_reward']:.2f}",
            }
        }


def analyze_market(market_data: Dict) -> Dict:
    """分析市场数据并返回推荐"""
    analyzer = StrategyAnalyzer(market_data)
    return analyzer.generate_recommendation()
