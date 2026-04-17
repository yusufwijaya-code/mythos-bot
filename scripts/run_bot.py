"""
Run Bot Trading Mythos - Full system (API + Scheduler)
Usage: python scripts/run_bot.py
"""
import os
import sys
import uvicorn

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings


def main():
    print("=" * 50)
    print("  Bot Trading Mythos - Starting")
    print(f"  Mode: {settings.TRADING_MODE}")
    print(f"  Pairs: {', '.join(settings.TRADING_PAIRS)}")
    print(f"  Timeframe: {settings.TIMEFRAME}")
    print(f"  API: http://{settings.API_HOST}:{settings.API_PORT}")
    print("=" * 50)

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
