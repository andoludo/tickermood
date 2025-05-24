from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from tickermood.articles import News, Consensus
from tickermood.database.crud import TickerMoodDb


class TickerSubject(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str] = None

    def to_url_search_name(self) ->str:
        return self.name.replace(" ", "+")


class Subject(TickerSubject):
    date: Optional[datetime] = Field(default_factory=datetime.now)
    news: List[News] = Field(default_factory=list)
    consensus: List[Consensus] = Field(default_factory=list)

    def save(self, database_path: Path) -> None:
        TickerMoodDb(database_path = database_path).write(self)

    def load(self, database_path: Path) -> "Subject":
        db = TickerMoodDb(database_path=database_path)
        return db.load(subject=self)





