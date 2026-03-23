#!/bin/bash
# TQQQ SP 策略工具 - 运行脚本

cd "$(dirname "$0")"

# 激活虚拟环境（如有）
# source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
