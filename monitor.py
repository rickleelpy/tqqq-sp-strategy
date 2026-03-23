#!/usr/bin/env python3
"""
TQQQ SP 策略监控服务
仅在美股盘中交易时间运行，发现符合条件期权时通知
"""

import yfinance as yf
import time
import pytz
from datetime import datetime, timedelta
import json
import os
import sys

# 本地配置导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

# ==================== 配置 ====================
CHECK_INTERVAL = 900  # 15分钟检查一次
NOTIFIED_FILE = "/tmp/tqqq_notified.json"  # 已通知记录

# ==================== 通知配置 ====================
# 飞书 webhook（需要用户配置）
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")

# 微信通知（需要企业微信或其他方式）
WECHAT_WEBHOOK = os.environ.get("WECHAT_WEBHOOK", "")


# ==================== 工具函数 ====================
def is_us_market_open():
    """检查美股是否在交易时间"""
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    
    if now_et.weekday() >= 5:  # 周六周日
        return False
    
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now_et <= market_close


def get_beijing_time():
    """获取北京时间"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(beijing_tz)


def send_feishu(message):
    """发送飞书通知"""
    if not FEISHU_WEBHOOK:
        print("未配置飞书 Webhook")
        return False
    
    try:
        import requests
        payload = {"msg_type": "text", "content": {"text": message}}
        resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"飞书通知失败: {e}")
        return False


def send_wechat(message):
    """发送微信通知"""
    if not WECHAT_WEBHOOK:
        print("未配置微信 Webhook")
        return False
    
    try:
        import requests
        resp = requests.post(WECHAT_WEBHOOK, json={"msgtype": "text", "text": {"content": message}}, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"微信通知失败: {e}")
        return False


def load_notified():
    """加载已通知记录"""
    if os.path.exists(NOTIFIED_FILE):
        with open(NOTIFIED_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_notified(data):
    """保存已通知记录"""
    with open(NOTIFIED_FILE, 'w') as f:
        json.dump(data, f)


def is_already_notified(strike, expiry):
    """检查是否已经通知过"""
    notified = load_notified()
    key = f"{expiry}_{strike}"
    return key in notified


def mark_notified(strike, expiry):
    """标记已通知"""
    notified = load_notified()
    key = f"{expiry}_{strike}"
    notified[key] = get_beijing_time().isoformat()
    save_notified(notified)


# ==================== 核心逻辑 ====================
def get_tqqq_price():
    """获取TQQQ当前价格"""
    ticker = yf.Ticker("TQQQ")
    df = ticker.history(period="1d")
    return df['Close'].iloc[-1] if len(df) > 0 else None


def get_options_chain():
    """获取期权链"""
    ticker = yf.Ticker("TQQQ")
    
    # 尝试获取多个到期日
    today = datetime.now()
    days_until_friday = (4 - today.weekday() + 7) % 7
    expirations = [
        (today + timedelta(days=days_until_friday + 7)).strftime("%Y-%m-%d"),   # 下周五
        (today + timedelta(days=days_until_friday + 14)).strftime("%Y-%m-%d"), # 再下周
        (today + timedelta(days=days_until_friday)).strftime("%Y-%m-%d"),      # 本周五
    ]
    
    for expiry in expirations:
        try:
            chain = ticker.option_chain(expiry)
            puts = chain.puts
            if puts is not None and len(puts) > 0:
                return puts.to_dict('records'), expiry
        except:
            continue
    
    return None, None


def filter_sp_options(puts, current_price):
    """筛选符合SP策略的期权"""
    if not puts:
        return []
    
    strike_threshold = current_price * (1 - config.STRIKE_DISCOUNT)
    
    filtered = []
    for p in puts:
        strike = p.get('strike', 0)
        bid = p.get('bid', 0)
        ask = p.get('ask', 0)
        
        if strike <= 0 or bid <= 0:
            continue
        
        premium = (bid + ask) / 2
        
        # 筛选条件
        if strike >= strike_threshold:
            continue
        if premium < 30 or premium > 50:
            continue
        
        filtered.append({
            'strike': strike,
            'premium': premium,
            'bid': bid,
            'ask': ask,
            'iv': p.get('impliedVolatility', 0),
            'delta': p.get('delta', 0),
            'distance_pct': (current_price - strike) / current_price * 100,
        })
    
    filtered.sort(key=lambda x: x['premium'], reverse=True)
    return filtered


def check_and_notify():
    """检查并通知"""
    print(f"\n[{get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')} 北京时间] 检查期权机会...")
    
    # 检查是否在交易时间
    if not is_us_market_open():
        print("❌ 非美股交易时间，跳过")
        return
    
    print("✅ 美股交易时间，获取数据...")
    
    # 获取数据
    price = get_tqqq_price()
    if not price:
        print("❌ 获取价格失败")
        return
    
    puts, expiry = get_options_chain()
    if not puts or not expiry:
        print("❌ 获取期权数据失败")
        return
    
    # 筛选
    filtered = filter_sp_options(puts, price)
    if not filtered:
        print("⚠️ 没有符合条件的机会")
        return
    
    # 找到最佳推荐
    top = filtered[0]
    
    # 检查是否已通知
    if is_already_notified(top['strike'], expiry):
        print(f"⏭️ 已通知过 {expiry} $${top['strike']}，跳过")
        return
    
    # 发送通知
    message = f"""
🔥 **TQQQ 期权机会**

📅 到期日: {expiry}
💰 当前价格: ${price:.2f}
🎯 推荐行权价: ${top['strike']:.2f}
💵 权利金: ${top['premium']:.2f}
📊 距离现价: {top['distance_pct']:.1f}%
⚠️ 风险提示: 可能被行权
"""
    
    print(message)
    
    # 发送通知
    feishu_ok = send_feishu(message)
    wechat_ok = send_wechat(message)
    
    if feishu_ok or wechat_ok:
        mark_notified(top['strike'], expiry)
        print("✅ 通知已发送")
    else:
        print("⚠️ 通知发送失败（请配置 Webhook）")


# ==================== 主循环 ====================
def main():
    print("=" * 50)
    print("🚀 TQQQ SP 策略监控服务启动")
    print(f"⏰ 美股交易时间: 9:30-16:00 ET (北京时间 21:30-次日 4:00)")
    print(f"🔄 检查间隔: {CHECK_INTERVAL // 60} 分钟")
    print("=" * 50)
    
    while True:
        try:
            check_and_notify()
        except Exception as e:
            print(f"❌ 错误: {e}")
        
        # 等待下次检查
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
