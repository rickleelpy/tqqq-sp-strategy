"""
TQQQ SP 策略配置
"""

# ==================== 基础参数 ====================
TICKER = "TQQQ"              # 标的
STRATEGY = "SP"              # 策略类型: SP = Short Put

# ==================== 资金参数 ====================
CAPITAL = 25000              # 资金体量 ($)
MAX_WEEKLY_LOSS = 0.05       # 每周最大亏损比例 (5%)
MAX_WEEKLY_LOSS_AMOUNT = CAPITAL * MAX_WEEKLY_LOSS  # $1,250

# ==================== 筛选参数 ====================
STRIKE_DISCOUNT = 0.20       # 行权价低于现价比例 (20%)
EXPIRY_DAY = "FRIDAY"        # 到期日 (每周五)
MIN_PREMIUM = 50             # 最小权利金 ($)
MIN_DELTA = 0.10             # 最小 Delta 绝对值

# ==================== 风险参数 ====================
MAX_DELTA_EXPOSURE = 0.30    # 最大 Delta 敞口 (30% 资金)
STOP_LOSS_PCT = 0.50         # 止损线 (亏损超过权利金的 50%)

# ==================== 通知配置 ====================
NOTIFY_WHEN = [
    "opportunity",           # 有符合条件的机会
    "warning",              # 风险警告
    "summary",              # 每日/每周总结
]

# ==================== 券商配置 ====================
BROKER = "futu"              # 券商: futu / ib / webull
