import os
from typing import List
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings
from pydantic import field_validator

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")


class Settings(BaseSettings):
    # Binance
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "bot_trading_mythos"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    # Fonnte
    FONNTE_TOKEN: str = ""
    FONNTE_SENDER: str = "6282114939571"
    FONNTE_TARGET: str = "62895394755672"

    # Trading
    TRADING_MODE: str = "paper"
    TRADING_PAIRS: List[str] = ["BTCUSDT"]
    TIMEFRAME: str = "1h"

    # Risk Management
    STOP_LOSS_PCT: float = 2.0
    TAKE_PROFIT_PCT: float = 4.0
    MAX_POSITION_PCT: float = 10.0
    MAX_DAILY_LOSS_PCT: float = 5.0
    TRAILING_STOP_PCT: float = 1.5
    MAX_TRADES_PER_DAY: int = 10

    # Pair Scanner
    SCANNER_ENABLED: bool = True
    SCANNER_TOP_PAIRS: int = 20
    SCANNER_MIN_VOLUME: float = 10_000_000  # Min 24h volume in USDT
    MAX_OPEN_POSITIONS: int = 3

    # Paper Trading
    PAPER_INITIAL_BALANCE: float = 10000.0

    # Authentication
    AUTH_PASSWORD_HASH: str = ""
    JWT_SECRET_KEY: str = "change_this_to_a_random_secret_string"
    AUTHORIZED_EMAILS: List[str] = ["yusufwijaya3@gmail.com"]

    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    @field_validator("TRADING_PAIRS", mode="before")
    @classmethod
    def parse_trading_pairs(cls, v):
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    @field_validator("AUTHORIZED_EMAILS", mode="before")
    @classmethod
    def parse_authorized_emails(cls, v):
        if isinstance(v, str):
            return [e.strip() for e in v.split(",") if e.strip()]
        return v

    @property
    def DATABASE_URL(self) -> str:
        password = quote_plus(self.DB_PASSWORD)
        return (
            f"mysql+pymysql://{self.DB_USER}:{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def is_live(self) -> bool:
        return self.TRADING_MODE.lower() == "live"

    model_config = {
        "env_file": ENV_PATH,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
