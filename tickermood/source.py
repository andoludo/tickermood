import logging
import tempfile
from abc import abstractmethod
from contextlib import contextmanager
from pathlib import Path
from time import sleep
from typing import List, Optional, Generator, Any

from bs4 import BeautifulSoup
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

from tickermood.articles import News, PriceTargetNews
from tickermood.subject import Subject
from tickermood.types import SourceName

logger = logging.getLogger(__name__)


@contextmanager
def web_browser(
    url: str, load_strategy_none: bool = False, headless: bool = False
) -> Generator[WebDriver, Any, None]:
    option = Options()
    option.add_argument("--disable-popup-blocking")
    option.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
    if headless:
        option.add_argument("--headless")
    if load_strategy_none:
        option.page_load_strategy = "none"
    browser = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=option
    )
    sleep(2)
    browser.get(url)
    yield browser

    browser.quit()


@contextmanager
def soup_page(browser: WebDriver) -> Generator[BeautifulSoup, Any, None]:
    with tempfile.NamedTemporaryFile(suffix=".html", delete=True) as page:
        Path(page.name).write_bytes(browser.page_source.encode("utf-8"))
        yield BeautifulSoup(page, "html.parser")


@contextmanager
def local_html(
    url: str, load_strategy_none: bool = False, headless: bool = False
) -> Generator[str, Any, None]:
    with web_browser(
        url, load_strategy_none, headless
    ) as browser, tempfile.NamedTemporaryFile(suffix=".html", delete=True) as page:
        Path(page.name).write_bytes(browser.page_source.encode("utf-8"))
        yield "file://" + page.name


@contextmanager
def temporary_web_page(
    url: str, load_strategy_none: bool = False, headless: bool = False
) -> Generator[BeautifulSoup, Any, None]:
    with web_browser(url, load_strategy_none, headless) as browser, soup_page(
        browser
    ) as soup:
        yield soup


class BaseSource(BaseModel):
    name: SourceName
    url: str
    headless: bool = False

    @classmethod
    def search_subject(cls, subject: Subject, headless: bool = False) -> Subject:
        source = cls.search(subject, headless=headless)
        if source:
            subject.news.extend(source.news())
            subject.price_target_news.extend(source.get_price_target_news())
        return subject

    @classmethod
    def search(
        cls, subject: Subject, headless: bool = False
    ) -> Optional["BaseSource"]: ...

    @abstractmethod
    def news(self) -> List[News]: ...
    @abstractmethod
    def get_price_target_news(self) -> List[PriceTargetNews]: ...


class BaseSeleniumScrapper(BaseModel): ...


class Investing(BaseSource):
    name: SourceName = "Investing"

    @classmethod
    def search(cls, subject: Subject, headless: bool = False) -> Optional["Investing"]:
        search_url = f"https://www.investing.com/search?q={subject.to_symbol_search()}"
        ticker_link = None
        with temporary_web_page(search_url, headless=headless) as soup:
            sections = soup.find_all("div", class_="searchSectionMain")
            for section in sections:
                header = section.find(class_="groupHeader")
                if header and header.get_text(strip=True) == "Quotes":
                    links = [a["href"] for a in section.find_all("a", href=True)]
                    if links:
                        ticker_link = links[0]
        if ticker_link:
            ticker_url = f"https://www.investing.com{ticker_link}"
            return cls(url=ticker_url, headless=headless)
        return None

    def news(self) -> List[News]:
        news_url = f"{self.url}-news"
        urls: List[str] = []
        articles = []
        with temporary_web_page(news_url, headless=self.headless) as soup:
            news_ = soup.find("ul", attrs={"data-test": "news-list"})
            if not news_:
                logger.warning(f"No news found at {news_url}")
                return []
            for item in news_:

                if not item.select_one(".mb-1.mt-2\\.5.flex"):  # type: ignore[union-attr]
                    links = item.find_all("a", href=True)  # type: ignore[union-attr]
                    urls.extend(list({a["href"] for a in links}))
        for url in urls:
            try:
                with temporary_web_page(url, headless=self.headless) as soup:
                    article_ = soup.find("div", class_="article_container")
                    if article_ is not None:
                        content = article_.get_text(separator=" ", strip=True)
                        articles.append(
                            News(url=url, source=self.name, content=content)
                        )
            except Exception as e:  # noqa: PERF203
                logger.warning(f"Error processing article {url}: {e}")
                continue
        return articles

    def get_price_target_news(self) -> List[PriceTargetNews]:
        consensus_url = f"{self.url}-consensus-estimates"
        with temporary_web_page(consensus_url, headless=self.headless) as soup:
            articles = soup.find_all("div", class_="mb-6")
            content = "\n\n\n".join(
                [a.get_text(separator="\n", strip=True) for a in articles]
            )
        return [PriceTargetNews(url=consensus_url, content=content, source=self.name)]
