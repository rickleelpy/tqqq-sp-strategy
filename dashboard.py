"""
TQQQ 期权 SP 策略 Dashboard V2
实时网页界面，每5分钟自动刷新
- 持仓管理
- 风险维度评估
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
    .stApp {
        background-color: #0e1117
    }
    .metric-card {
        background-color: #1e2130;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .price-up { color: #4ade80; }
    .price-down { color: #f87171; }
    .risk-high { color: #f87171; font-weight: bold; }
    .risk-medium { color: #fbbf24; font-weight: bold; }
    .risk-low { color: #4ade80; font-weight: bold; }
    .stButton>button { width: 100%; }
</style>
""", unsafe_allow_html=True)


# ==================== 状态初始化 ====================
if 'positions' not in st.session_state:
    st.session_state.positions = []

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
    """检查美股是否在交易时间（9:30-16:00 ET）"""
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)
    if now_et.weekday() >= 5:
        return False
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now_et <= market_close


def get_beijing_time():
    """获取北京时间"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(beijing_tz)


def calculate_position_greeks(put_data, current_price):
    """计算单个期权的希腊字母"""
    strike = put_data.get('strike', 0)
    premium = put_data.get('premium', 0)
    delta = put_data.get('delta', 0)
    gamma = put_data.get('gamma', 0)
    theta = put_data.get('theta', 0)
    vega = put_data.get('vega', 0)
    
    # 简化：如果没有提供 delta，根据虚值程度估算
    if delta == 0 and strike > 0 and current_price > 0:
        moneyness = strike / current_price
        if moneyness < 0.9:
            delta = -0.2
        elif moneyness < 0.85:
            delta = -0.15
        else:
            delta = -0.3
    
    return {
        'delta': delta,
        'gamma': gamma if gamma else 0.02,
        'theta': theta if theta else 3,
        'vega': vega if vega else 10,
    }


# ==================== 数据获取 ====================
@st.cache_data(ttl=300)
def get_tqqq_price():
    """获取TQQQ当前价格"""
    ticker = yf.Ticker("TQQQ")
    df = ticker.history(period="1d")
    return df['Close'].iloc[-1] if len(df) > 0 else 0


@st.cache_data(ttl=300)
def get_options_chain(expiry):
    """获取期权链"""
    ticker = yf.Ticker("TQQQ")
    try:
        chain = ticker.option_chain(expiry)
        puts = chain.puts
        if puts is None or len(puts) == 0:
            return None
        return puts.to_dict('records')
    except:
        return None


def get_next_friday():
    """获取下周五日期"""
    today = datetime.now()
    days_until_this_friday = (4 - today.weekday() + 7) % 7
    next_friday = today + timedelta(days=days_until_this_friday + 7)
    return next_friday.strftime("%Y-%m-%d")


# ==================== 持仓管理函数 ====================
def add_position(strike, premium, quantity, expiry):
    """添加一个新持仓"""
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


def remove_position(pos_id):
    """删除持仓"""
    st.session_state.positions = [p for p in st.session_state.positions if p['id'] != pos_id]
    _recalc_portfolio()


def _recalc_portfolio():
    """重新计算组合统计"""
    positions = st.session_state.positions
    if not positions:
        st.session_state.portfolio_stats = {
            'total_delta': 0,
            'total_gamma': 0,
            'total_theta': 0,
            'total_vega': 0,
            'total_premium': 0,
            'max_risk': 0,
        }
        return
    
    # 计算总权利金
    total_premium = sum(p['premium'] * p['quantity'] * p['contract_size'] for p in positions)
    
    # 简化希腊字母计算
    # Delta: 义务仓是负数
    total_delta = sum(-0.25 * p['quantity'] for p in positions)
    total_gamma = 0.02 * sum(p['quantity'] for p in positions)
    total_theta = 5 * sum(p['quantity'] for p in positions)
    total_vega = 10 * sum(p['quantity'] for p in positions)
    
    # 最大风险：所有仓位被行权
    max_risk = sum(p['strike'] * p['quantity'] * p['contract_size'] for p in positions) - total_premium
    
    st.session_state.portfolio_stats = {
        'total_delta': total_delta,
        'total_gamma': total_gamma,
        'total_theta': total_theta,
        'total_vega': total_vega,
        'total_premium': total_premium,
        'max_risk': max_risk,
    }


# ==================== 主界面 ====================
st.title("🦐 TQQQ 期权 SP 策略池 V2")

# 侧边栏 - 参数配置
with st.sidebar:
    st.header("⚙️ 参数配置")
    
    # 筛选参数
    st.subheader("筛选参数")
    strike_discount = st.slider("行权价低于现价", 5, 30, 15, step=5) / 100
    min_premium = st.number_input("最小权利金 ($)", value=30)
    max_premium = st.number_input("最大权利金 ($)", value=100)
    
    st.divider()
    
    # 持仓输入
    st.header("📝 添加持仓")
    with st.form("add_position_form"):
        pos_strike = st.number_input("行权价 ($)", min_value=0.0, value=150.0, step=1.0)
        pos_premium = st.number_input("权利金 ($)", min_value=0.0, value=45.0, step=5.0)
        pos_quantity = st.number_input("张数", min_value=1, value=1, step=1)
        pos_expiry = st.text_input("到期日 (YYYY-MM-DD)", value=get_next_friday())
        submitted = st.form_submit_button("➕ 添加持仓")
        
        if submitted:
            add_position(pos_strike, pos_premium, pos_quantity, pos_expiry)
            st.success(f"已添加: {pos_quantity}张 ${pos_strike} Put @ ${pos_premium}")
    
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
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("TQQQ", f"${price:.2f}")

with col2:
    st.metric("持仓数", f"{len(st.session_state.positions)} 个")

with col3:
    stats = st.session_state.portfolio_stats
    st.metric("总权利金", f"${stats['total_premium']:,.0f}")

with col4:
    st.metric("最大风险", f"${stats['max_risk']:,.0f}")


# ==================== 第一行：持仓跟踪 + 风险面板 ====================
col_pos, col_risk = st.columns([3, 2])

with col_pos:
    st.subheader("📋 持仓跟踪")
    
    if st.session_state.positions:
        # 持仓表格
        pos_data = []
        for p in st.session_state.positions:
            # 估算当前价值（简化：使用原始权利金，不实时更新）
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
        st.dataframe(
            df_pos,
            use_container_width=True,
            hide_index=True,
            column_config={
                'ID': st.column_config.NumberColumn('ID', width=40),
            }
        )
        
        # 删除按钮
        col_del, _ = st.columns([1, 4])
        with col_del:
            del_id = st.number_input("删除ID", min_value=1, value=1, step=1)
            if st.button("🗑️ 删除"):
                remove_position(del_id)
                st.rerun()
    else:
        st.info("暂无持仓，请在左侧添加")

with col_risk:
    st.subheader("⚠️ 风险面板")
    
    # Delta 敞口
    delta = stats['total_delta']
    delta_pct = abs(delta) / config.CAPITAL * 100 if config.CAPITAL > 0 else 0
    delta_level = "🔴 高" if delta_pct > 20 else "🟡 中" if delta_pct > 10 else "🟢 低"
    st.metric("Delta 敞口", f"{delta:.2f} ({delta_pct:.1f}%)", delta_level)
    
    # Gamma
    st.metric("Gamma", f"{stats['total_gamma']:.3f}")
    
    # Theta
    theta = stats['total_theta']
    theta_level = "🟢" if theta > 0 else "🔴"
    st.metric(f"{theta_level} Theta (日)", f"${theta:.2f}")
    
    # 最大风险
    max_risk = stats['max_risk']
    risk_pct = max_risk / config.CAPITAL * 100 if config.CAPITAL > 0 else 0
    risk_level = "🔴 高" if risk_pct > 30 else "🟡 中" if risk_pct > 15 else "🟢 低"
    st.metric("最大风险", f"${max_risk:,.0f} ({risk_pct:.1f}%)", risk_level)
    
    # 压力测试
    st.subheader("🧪 压力测试")
    if price > 0:
        up_10 = price * 1.10
        down_10 = price * 0.90
        # 简化计算：Delta * 标的变化
        pnl_up = delta * (up_10 - price)
        pnl_down = delta * (down_10 - price)
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.metric("TQQQ +10%", f"${pnl_up:.0f}")
        with col_s2:
            st.metric("TQQQ -10%", f"${pnl_down:.0f}")


# ==================== 第二行：期权池 ====================
st.divider()
st.subheader("📊 期权池")

# 获取期权数据
expiry = get_next_friday()
puts = get_options_chain(expiry)

if puts:
    # 筛选期权
    strike_threshold = price * (1 - strike_discount)
    
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
        if premium < min_premium or premium > max_premium:
            continue
        
        greeks = calculate_position_greeks(p, price)
        
        filtered.append({
            'strike': strike,
            'premium': premium,
            'bid': bid,
            'ask': ask,
            'iv': iv,
            'oi': oi,
            'delta': greeks['delta'],
            'gamma': greeks['gamma'],
            'theta': greeks['theta'],
            'vega': greeks['vega'],
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
        # 期权表格
        df_opts = pd.DataFrame(filtered)
        df_opts['权利金'] = df_opts['premium'].apply(lambda x: f"${x:.2f}")
        df_opts['行权价'] = df_opts['strike'].apply(lambda x: f"${x:.2f}")
        df_opts['距离'] = df_opts['distance_pct'].apply(lambda x: f"{x:.1f}%")
        df_opts['IV'] = df_opts['iv'].apply(lambda x: f"{x:.1%}")
        df_opts['Delta'] = df_opts['delta'].apply(lambda x: f"{x:.3f}")
        df_opts['Theta'] = df_opts['theta'].apply(lambda x: f"{x:.2f}")
        df_opts['Gamma'] = df_opts['gamma'].apply(lambda x: f"{x:.3f}")
        
        display_cols = ['行权价', '权利金', '距离', 'IV', 'Delta', 'Theta', 'Gamma']
        st.dataframe(
            df_opts[display_cols],
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
        
        卖出 TQQQ ${top['strike']:.2f} Put，{expiry} 到期
        - 收取权利金: **${top['premium']:.2f}**
        - 如被行权成本: ${top['strike']:.2f}
        - 最大风险: ${top['strike'] - top['premium']:.2f}
        """)
    else:
        st.warning(f"当前没有符合条件（权利金 ${min_premium}-${max_premium}）的期权")
else:
    st.error("无法获取期权数据")


# ==================== 底部 ====================
st.markdown("---")
st.markdown(f"*📌 自动刷新间隔: {refresh_interval//60}分钟 | {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}*")
