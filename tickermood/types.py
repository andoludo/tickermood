from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

SourceName = Literal["Investing", "Marketwatch", "Yahoo"]
ConsensusType = Literal[
    "Strong Buy", "Buy", "Cautious Buy", "Hold", "Cautious Sell", "Sell", "Strong Sell"
]


class DatabaseConfig(BaseModel):
    database_path: Path = Field(default=Path.cwd() / "tickermood.db")
    no_migration: bool = False
