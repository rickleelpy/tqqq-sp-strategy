#!/bin/bash
# TQQQ 期权 Dashboard 启动脚本

cd "$(dirname "$0")"

# 安装依赖
pip install -r requirements.txt

# 启动 Streamlit
streamlit run dashboard.py --server.port 8501 --server.address localhost
