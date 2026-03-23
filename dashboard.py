"""
TQQQ 期权 SP 策略 Dashboard
实时网页界面，每5分钟自动刷新
"""

import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import time
import pytz
import config

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="🦐 TQQQ SP 策略池",
    page_icon="🦐",
    layout="wide"
)

# ==================== 样式 ====================
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117
    }
    .metric-card {
        background-color: #1e2130;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .price-up {
        color: #4ade80;
    }
    .price-down {
        color: #f87171;
    }
</style>
""", unsafe_allow_html=True)


# ==================== 工具函数 ====================
def is_us_market_open():
    """检查美股是否在交易时间（9:30-16:00 ET）"""
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    
    # 检查是否在交易时间内（周一到周五，9:30-16:00）
    if now_et.weekday() >= 5:  # 周六周日
        return False
    
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    
    return market_open <= now_et <= market_close


def get_beijing_time():
    """获取北京时间"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(beijing_tz)


# ==================== 数据获取 ====================
@st.cache_data(ttl=300)  # 缓存5分钟
def get_tqqq_price():
    """获取TQQQ当前价格"""
    ticker = yf.Ticker("TQQQ")
    df = ticker.history(period="1d")
    return df['Close'].iloc[-1] if len(df) > 0 else 0


@st.cache_data(ttl=300)
def get_options_chain():
    """获取期权链"""
    ticker = yf.Ticker("TQQQ")
    
    # 只获取下周五（不是本周五）
    today = datetime.now()
    days_until_this_friday = (4 - today.weekday() + 7) % 7
    next_friday = today + timedelta(days=days_until_this_friday + 7)
    expiry = next_friday.strftime("%Y-%m-%d")
    
    try:
        chain = ticker.option_chain(expiry)
        puts = chain.puts
        if puts is None or len(puts) == 0:
            return None, expiry
        return puts.to_dict('records'), expiry
    except:
        return None, expiry


def filter_sp_options(puts, current_price):
    """筛选符合SP策略的期权"""
    if not puts:
        return []
    
    # 行权价门槛：低于现价20%
    strike_threshold = current_price * (1 - config.STRIKE_DISCOUNT)
    
    filtered = []
    for p in puts:
        strike = p.get('strike', 0)
        bid = p.get('bid', 0)
        ask = p.get('ask', 0)
        iv = p.get('impliedVolatility', 0)
        oi = p.get('openInterest', 0)
        
        if strike <= 0 or bid <= 0:
            continue
        
        premium = (bid + ask) / 2
        
        # 筛选条件
        if strike >= strike_threshold:
            continue
        
        if premium < 20 or premium > 100:  # 放宽一点范围
            continue
        
        # 筛选权利金30-50区间
        if premium < 30 or premium > 50:
            continue
        
        filtered.append({
            'strike': strike,
            'premium': premium,
            'bid': bid,
            'ask': ask,
            'iv': iv,
            'oi': oi,
            'delta': p.get('delta', 0),
            'theta': p.get('theta', 0),
            'distance_pct': (current_price - strike) / current_price * 100,
        })
    
    # 按权利金排序
    filtered.sort(key=lambda x: x['premium'], reverse=True)
    return filtered


# ==================== 主界面 ====================
st.title("🦐 TQQQ 期权 SP 策略池")

# 侧边栏 - 参数
with st.sidebar:
    st.header("⚙️ 策略参数")
    st.write(f"**资金:** ${config.CAPITAL:,}")
    st.write(f"**每周最大亏损:** ${config.MAX_WEEKLY_LOSS_AMOUNT:,.0f} (5%)")
    st.write(f"**行权价门槛:** 低于现价 {config.STRIKE_DISCOUNT*100:.0f}%")
    st.write(f"**权利金区间:** $30 - $50")
    st.write(f"**目标到期:** 下周五")
    
    st.divider()
    # 判断是否在美股交易时间
    market_open = is_us_market_open()
    refresh_interval = 900 if market_open else 300  # 交易时间15分钟，非交易时间5分钟
    
    st.write("🕐 最后更新 (北京时间):", get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"))
    st.write(f"{'🔥' if market_open else '💤'} 美股交易时间: {'是' if market_open else '否'} (刷新间隔: {refresh_interval//60}分钟)")
    
    # 刷新按钮
    if st.button("🔄 立即刷新"):
        st.cache_data.clear()
        st.rerun()

# ==================== 顶部指标 ====================
col1, col2, col3 = st.columns(3)

with col1:
    try:
        price = get_tqqq_price()
        change = price - (price * 0.02)  # 假设2%
        color = "price-up" if change > 0 else "price-down"
        st.metric("TQQQ 当前价格", f"${price:.2f}", f"{change:.2f}")
    except:
        st.metric("TQQQ 当前价格", "获取失败")

with col2:
    puts, expiry = get_options_chain()
    if puts:
        st.metric("下周五到期", expiry)
    else:
        st.metric("下周五到期", "无数据")

with col3:
    if puts:
        filtered = filter_sp_options(puts, price)
        st.metric("符合条件期权", f"{len(filtered)} 个")

# ==================== 期权池 ====================
st.divider()
st.subheader(f"📊 期权池 (下周五 {expiry} 到期)")

if puts and filtered:
    # 创建表格
    df = pd.DataFrame(filtered)
    
    # 格式化显示
    df['权利金'] = df['premium'].apply(lambda x: f"${x:.2f}")
    df['行权价'] = df['strike'].apply(lambda x: f"${x:.2f}")
    df['距离'] = df['distance_pct'].apply(lambda x: f"{x:.1f}%")
    df['IV'] = df['iv'].apply(lambda x: f"{x:.1%}")
    df['Delta'] = df['delta'].apply(lambda x: f"{x:.3f}")
    df['Theta'] = df['theta'].apply(lambda x: f"{x:.3f}")
    df['OI'] = df['oi'].apply(lambda x: f"{int(x):,}")
    
    # 选择显示列
    display_cols = ['行权价', '权利金', '距离', 'IV', 'Delta', 'Theta', 'OI']
    st.dataframe(
        df[display_cols],
        use_container_width=True,
        hide_index=True
    )
    
    # 最佳推荐
    st.subheader("🎯 最佳推荐")
    top = filtered[0]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("行权价", f"${top['strike']:.2f}")
    with col2:
        st.metric("权利金", f"${top['premium']:.2f}")
    with col3:
        st.metric("距离现价", f"{top['distance_pct']:.1f}%")
    with col4:
        st.metric("Delta", f"{top['delta']:.3f}")
    
    # 操作建议
    st.info(f"""
    📝 **操作建议**
    
    卖出 TQQQ ${top['strike']:.2f} Put，下周五 {expiry} 到期
    - 收取权利金: **${top['premium']:.2f}**
    - 如被行权成本: ${top['strike']:.2f}
    - 最大风险: ${top['strike'] - top['premium']:.2f}
    """)
    
elif puts:
    st.warning("当前没有符合条件（权利金 $30-50）的期权，等待机会")
else:
    st.error("无法获取期权数据")

# ==================== 自动刷新 ====================
st.markdown("---")
st.markdown(f"*📌 自动刷新 | 最后更新 (北京时间): {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}*")

# 动态刷新间隔
refresh_interval = 900 if is_us_market_open() else 300
st.markdown(f"<meta http-equiv=\"refresh\" content=\"{refresh_interval}\">", unsafe_allow_html=True)

# ==================== 通知说明 ====================
st.markdown("---")
st.info("📲 **通知功能**：Streamlit Cloud 无法主动推送通知。如需微信/飞书通知，需部署独立监控服务。")
