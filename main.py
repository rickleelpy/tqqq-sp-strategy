"""
TQQQ SP 策略工具 - 主程序
"""

from fetcher import OptionsFetcher
from analyzer import analyze_market
import config
from datetime import datetime


def format_report(report: Dict) -> str:
    """格式化报告为可读文本"""
    lines = []
    lines.append("=" * 50)
    lines.append("🦐 TQQQ 期权 SP 策略分析报告")
    lines.append("=" * 50)
    lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"📈 标的: {config.TICKER}")
    lines.append(f"💵 当前价格: ${report['details']['current_price']:.2f}")
    lines.append(f"🎯 行权价门槛: ${report['details']['strike_threshold']:.2f} (低于现价 {config.STRIKE_DISCOUNT*100}%)")
    lines.append(f"📆 目标到期日: {report['details']['expiry']}")
    lines.append("")
    
    if not report["has_opportunity"]:
        lines.append("❌ 当前没有符合条件的期权")
        lines.append("")
        lines.append("建议：等待大跌后再检查")
        return "\n".join(lines)
    
    # 最佳选择
    pick = report["top_pick"]
    lines.append("✅ 推荐期权:")
    lines.append("-" * 30)
    lines.append(f"  行权价: ${pick['strike']:.2f}")
    lines.append(f"  权利金: ${pick['premium']:.2f} ({pick['premium_pct']:.2f}%)")
    lines.append(f"  最大亏损: ${pick['max_loss']:.2f}")
    lines.append(f"  盈亏平衡: ${pick['break_even']:.2f}")
    lines.append(f"  风险收益比: 1:{pick['risk_reward']:.2f}")
    lines.append(f"  Delta: {pick.get('delta', 0):.3f}")
    lines.append(f"  Theta: {pick.get('theta', 0):.3f}")
    lines.append(f"  IV: {pick.get('iv', 0):.2%}")
    lines.append(f"  保证金: ${pick['margin']:.0f}")
    lines.append(f"  得分: {pick['score']}")
    lines.append(f"  推荐理由: {', '.join(pick['reasons'])}")
    lines.append("")
    
    # 警告
    if report["warnings"]:
        lines.append("⚠️ 风险提示:")
        for warning in report["warnings"]:
            lines.append(f"  {warning}")
        lines.append("")
    
    # 备选
    if report["alternatives"]:
        lines.append("📋 备选期权:")
        for i, alt in enumerate(report["alternatives"], 1):
            lines.append(f"  {i}. ${alt['strike']:.2f} | 权利金 ${alt['premium']:.2f} | 得分 {alt['score']}")
        lines.append("")
    
    # 策略总结
    summary = report["strategy_summary"]
    lines.append("📝 操作建议:")
    lines.append(f"  卖出 {config.TICKER} ${pick['strike']:.2f} Put，到期日 {summary['expiry']}")
    lines.append(f"  收取权利金 ${pick['premium']:.2f}")
    lines.append(f"  如被行权则以 ${pick['strike']:.2f} 买入股票")
    lines.append(f"  最大风险: ${pick['max_loss']:.2f}")
    lines.append("")
    
    return "\n".join(lines)


def main():
    """主函数"""
    print("🦐 正在获取 TQQQ 期权数据...")
    
    try:
        # 获取数据
        fetcher = OptionsFetcher()
        market_data = fetcher.fetch_all_data()
        
        print(f"当前价格: ${market_data['current_price']:.2f}")
        print(f"目标到期日: {market_data['target_expiry']}")
        print(f"行权价门槛: ${market_data['strike_threshold']:.2f}")
        print("")
        
        # 分析
        report = analyze_market(market_data)
        
        # 输出报告
        print(format_report(report))
        
        return report
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
