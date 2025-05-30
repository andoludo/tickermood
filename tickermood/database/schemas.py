from datetime import datetime
from typing import Optional, List, Any

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field

from tickermood.subject import Subject


class BaseTable(SQLModel): ...


class SubjectORM(BaseTable, Subject, table=True):
    __tablename__ = "subject"
    date: datetime = Field(primary_key=True, index=True)
    symbol: str = Field(primary_key=True, index=True)
    consensus: Optional[str] = Field(default=None, index=True)
    news: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))  # type: ignore
    news_summary: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))  # type: ignore
    summary: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))  # type: ignore
    price_target_news: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))  # type: ignore
