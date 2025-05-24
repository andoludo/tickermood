import tempfile
from abc import abstractmethod
from contextlib import contextmanager
from pathlib import Path
from time import sleep
from typing import List, Optional, Generator, Any
from webbrowser import Chrome

from googlesearch import search
from newspaper import Article
from pydantic import BaseModel, Field, ConfigDict
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from bs4 import BeautifulSoup

from tickermood.articles import News, Consensus
from tickermood.subject import Subject
from tickermood.types import SourceName


@contextmanager
def web_browser(url:str, load_strategy_none: bool = False, headless: bool = False) -> Generator[BeautifulSoup, Any, None]:
    option = Options()
    if headless:
        option.add_argument("--headless")
    if load_strategy_none:
        option.page_load_strategy = "none"
    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=option)
    sleep(2)
    browser.get(url)
    with tempfile.NamedTemporaryFile(suffix=".html", delete=True) as page:
        Path(page.name).write_bytes(browser.page_source.encode("utf-8"))
        yield BeautifulSoup(page, "html.parser")
    browser.quit()



class BaseSource(BaseModel):
    name: SourceName
    url: str

    @classmethod
    def search(cls, subject: Subject)-> "BaseSource":...

    @abstractmethod
    def news(self)-> List[News]:...
    @abstractmethod
    def consensus(self)-> List[Consensus]:...

class BaseSeleniumScrapper(BaseModel):...

class Investing(BaseSource):
    name: SourceName = "Investing"

    @classmethod
    def search(cls, subject: Subject)-> Optional["Investing"]:
        search_url = f"https://www.investing.com/search?q={subject.to_url_search_name()}"
        ticker_link = None
        with web_browser(search_url) as soup:
            sections = soup.find_all("div", class_='searchSectionMain')
            for section in sections:
                header = section.find(class_='groupHeader')
                if header and header.get_text(strip=True) == 'Quotes':
                    links = [a['href'] for a in section.find_all('a', href=True)]
                    if links:
                         ticker_link = links[0]
        if ticker_link:
            ticker_url = f"https://www.investing.com{ticker_link}"
            return cls(url=ticker_url)
        return None
    def news(self)->List[News]:
        news_url = f"{self.url}-news"
        urls= []
        articles = []
        with web_browser(news_url) as soup:
            news = soup.find('ul', attrs={'data-test': 'news-list'})
            for item in news:
                if not item.select_one('.mb-1.mt-2\\.5.flex'):  # Note: dot escapes in class name with decimals
                    links = item.find_all('a', href=True)
                    urls.extend(list({a['href'] for a in links}))
        for url in urls:
            with web_browser(url) as soup:
                article_ = soup.find("div", class_='article_container')
                content = article_.get_text(separator=' ', strip=True)
                articles.append(News(url=url, source=self.name, content=content))
        return articles

    def consensus(self):...


class BaseScrapper(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)
    browser: Optional[WebDriver] = None
    def _get(self, url: str):
        sleep(2)
        self.browser = web_browser()
        self.browser.get(url)
    def _close(self):
        self.browser.quit()
        self.browser = None


    def search_ticker(self, ticker_name: str) -> Optional[str]:
        ticker_name = ticker_name.replace(" ", "+")
        self._get(f"https://www.investing.com/search?q={ticker_name}")
        ticker_link = None
        with tempfile.NamedTemporaryFile(suffix=".html", delete=True) as page:
            Path(page.name).write_bytes(self.browser.page_source.encode("utf-8"))
            soup = BeautifulSoup(page, "html.parser")
            sections = soup.find_all("div", class_='searchSectionMain')
            for section in sections:
                header = section.find(class_='groupHeader')
                if header and header.get_text(strip=True) == 'Quotes':
                    links = [a['href'] for a in section.find_all('a', href=True)]
                    if links:
                         ticker_link = links[0]
        self._close()
        if not ticker_link:
            return None
        return f"https://www.investing.com{ticker_link}"


    def consensus(self, ticker_url: str):
        self._get(f"{ticker_url}-consensus-estimates")
        element = self.browser.find_element(By.XPATH,
                                      '/html/body/div[1]/div[2]/div[1]/div[2]/div[1]/div[3]/div/div[1]')

        element = self.browser.find_element(By.XPATH,"/html/body/div[1]/div[2]/div[1]/div[2]/div[1]/div[3]/div/div[2]")
        "/html/body/div[1]/div[2]/div[1]/div[2]/div[1]/div[4]/section/div[3]/div[1]"
        "/html/body/div[1]/div[2]/div[1]/div[2]/div[1]/div[4]/section/div[3]/div[2]"
        element.text
        self._close()
        return urls

    def get_news_urls(self, ticker_url: str):
        self._get(f"{ticker_url}-news")
        with tempfile.NamedTemporaryFile(suffix=".html", delete=True) as page:
            Path(page.name).write_bytes(self.browser.page_source.encode("utf-8"))
            soup = BeautifulSoup(page, "html.parser")
            urls = []
            news = soup.find('ul', attrs={'data-test': 'news-list'})
            for item in news:
                if not item.select_one('.mb-1.mt-2\\.5.flex'):  # Note: dot escapes in class name with decimals
                    links = item.find_all('a', href=True)
                    urls.extend(list({a['href'] for a in links}))
        self._close()
        return urls

    def read(self, urls):
        articles = []
        for url in urls:
            self._get(url)
            with tempfile.NamedTemporaryFile(suffix=".html", delete=True) as page:
                Path(page.name).write_bytes(self.browser.page_source.encode("utf-8"))
                soup = BeautifulSoup(page, "html.parser")
                article_ = soup.find("div", class_='article_container')
                articles.append(article_.get_text(separator=' ', strip=True))
            self._close()
        return articles
