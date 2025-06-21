import json
import logging
import re
import tempfile
from abc import abstractmethod
from contextlib import contextmanager
from pathlib import Path
from time import sleep
from typing import List, Optional, Generator, Any, Callable

from bs4 import BeautifulSoup
from pydantic import BaseModel, model_validator
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from tickermood.articles import News, PriceTargetNews
from tickermood.subject import Subject
from tickermood.types import SourceName

import yfinance as yf  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)
PAGE_SOURCE_PATH = Path(__file__).parents[1] / "tests" / "sources"


def clean_url(url: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]", "", url)


class SavePage(BaseModel):
    url: str
    source: str
    save: bool = False

    @model_validator(mode="after")
    def _validator(self) -> "SavePage":
        self.url = f'{clean_url(self.url.replace("html",""))}.html'
        return self


@contextmanager
def web_browser(
    url: str,
    load_strategy_none: bool = False,
    headless: bool = False,
    callback: Optional[Callable[[WebDriver], None]] = None,
) -> Generator[WebDriver, Any, None]:
    option = Options()
    option.add_argument("--disable-popup-blocking")
    option.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
    option.add_argument("--no-sandbox")
    option.add_argument("--disable-dev-shm-usage")
    if headless:
        option.add_argument("--headless")
    if load_strategy_none:
        option.page_load_strategy = "none"
    browser = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=option
    )
    browser.get(url)
    if callback:
        sleep(2)
        callback(browser)

    sleep(2)

    yield browser

    browser.quit()


@contextmanager
def soup_page(
    browser: WebDriver, save_page: Optional[SavePage] = None
) -> Generator[BeautifulSoup, Any, None]:
    with tempfile.NamedTemporaryFile(suffix=".html", delete=True) as page:
        page_source_code = browser.page_source.encode("utf-8")
        Path(page.name).write_bytes(page_source_code)
        if save_page and save_page.save:
            source_path = PAGE_SOURCE_PATH.joinpath(save_page.source)
            source_path.mkdir(parents=True, exist_ok=True)
            source_path.joinpath(clean_url(save_page.url)).write_bytes(page_source_code)

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
    url: str,
    load_strategy_none: bool = False,
    headless: bool = False,
    save_page: Optional[SavePage] = None,
    callback: Optional[Callable[[WebDriver], None]] = None,
) -> Generator[BeautifulSoup, Any, None]:
    with web_browser(
        url, load_strategy_none, headless, callback=callback
    ) as browser, soup_page(browser, save_page=save_page) as soup:
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
        save_page = SavePage(url=search_url, source="Investing", save=True)
        with temporary_web_page(
            search_url, headless=headless, save_page=save_page
        ) as soup:
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


def find_cookie_banner(browser: WebDriver) -> None:
    try:
        button = browser.find_element(
            By.XPATH, "/html/body/div/div/div/div/form/div[2]/div[2]/button[1]"
        )
        button.click()
    except NoSuchElementException:
        pass


class Yahoo(BaseSource):
    name: SourceName = "Yahoo"

    @classmethod
    def search(cls, subject: Subject, headless: bool = False) -> Optional["Yahoo"]:
        return cls(
            url=subject.symbol,
            headless=headless,
        )

    def news(self) -> List[News]:
        ticker = yf.Ticker(self.url)
        urls = [
            n.get("content", {}).get("canonicalUrl", {}).get("url", "")
            for n in ticker.get_news()
        ]
        articles = []
        for url in urls:
            if not url:
                continue
            try:
                with temporary_web_page(
                    url, headless=self.headless, callback=find_cookie_banner
                ) as soup:

                    for tag in soup(
                        [
                            "script",
                            "style",
                            "noscript",
                            "svg",
                            "meta",
                            "header",
                            "footer",
                        ]
                    ):
                        tag.decompose()
                    if soup is not None:
                        content = soup.get_text(separator=" ", strip=True)
                        articles.append(
                            News(url=url, source=self.name, content=content)
                        )
            except Exception as e:
                logger.warning(f"Error processing article {url}: {e}")
                continue
        return articles

    def get_price_target_news(self) -> List[PriceTargetNews]:
        ticker = yf.Ticker(self.url)
        return [
            PriceTargetNews(
                url=self.url,
                content=json.dumps(ticker.get_analyst_price_targets()),
                source=self.name,
            )
        ]
