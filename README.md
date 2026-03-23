# TQQQ 期权 SP 策略工具

## 策略说明

- **标的**: TQQQ (3倍做多纳指)
- **策略**: Short Put (卖出看跌期权)
- **筛选条件**:
  - 到期日：下周五
  - 行权价：低于现价 20%
  - 每周操作 1-2 次
  - 尽量不接股、不 roll

## 参数配置

| 参数 | 值 |
|------|-----|
| 资金体量 | $25,000 |
| 每周最大亏损 | 5% ($1,250) |
| 券商 | 富途 |

## 文件结构

```
tqqq-sp-strategy/
├── config.py          # 配置文件
├── fetcher.py         # 期权数据获取
├── analyzer.py        # 策略分析
├── notifier.py        # 通知推送
├── main.py            # 主程序
├── run.sh             # 运行脚本
└── requirements.txt   # 依赖
```

## 使用方法

```bash
# 安装依赖
pip install -r requirements.txt

# 运行策略分析
python main.py
```

## 数据来源

- 期权数据：Yahoo Finance API
- 实时行情：yfinance 库
