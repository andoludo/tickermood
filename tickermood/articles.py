from typing import Optional

from pydantic import BaseModel


class BaseArticle(BaseModel):
    url: Optional[str] = None
    source: str
    title: Optional[str] = None
    content: str


class News(BaseArticle):
    ...


class Consensus(BaseArticle):
    ...
