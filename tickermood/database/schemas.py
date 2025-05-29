from datetime import datetime
from typing import Optional, Dict, List, Any

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field

from tickermood.subject import Subject


class BaseTable(SQLModel): ...


class SubjectORM(BaseTable, Subject, table=True):  # type: ignore
    __tablename__ = "subject"
    date: datetime = Field(primary_key=True, index=True)
    symbol: str = Field(primary_key=True, index=True)
    news: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))
    price_target: Optional[List[Any]] = Field(default=None, sa_column=Column(JSON))
