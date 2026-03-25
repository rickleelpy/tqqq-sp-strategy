"""
TQQQ 期权 SP 策略 Dashboard V2
实时网页界面，每5分钟自动刷新
- 持仓管理（添加/平仓）
- 风险维度评估
- 收益统计
- 升级版期权池
"""

import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import pytz

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="🦐 TQQQ SP 策略池 V2",
    page_icon="🦐",
    layout="wide"
)

# ==================== 样式 ====================
st.markdown("""
<style>
    .stApp { background-color: #0e1117 }
    .price-up { color: #4ade80; }
    .price-down { color: #f87171; }
    .stButton>button { width: 100%; }
    .stForm { background-color: #1e2130; padding: 15px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)


# ==================== 配置参数 ====================
CAPITAL = 100000           # 总购买力 ($)
MARGIN_PER_LOT = 10000    # 每张占用购买力 ($)
TOTAL_LOTS = CAPITAL // MARGIN_PER_LOT  # 总仓位上限


# ==================== 状态初始化 ====================
if 'positions' not in st.session_state:
    st.session_state.positions = []

if 'closed_positions' not in st.session_state:
    st.session_state.closed_positions = []  # 平仓记录

if 'portfolio_stats' not in st.session_state:
    st.session_state.portfolio_stats = {
        'total_delta': 0,
        'total_gamma': 0,
        'total_theta': 0,
        'total_vega': 0,
        'total_premium': 0,
        'max_risk': 0,
    }


# ==================== 工具函数 ====================
def is_us_market_open():
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    if now_et.weekday() >= 5:
        return False
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now_et <= market_close


def get_beijing_time():
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(beijing_tz)


def get_next_friday():
    today = datetime.now()
    days_until_this_friday = (4 - today.weekday() + 7) % 7
    next_friday = today + timedelta(days=days_until_this_friday + 7)
    return next_friday.strftime("%Y-%m-%d")


# ==================== 持仓管理函数 ====================
def add_position(strike, premium, quantity, expiry):
    position = {
        'id': len(st.session_state.positions) + 1,
        'strike': strike,
        'premium': premium,
        'quantity': quantity,
        'expiry': expiry,
        'open_date': datetime.now().strftime("%Y-%m-%d"),
        'contract_size': 100,
    }
    st.session_state.positions.append(position)
    _recalc_portfolio()


def close_position(pos_id, close_price, close_date=None):
    """平仓"""
    positions = st.session_state.positions
    pos = next((p for p in positions if p['id'] == pos_id), None)
    if not pos:
        return False
    
    # 计算平仓盈亏
    # 盈利 = 收取的权利金 - 平仓成本（买回期权花费）
    pnl = (pos['premium'] - close_price) * pos['quantity'] * pos['contract_size']
    
    closed = {
        'id': pos['id'],
        'strike': pos['strike'],
        'premium': pos['premium'],
        'quantity': pos['quantity'],
        'expiry': pos['expiry'],
        'open_date': pos['open_date'],
        'close_date': close_date or datetime.now().strftime("%Y-%m-%d"),
        'close_price': close_price,
        'pnl': pnl,
    }
    
    st.session_state.closed_positions.append(closed)
    st.session_state.positions = [p for p in positions if p['id'] != pos_id]
    _recalc_portfolio()
    return True


def remove_position(pos_id):
    st.session_state.positions = [p for p in st.session_state.positions if p['id'] != pos_id]
    _recalc_portfolio()


def _recalc_portfolio():
    positions = st.session_state.positions
    if not positions:
        st.session_state.portfolio_stats = {
            'total_delta': 0,
            'total_gamma': 0,
            'total_theta': 0,
            'total_vega': 0,
            'total_premium': 0,
            'max_risk': 0,
            'used_lots': 0,
            'remaining_lots': TOTAL_LOTS,
        }
        return
    
    total_premium = sum(p['premium'] * p['quantity'] * p['contract_size'] for p in positions)
    total_delta = sum(-0.25 * p['quantity'] for p in positions)
    total_gamma = 0.02 * sum(p['quantity'] for p in positions)
    total_theta = 5 * sum(p['quantity'] for p in positions)
    total_vega = 10 * sum(p['quantity'] for p in positions)
    max_risk = sum(p['strike'] * p['quantity'] * p['contract_size'] for p in positions) - total_premium
    
    # 计算已用仓位
    used_lots = sum(p['quantity'] for p in positions)
    
    st.session_state.portfolio_stats = {
        'total_delta': total_delta,
        'total_gamma': total_gamma,
        'total_theta': total_theta,
        'total_vega': total_vega,
        'total_premium': total_premium,
        'max_risk': max_risk,
        'used_lots': used_lots,
        'remaining_lots': TOTAL_LOTS - used_lots,
    }


def calculate_returns():
    """计算收益统计"""
    closed = st.session_state.closed_positions
    if not closed:
        return {'week': 0, 'month': 0, 'year': 0, 'total': 0, 
                'week_pct': 0, 'month_pct': 0, 'year_pct': 0, 'total_pct': 0}
    
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    year_ago = now - timedelta(days=365)
    
    week_pnl = sum(c['pnl'] for c in closed if datetime.strptime(c['close_date'], "%Y-%m-%d") >= week_ago)
    month_pnl = sum(c['pnl'] for c in closed if datetime.strptime(c['close_date'], "%Y-%m-%d") >= month_ago)
    year_pnl = sum(c['pnl'] for c in closed if datetime.strptime(c['close_date'], "%Y-%m-%d") >= year_ago)
    total_pnl = sum(c['pnl'] for c in closed)
    
    # 收益率（基于总购买力）
    week_pct = (week_pnl / CAPITAL * 100) if CAPITAL > 0 else 0
    month_pct = (month_pnl / CAPITAL * 100) if CAPITAL > 0 else 0
    year_pct = (year_pnl / CAPITAL * 100) if CAPITAL > 0 else 0
    total_pct = (total_pnl / CAPITAL * 100) if CAPITAL > 0 else 0
    
    return {
        'week': week_pnl, 'month': month_pnl, 'year': year_pnl, 'total': total_pnl,
        'week_pct': week_pct, 'month_pct': month_pct, 'year_pct': year_pct, 'total_pct': total_pct
    }


# ==================== 数据获取 ====================
@st.cache_data(ttl=300)
def get_tqqq_price():
    ticker = yf.Ticker("TQQQ")
    df = ticker.history(period="1d")
    return df['Close'].iloc[-1] if len(df) > 0 else 0


@st.cache_data(ttl=300)
def get_options_chain(expiry):
    ticker = yf.Ticker("TQQQ")
    try:
        chain = ticker.option_chain(expiry)
        puts = chain.puts
        if puts is None or len(puts) == 0:
            return None
        return puts.to_dict('records')
    except:
        return None


# ==================== 主界面 ====================
st.title("🦐 TQQQ 期权 SP 策略池 V2")

# 侧边栏
with st.sidebar:
    st.header("⚙️ 参数配置")
    
    # 筛选参数
    st.subheader("筛选参数")
    strike_discount = st.slider("行权价低于现价", 5, 30, 15, step=5) / 100
    min_premium = st.number_input("最小权利金 ($)", value=30)
    max_premium = st.number_input("最大权利金 ($)", value=100)
    
    st.divider()
    
    # 添加持仓
    st.header("📝 添加持仓")
    with st.form("add_position_form"):
        pos_strike = st.number_input("行权价 ($)", min_value=0.0, value=150.0, step=1.0)
        pos_premium = st.number_input("权利金 ($)", min_value=0.0, value=45.0, step=5.0)
        pos_quantity = st.number_input("张数", min_value=1, value=1, step=1)
        pos_expiry = st.text_input("到期日", value=get_next_friday())
        submitted = st.form_submit_button("➕ 添加持仓")
        
        if submitted:
            add_position(pos_strike, pos_premium, pos_quantity, pos_expiry)
            st.success(f"已添加: {pos_quantity}张 ${pos_strike} Put")
            st.rerun()
    
    st.divider()
    
    # 平仓
    st.header("🔴 平仓")
    with st.form("close_position_form"):
        close_id = st.number_input("平仓ID", min_value=1, value=1, step=1)
        close_price = st.number_input("平仓价格 ($)", min_value=0.0, value=10.0, step=5.0)
        close_btn = st.form_submit_button("🔴 确认平仓")
        
        if close_btn:
            if close_position(close_id, close_price):
                st.success(f"ID {close_id} 已平仓")
                st.rerun()
            else:
                st.error("找不到该持仓ID")
    
    st.divider()
    
    # 市场状态
    market_open = is_us_market_open()
    refresh_interval = 900 if market_open else 300
    st.write("🕐", get_beijing_time().strftime("%Y-%m-%d %H:%M:%S"))
    st.write(f"{'🔥' if market_open else '💤'} 美股: {'开市' if market_open else '闭市'}")
    
    if st.button("🔄 刷新数据"):
        st.cache_data.clear()
        st.rerun()


# ==================== 顶部指标 ====================
price = get_tqqq_price()
stats = st.session_state.portfolio_stats

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("TQQQ", f"${price:.2f}")

with col2:
    st.metric("持仓数", f"{len(st.session_state.positions)} 张")

with col3:
    st.metric("总权利金", f"${stats['total_premium']:,.0f}")

with col4:
    st.metric("最大风险", f"${stats['max_risk']:,.0f}")


# ==================== 第一行：持仓跟踪 + 风险面板 ====================
col_pos, col_risk = st.columns([3, 2])

with col_pos:
    st.subheader("📋 持仓跟踪")
    
    if st.session_state.positions:
        pos_data = []
        for p in st.session_state.positions:
            pos_data.append({
                'ID': p['id'],
                '行权价': f"${p['strike']:.2f}",
                '权利金': f"${p['premium']:.2f}",
                '张数': p['quantity'],
                '到期日': p['expiry'],
                '开仓日': p['open_date'],
                '已收权利金': f"${p['premium'] * p['quantity'] * 100:,.0f}",
            })
        
        df_pos = pd.DataFrame(pos_data)
        st.dataframe(df_pos, use_container_width=True, hide_index=True)
    else:
        st.info("暂无持仓")

with col_risk:
    st.subheader("⚠️ 风险面板")
    
    # Delta
    delta = stats['total_delta']
    delta_pct = abs(delta) / CAPITAL * 100 if CAPITAL > 0 else 0
    delta_level = "🔴" if delta_pct > 20 else "🟡" if delta_pct > 10 else "🟢"
    st.metric(f"{delta_level} Delta", f"{delta:.2f}")
    
    # Theta
    theta = stats['total_theta']
    st.metric(f"📈 Theta", f"${theta:.2f}/天")
    
    # 最大风险
    max_risk = stats['max_risk']
    risk_pct = max_risk / CAPITAL * 100 if CAPITAL > 0 else 0
    st.metric("⚠️ 最大风险", f"${max_risk:,.0f} ({risk_pct:.1f}%)")


# ==================== 第二行：购买力 + 收益统计 ====================
col_power, col_returns = st.columns([1, 2])

with col_power:
    st.subheader("💰 购买力")
    used = stats['used_lots']
    remaining = stats['remaining_lots']
    st.metric("已用仓位", f"{used} 张")
    st.metric("剩余仓位", f"{remaining} 张")
    st.progress(used / TOTAL_LOTS if TOTAL_LOTS > 0 else 0, text=f"已用 {used}/{TOTAL_LOTS}")
    st.caption(f"总购买力: ${CAPITAL:,} | 每张占用: ${MARGIN_PER_LOT:,}")

with col_returns:
    st.subheader("📈 收益统计")
    returns = calculate_returns()
    
    # 四列：本周、本月、本年、累计
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        pnl = returns['week']
        color = "↑" if pnl > 0 else "↓" if pnl < 0 else ""
        st.metric(f"本周 {color}", f"${pnl:,.0f}", f"{returns['week_pct']:.1f}%")
    with c2:
        pnl = returns['month']
        color = "↑" if pnl > 0 else "↓" if pnl < 0 else ""
        st.metric(f"本月 {color}", f"${pnl:,.0f}", f"{returns['month_pct']:.1f}%")
    with c3:
        pnl = returns['year']
        color = "↑" if pnl > 0 else "↓" if pnl < 0 else ""
        st.metric(f"本年 {color}", f"${pnl:,.0f}", f"{returns['year_pct']:.1f}%")
    with c4:
        pnl = returns['total']
        color = "↑" if pnl > 0 else "↓" if pnl < 0 else ""
        st.metric(f"累计 {color}", f"${pnl:,.0f}", f"{returns['total_pct']:.1f}%")


# ==================== 第三行：期权池 ====================
st.divider()
st.subheader("📊 期权池")

expiry = get_next_friday()
puts = get_options_chain(expiry)

if puts:
    strike_threshold = price * (1 - strike_discount)
    
    filtered = []
    for p in puts:
        strike = p.get('strike', 0)
        bid = p.get('bid', 0)
        ask = p.get('ask', 0)
        
        if strike <= 0 or bid <= 0:
            continue
        
        premium = (bid + ask) / 2
        if strike >= strike_threshold:
            continue
        if premium < min_premium or premium > max_premium:
            continue
        
        filtered.append({
            'strike': strike,
            'premium': premium,
            'bid': bid,
            'ask': ask,
            'iv': p.get('impliedVolatility', 0),
            'delta': p.get('delta', -0.2),
            'theta': p.get('theta', 3),
            'distance_pct': (price - strike) / price * 100,
        })
    
    # 排序
    sort_by = st.radio("排序", ['权利金', 'Delta', 'IV'], horizontal=True)
    if sort_by == '权利金':
        filtered.sort(key=lambda x: x['premium'], reverse=True)
    elif sort_by == 'Delta':
        filtered.sort(key=lambda x: abs(x['delta']), reverse=True)
    else:
        filtered.sort(key=lambda x: x['iv'], reverse=True)
    
    if filtered:
        df_opts = pd.DataFrame(filtered)
        df_opts['权利金'] = df_opts['premium'].apply(lambda x: f"${x:.2f}")
        df_opts['行权价'] = df_opts['strike'].apply(lambda x: f"${x:.2f}")
        df_opts['距离'] = df_opts['distance_pct'].apply(lambda x: f"{x:.1f}%")
        df_opts['IV'] = df_opts['iv'].apply(lambda x: f"{x:.1%}")
        df_opts['Delta'] = df_opts['delta'].apply(lambda x: f"{x:.3f}")
        
        display_cols = ['行权价', '权利金', '距离', 'IV', 'Delta']
        st.dataframe(df_opts[display_cols], use_container_width=True, hide_index=True)
        
        # 最佳推荐
        st.subheader("🎯 最佳推荐")
        top = filtered[0]
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("行权价", f"${top['strike']:.2f}")
        with c2: st.metric("权利金", f"${top['premium']:.2f}")
        with c3: st.metric("距离", f"{top['distance_pct']:.1f}%")
        with c4: st.metric("Delta", f"{top['delta']:.3f}")
    else:
        st.warning(f"暂无符合条件期权")
else:
    st.error("无法获取期权数据")


# ==================== 底部 ====================
st.markdown("---")
st.caption(f"自动刷新: {refresh_interval//60}分钟 | {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}")
