from typing import Optional

from pydantic import BaseModel


class Summary(BaseModel):
    content: str


class BaseArticle(Summary):
    url: Optional[str] = None
    source: str
    title: Optional[str] = None

    def __hash__(self) -> int:
        return hash((self.url, self.source))


class News(BaseArticle): ...


class NewsSummary(BaseArticle): ...


class PriceTargetNews(BaseArticle): ...
