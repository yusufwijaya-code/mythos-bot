from loguru import logger


def format_backtest_report(results: dict) -> str:
    """Format backtest results as readable text report."""
    if not results or results.get("total_trades", 0) == 0:
        return "No trades executed during backtest period."

    report = f"""
========================================
  BACKTEST REPORT - {results['pair']}
========================================
Strategy   : {results['strategy']}
Timeframe  : {results['timeframe']}
Period     : {results['days']} days

--- PERFORMANCE ---
Total Trades   : {results['total_trades']}
Winning Trades : {results['winning_trades']}
Losing Trades  : {results['losing_trades']}
Win Rate       : {results['win_rate']:.1f}%

--- PROFIT/LOSS ---
Net Profit     : {results['net_profit']:+.2f} USDT ({results['net_profit_pct']:+.2f}%)
Gross Profit   : {results.get('gross_profit', 0):.2f} USDT
Gross Loss     : {results.get('gross_loss', 0):.2f} USDT
Profit Factor  : {results['profit_factor']:.2f}

--- RISK ---
Max Drawdown   : {results['max_drawdown']:.2f} USDT ({results['max_drawdown_pct']:.2f}%)
Sharpe Ratio   : {results['sharpe_ratio']:.2f}

--- BALANCE ---
Initial        : {results['final_balance'] - results['net_profit']:.2f} USDT
Final          : {results['final_balance']:.2f} USDT
========================================
"""
    return report.strip()


def format_backtest_for_whatsapp(results: dict) -> str:
    """Format backtest results for WhatsApp message."""
    if not results or results.get("total_trades", 0) == 0:
        return "[BACKTEST] No trades executed."

    return (
        f"[BACKTEST RESULT]\n"
        f"Pair: {results['pair']}\n"
        f"Strategy: {results['strategy']}\n"
        f"Period: {results['days']} days\n"
        f"Trades: {results['total_trades']}\n"
        f"Win Rate: {results['win_rate']:.1f}%\n"
        f"Net Profit: {results['net_profit']:+.2f} USDT\n"
        f"Max DD: {results['max_drawdown_pct']:.1f}%\n"
        f"Sharpe: {results['sharpe_ratio']:.2f}"
    )
