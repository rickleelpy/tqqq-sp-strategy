"""
TQQQ 期权 SP 策略池 Dashboard V2
实时网页界面，每5分钟自动刷新
- 持仓管理（添加/平仓）
- 可选期权池（核心功能）
- 风险维度评估
- 收益统计
"""

import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import pytz

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="🦐 TQQQ SP 策略池",
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
</style>
""", unsafe_allow_html=True)


# ==================== 配置参数 ====================
CAPITAL = 100000           # 总购买力 ($)
MARGIN_PER_LOT = 10000    # 每张占用购买力 ($)
TOTAL_LOTS = CAPITAL // MARGIN_PER_LOT  # 10张


# ==================== 状态初始化 ====================
if 'positions' not in st.session_state:
    st.session_state.positions = []

if 'closed_positions' not in st.session_state:
    st.session_state.closed_positions = []

if 'portfolio_stats' not in st.session_state:
    st.session_state.portfolio_stats = {}


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
    days_until_friday = (4 - today.weekday() + 7) % 7
    next_friday = today + timedelta(days=days_until_friday + 7)
    return next_friday.strftime("%Y-%m-%d")


def get_this_friday():
    today = datetime.now()
    days_until_friday = (4 - today.weekday() + 7) % 7
    return (today + timedelta(days=days_until_friday)).strftime("%Y-%m-%d")


# ==================== 持仓管理 ====================
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


def close_position(pos_id, close_price):
    positions = st.session_state.positions
    pos = next((p for p in positions if p['id'] == pos_id), None)
    if not pos:
        return False
    
    pnl = (pos['premium'] - close_price) * pos['quantity'] * pos['contract_size']
    
    closed = {
        'id': pos['id'],
        'strike': pos['strike'],
        'premium': pos['premium'],
        'quantity': pos['quantity'],
        'expiry': pos['expiry'],
        'open_date': pos['open_date'],
        'close_date': datetime.now().strftime("%Y-%m-%d"),
        'close_price': close_price,
        'pnl': pnl,
    }
    
    st.session_state.closed_positions.append(closed)
    st.session_state.positions = [p for p in positions if p['id'] != pos_id]
    _recalc_portfolio()
    return True


def _recalc_portfolio():
    positions = st.session_state.positions
    if not positions:
        st.session_state.portfolio_stats = {
            'total_premium': 0, 'max_risk': 0, 'used_lots': 0, 'remaining_lots': TOTAL_LOTS,
        }
        return
    
    total_premium = sum(p['premium'] * p['quantity'] * 100 for p in positions)
    max_risk = sum(p['strike'] * p['quantity'] * 100 for p in positions) - total_premium
    used_lots = sum(p['quantity'] for p in positions)
    
    st.session_state.portfolio_stats = {
        'total_premium': total_premium,
        'max_risk': max_risk,
        'used_lots': used_lots,
        'remaining_lots': TOTAL_LOTS - used_lots,
    }


def calculate_returns():
    closed = st.session_state.closed_positions
    if not closed:
        return {'week': 0, 'month': 0, 'year': 0, 'total': 0, 'week_pct': 0, 'month_pct': 0, 'year_pct': 0, 'total_pct': 0}
    
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    year_ago = now - timedelta(days=365)
    
    week_pnl = sum(c['pnl'] for c in closed if datetime.strptime(c['close_date'], "%Y-%m-%d") >= week_ago)
    month_pnl = sum(c['pnl'] for c in closed if datetime.strptime(c['close_date'], "%Y-%m-%d") >= month_ago)
    year_pnl = sum(c['pnl'] for c in closed if datetime.strptime(c['close_date'], "%Y-%m-%d") >= year_ago)
    total_pnl = sum(c['pnl'] for c in closed)
    
    return {
        'week': week_pnl, 'month': month_pnl, 'year': year_pnl, 'total': total_pnl,
        'week_pct': week_pnl / CAPITAL * 100 if CAPITAL > 0 else 0,
        'month_pct': month_pnl / CAPITAL * 100 if CAPITAL > 0 else 0,
        'year_pct': year_pnl / CAPITAL * 100 if CAPITAL > 0 else 0,
        'total_pct': total_pnl / CAPITAL * 100 if CAPITAL > 0 else 0,
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
        return puts.to_dict('records') if puts is not None and len(puts) > 0 else None
    except:
        return None


# ==================== 主界面 ====================
st.title("🦐 TQQQ SP 策略池")

# 侧边栏
with st.sidebar:
    st.header("⚙️ 参数配置")
    
    # 筛选参数
    st.subheader("筛选参数")
    strike_discount = st.slider("行权价低于现价", 5, 30, 15, step=5) / 100
    min_premium = st.number_input("最小权利金 ($)", value=30)
    max_premium = st.number_input("最大权利金 ($)", value=100)
    
    # 到期日选择
    expiry_option = st.selectbox("到期日", ["下周五", "本周五"], index=0)
    target_expiry = get_next_friday() if expiry_option == "下周五" else get_this_friday()
    
    st.divider()
    
    # 添加持仓
    st.header("📝 开仓")
    with st.form("add_position_form"):
        pos_strike = st.number_input("行权价 ($)", min_value=0.0, value=150.0, step=1.0)
        pos_premium = st.number_input("权利金 ($)", min_value=0.0, value=45.0, step=5.0)
        pos_quantity = st.number_input("张数", min_value=1, value=1, step=1)
        submitted = st.form_submit_button("➕ 确认开仓")
        
        if submitted:
            add_position(pos_strike, pos_premium, pos_quantity, target_expiry)
            st.success(f"已开仓: {pos_quantity}张 ${pos_strike} Put")
            st.rerun()
    
    st.divider()
    
    # 平仓
    st.header("🔴 平仓")
    
    # 平仓选择器
    if st.session_state.positions:
        position_options = {f"ID {p['id']}: ${p['strike']} Put @ ${p['premium']} ({p['expiry']})": p['id'] for p in st.session_state.positions}
        selected_pos = st.selectbox("选择持仓", list(position_options.keys()))
        pos_id = position_options[selected_pos]
    else:
        st.info("暂无持仓")
        pos_id = None
    
    if pos_id:
        with st.form("close_position_form"):
            close_price = st.number_input("平仓价格 ($)", min_value=0.0, value=10.0, step=5.0)
            close_btn = st.form_submit_button("🔴 确认平仓")
            
            if close_btn:
                if close_position(pos_id, close_price):
                    st.success(f"已平仓")
                    st.rerun()
                else:
                    st.error("平仓失败")
    
    st.divider()
    
    # 市场状态
    market_open = is_us_market_open()
    st.write("🕐", get_beijing_time().strftime("%H:%M:%S"))
    st.write(f"{'🔥' if market_open else '💤'} 美股: {'开市' if market_open else '闭市'}")
    
    if st.button("🔄 刷新"):
        st.cache_data.clear()
        st.rerun()


# ==================== 顶部指标 ====================
price = get_tqqq_price()
stats = st.session_state.portfolio_stats

col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("TQQQ", f"${price:.2f}")
with col2: st.metric("持仓", f"{len(st.session_state.positions)} 张")
with col3: st.metric("权利金", f"${stats.get('total_premium', 0):,.0f}")
with col4: st.metric("最大风险", f"${stats.get('max_risk', 0):,.0f}")


# ==================== 第一行：期权池（核心功能）====================
st.markdown("---")
st.subheader(f"📊 可选期权池 ({target_expiry} 到期)")

puts = get_options_chain(target_expiry)

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
            'oi': p.get('openInterest', 0),
            'distance_pct': (price - strike) / price * 100,
        })
    
    # 排序
    sort_by = st.radio("排序方式", ['权利金↑', '权利金↓', 'Delta', 'IV', '距离'], horizontal=True)
    if sort_by == '权利金↑':
        filtered.sort(key=lambda x: x['premium'])
    elif sort_by == '权利金↓':
        filtered.sort(key=lambda x: x['premium'], reverse=True)
    elif sort_by == 'Delta':
        filtered.sort(key=lambda x: abs(x['delta']), reverse=True)
    elif sort_by == 'IV':
        filtered.sort(key=lambda x: x['iv'], reverse=True)
    else:
        filtered.sort(key=lambda x: x['distance_pct'], reverse=True)
    
    if filtered:
        # 表格
        df = pd.DataFrame(filtered)
        df['权利金'] = df['premium'].apply(lambda x: f"${x:.2f}")
        df['行权价'] = df['strike'].apply(lambda x: f"${x:.2f}")
        df['距离'] = df['distance_pct'].apply(lambda x: f"{x:.1f}%")
        df['IV'] = df['iv'].apply(lambda x: f"{x:.1%}")
        df['Delta'] = df['delta'].apply(lambda x: f"{x:.3f}")
        df['OI'] = df['oi'].apply(lambda x: f"{int(x):,}")
        
        st.dataframe(df[['行权价', '权利金', '距离', 'IV', 'Delta', 'OI']], use_container_width=True, hide_index=True)
        
        # 最佳推荐
        top = filtered[0]
        st.subheader("🎯 最佳推荐")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.metric("行权价", f"${top['strike']:.2f}")
        with c2: st.metric("权利金", f"${top['premium']:.2f}")
        with c3: st.metric("距离", f"{top['distance_pct']:.1f}%")
        with c4: st.metric("IV", f"{top['iv']:.1%}")
        with c5: st.metric("Delta", f"{top['delta']:.3f}")
        
        # 开仓建议
        st.info(f"""
        📝 **操作建议**
        
        卖出 TQQQ ${top['strike']:.2f} Put，{target_expiry} 到期
        - 权利金: **${top['premium']:.2f}**/张
        - 如被行权成本: ${top['strike']:.2f}
        - 最大风险: ${top['strike'] - top['premium']:.2f}/张
        """)
    else:
        st.warning(f"暂无符合条件期权 (权利金 ${min_premium}-${max_premium})")
else:
    st.error("无法获取期权数据，请检查网络")


# ==================== 第二行：持仓 + 风险 + 购买力 ====================
st.markdown("---")
col_pos, col_risk, col_power = st.columns([2, 1, 1])

with col_pos:
    st.subheader("📋 持仓")
    if st.session_state.positions:
        pos_data = []
        for p in st.session_state.positions:
            pos_data.append({
                'ID': p['id'],
                '行权价': f"${p['strike']:.2f}",
                '权利金': f"${p['premium']:.2f}",
                '张数': p['quantity'],
                '到期': p['expiry'],
                '已收': f"${p['premium'] * p['quantity'] * 100:,.0f}",
            })
        st.dataframe(pd.DataFrame(pos_data), use_container_width=True, hide_index=True)
    else:
        st.info("暂无持仓")

with col_risk:
    st.subheader("⚠️ 风险")
    max_risk = stats.get('max_risk', 0)
    risk_pct = max_risk / CAPITAL * 100 if CAPITAL > 0 else 0
    st.metric("最大风险", f"${max_risk:,.0f}", f"{risk_pct:.1f}%")
    st.caption("全部被行权时的亏损")

with col_power:
    st.subheader("💰 购买力")
    used = stats.get('used_lots', 0)
    remaining = stats.get('remaining_lots', TOTAL_LOTS)
    st.metric("剩余", f"{remaining} 张")
    st.progress(used / TOTAL_LOTS, text=f"{used}/{TOTAL_LOTS}")
    st.caption(f"总购买力 ${CAPITAL:,}")


# ==================== 第三行：收益统计 ====================
st.subheader("📈 收益统计")
returns = calculate_returns()

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("本周", f"${returns['week']:,.0f}", f"{returns['week_pct']:.1f}%")
with c2: st.metric("本月", f"${returns['month']:,.0f}", f"{returns['month_pct']:.1f}%")
with c3: st.metric("本年", f"${returns['year']:,.0f}", f"{returns['year_pct']:.1f}%")
with c4: st.metric("累计", f"${returns['total']:,.0f}", f"{returns['total_pct']:.1f}%")


# ==================== 底部 ====================
st.markdown("---")
st.caption(f"刷新间隔: {'15' if is_us_market_open() else '5'}分钟 | {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}")
