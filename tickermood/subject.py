from datetime import datetime
from pathlib import Path
from typing import List, Optional, Type

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from tickermood.articles import News, PriceTargetNews, NewsSummary, Summary
from tickermood.database.crud import TickerMoodDb
from tickermood.types import ConsensusType


class TickerSubject(BaseModel):
    symbol: str
    name: str
    exchange: Optional[str] = None

    def to_url_search_name(self) -> str:
        return self.name.replace(" ", "+")


class PriceTarget(BaseModel):
    high_price_target: Optional[float] = None
    low_price_target: Optional[float] = None
    fair_value: Optional[float] = None
    summary_price_target: Optional[str] = None


class Consensus(BaseModel):
    consensus: Optional[ConsensusType] = None
    reason: Optional[str] = None


class Subject(TickerSubject, PriceTarget, Consensus):
    date: Optional[datetime] = Field(default_factory=datetime.now)
    news: List[News] = Field(default_factory=list)
    news_summary: List[NewsSummary] = Field(default_factory=list)
    summary: Optional[Summary] = None
    price_target_news: List[PriceTargetNews] = Field(default_factory=list)

    def save(self, database_path: Path) -> None:
        TickerMoodDb(database_path=database_path).write(self)

    def load(self, database_path: Path) -> "Subject":
        db = TickerMoodDb(database_path=database_path)
        return db.load(subject=self)

    def add_news_summary(self, content: str, origin: news) -> None:
        self.news_summary.append(
            NewsSummary(
                url=origin.url,
                content=content,
                source=origin.source,
                title=origin.title,
            )
        )

    def add_summary(self, content: str) -> None:
        self.summary = Summary(content=content)

    def combined_news(self):
        return "####\n".join(n.content for n in self.news if n.content)

    def combined_price_target_news(self):
        return "####\n".join(n.content for n in self.price_target_news if n.content)

    def add_price_target(self, price_target: PriceTarget) -> None:
        for field in list(PriceTarget.model_fields):
            setattr(self, field, getattr(price_target, field))


class LLM(BaseModel):
    model_type: Type[BaseChatModel]
    model_name: str
    temperature: float = 0.0

    def get_model(self) -> BaseChatModel:
        return self.model_type(model_name=self.model_name, temperature=self.temperature)


class LLMSubject(Subject, LLM):

    def get_next_article(self) -> Optional[News]:
        return next(
            (
                n
                for n in self.news
                if hash(n) not in {hash(s) for s in self.news_summary}
            ),
            None,
        )
