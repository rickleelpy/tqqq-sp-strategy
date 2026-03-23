"""
TQQQ 期权数据获取
使用 Yahoo Finance API 获取期权数据
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import config


class OptionsFetcher:
    """期权数据获取器"""
    
    def __init__(self, ticker: str = config.TICKER):
        self.ticker = ticker
        self.yf_ticker = yf.Ticker(ticker)
    
    def get_current_price(self) -> float:
        """获取当前标的价格"""
        return self.yf_ticker.history(period="1d")['Close'].iloc[-1]
    
    def get_expiry_dates(self) -> List[str]:
        """获取所有到期日"""
        expirations = self.yf_ticker.options
        return expirations if expirations else []
    
    def get_nearest_friday(self) -> Optional[str]:
        """获取最近的下周五到期日"""
        today = datetime.now()
        # 找到下周五
        days_until_friday = (4 - today.weekday() + 7) % 7
        if days_until_friday == 0:
            days_until_friday = 7  # 如果今天是周五，取下周五
        next_friday = today + timedelta(days=days_until_friday)
        
        # 格式化为 YYYY-MM-DD
        return next_friday.strftime("%Y-%m-%d")
    
    def get_options_chain(self, expiry: str) -> Dict:
        """获取指定到期日的期权链"""
        try:
            return self.yf_ticker.option_chain(expiry)
        except Exception as e:
            print(f"获取期权链失败: {e}")
            return {"calls": [], "puts": []}
    
    def get_put_options(self, expiry: str) -> List[Dict]:
        """获取看跌期权数据"""
        chain = self.get_options_chain(expiry)
        puts = chain.get('puts', [])
        
        # 转换为字典列表
        if hasattr(puts, 'to_dict'):
            puts = puts.to_dict('records')
        
        return puts
    
    def fetch_all_data(self) -> Dict:
        """获取所有数据"""
        current_price = self.get_current_price()
        target_expiry = self.get_nearest_friday()
        
        result = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticker": self.ticker,
            "current_price": current_price,
            "target_expiry": target_expiry,
            "strike_threshold": current_price * (1 - config.STRIKE_DISCOUNT),
            "puts": []
        }
        
        if target_expiry:
            result["puts"] = self.get_put_options(target_expiry)
        
        return result


def main():
    """测试用"""
    fetcher = OptionsFetcher()
    data = fetcher.fetch_all_data()
    
    print(f"标的: {data['ticker']}")
    print(f"当前价格: ${data['current_price']:.2f}")
    print(f"目标到期日: {data['target_expiry']}")
    print(f"行权价门槛 (低于现价 {config.STRIKE_DISCOUNT*100}%): ${data['strike_threshold']:.2f}")
    print(f"看跌期权数量: {len(data['puts'])}")


if __name__ == "__main__":
    main()
