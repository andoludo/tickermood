import os
import urllib.parse
from datetime import datetime
from typing import List, Optional, Type

import ollama
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field, model_validator

from tickermood.articles import News, PriceTargetNews, NewsSummary, Summary
from tickermood.database.crud import TickerMoodDb
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from tickermood.exceptions import InvalidLLMError, OllamaModelError, OllamaError
from tickermood.types import DatabaseConfig


class TickerSubject(BaseModel):
    symbol: str
    symbol_without_suffix: Optional[str] = Field(default=None)
    name: Optional[str] = None
    exchange: Optional[str] = None

    @model_validator(mode="after")
    def _validation(self) -> "TickerSubject":
        self.symbol_without_suffix = self.symbol.split(".")[0]
        return self

    def to_symbol_search(self) -> str:
        if self.symbol_without_suffix is None:
            raise ValueError("Symbol without suffix is not set.")
        if self.name:
            return urllib.parse.quote(
                f"{self.symbol_without_suffix.upper()}+{self.name.replace(' ', '+')}"
            )
        return self.symbol_without_suffix.upper()


class PriceTarget(BaseModel):
    high_price_target: Optional[float] = None
    low_price_target: Optional[float] = None
    fair_value: Optional[float] = None
    summary_price_target: Optional[str] = None


class Consensus(BaseModel):
    consensus: Optional[str] = None
    reason: Optional[str] = None


class Subject(TickerSubject, PriceTarget, Consensus):
    date: Optional[datetime] = Field(default_factory=datetime.now)
    news: List[News] = Field(default_factory=list)
    news_summary: List[NewsSummary] = Field(default_factory=list)
    summary: Optional[Summary] = None
    price_target_news: List[PriceTargetNews] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validator(self) -> "Subject":
        if self.news_summary and len(self.news_summary) != len(self.news_summary):
            raise ValueError(
                "The length of news_summary must match the length of news."
            )
        if len(self.news) != len(set(self.news)):
            raise ValueError("News items must be unique.")
        return self

    def save(self, database_config: DatabaseConfig) -> None:
        TickerMoodDb(
            database_path=database_config.database_path,
            no_migration=database_config.no_migration,
        ).write(self)

    def load(self, database_config: DatabaseConfig) -> "Subject":
        db = TickerMoodDb(
            database_path=database_config.database_path,
            no_migration=database_config.no_migration,
        )
        return db.load(subject=self)

    def add_news_summary(self, content: str, origin: News) -> None:
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

    def combined_summary_news(self) -> str:
        return "####\n".join(n.content for n in self.news_summary if n.content)

    def combined_price_target_news(self) -> str:
        return "####\n".join(n.content for n in self.price_target_news if n.content)

    def add(self, object: BaseModel) -> None:
        for field in list(object.model_fields):
            setattr(self, field, getattr(object, field))

    def get_consensus_data(self) -> str:
        data = f"""Summary of the stock:
        {self.summary}
        {self.summary_price_target}
        """
        return data


def check_ollama_model(model_name: str) -> bool:
    try:
        model_list = ollama.list()
    except Exception as e:
        raise OllamaError("Failed to list Ollama models.") from e
    if not any(model.model == model_name for model in model_list.models):
        raise OllamaModelError(f"Ollama model '{model_name}' not found.")

    return True


def check_openai_model() -> bool:
    return "OPENAI_API_KEY" in os.environ


class LLM(BaseModel):
    model_type: Type[BaseChatModel]
    model_name: str
    temperature: float = 0.0

    @model_validator(mode="after")
    def _validator(self) -> "LLM":
        if (self.model_type == ChatOllama and check_ollama_model(self.model_name)) or (
            self.model_type == ChatOpenAI and check_openai_model()
        ):
            return self
        raise InvalidLLMError("Only Ollama and OpenAI models are supported.")

    def get_model(self) -> BaseChatModel:
        return self.model_type(model=self.model_name, temperature=self.temperature)


class LLMSubject(Subject, LLM):

    @classmethod
    def from_subject(cls, subject: Subject, llm: LLM) -> "LLMSubject":
        return cls.model_validate(subject.model_dump() | llm.model_dump())

    def get_next_article(self) -> Optional[News]:
        return next(
            (
                n
                for n in self.news
                if hash(n) not in {hash(s) for s in self.news_summary}
            ),
            None,
        )
