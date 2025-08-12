import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from tickermood.source import Investing, Yahoo, Marketwatch
from tickermood.subject import Subject
from tickermood.types import DatabaseConfig


@pytest.mark.local
def test_investing_search() -> None:
    subject = Subject(symbol="IQV", name="IQVIA Holdings Inc.", exchange="NYSE")
    investing = Investing.search(subject, headless=True)
    assert investing is not None


@pytest.mark.local
def test_investing_news() -> None:
    subject = Subject(symbol="IQV", name="IQVIA Holdings Inc.", exchange="NYSE")
    investing = Investing.search(subject, headless=False)
    news = investing.news()
    assert news
    assert len(news) > 0
    assert all(n.content is not None for n in news)


@pytest.mark.local
def test_investing_consensus() -> None:
    subject = Subject(symbol="IQV", name="IQVIA Holdings Inc.", exchange="NYSE")
    investing = Investing.search(subject, headless=True)
    consensus = investing.get_price_target_news()
    assert consensus
    assert consensus[0].content is not None


@pytest.mark.local
def test_search_subject() -> None:
    subject = Subject(symbol="BEN.PA", name="beneteau", exchange="NASDAQ")
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        subject = Investing.search_subject(subject, headless=True)
        database_config = DatabaseConfig(database_path=Path(f.name))
        subject.save(database_config)
        loaded_subject = subject.load(database_config)
        assert loaded_subject
        assert loaded_subject.news
        assert loaded_subject.price_target_news


@pytest.mark.local
def test_search_subject_() -> None:
    subject = Subject(symbol="PLTR", name="palantir", exchange="NASDAQ")
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        subject = Investing.search_subject(subject, headless=True)
        database_config = DatabaseConfig(database_path=Path(f.name))
        subject.save(database_config)
        loaded_subject = subject.load(database_config)
        assert loaded_subject
        assert loaded_subject.news
        assert loaded_subject.price_target_news


class MockedChrome:

    def get(self, url: str):
        return

    def set_page_load_timeout(self, timeout: int):
        return

    def quit(self): ...
    @property
    def page_source(self):
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Mini Test Page</title>
</head>
<body>
    <h1 id="title">Hello, Selenium!</h1>
    <p class="description">
        This is a lightweight page for unit-testing anything that consumes
        <code>browser.page_source</code>.
    </p>
</body>
</html>
"""


def mocked_chrome(*args: Any, **kwargs: Any) -> MockedChrome:
    return MockedChrome()


@patch("tickermood.source.uc.Chrome", side_effect=mocked_chrome)
def test_mocked_search_subject_(chrome: MockedChrome):
    subject = Subject(symbol="PLTR", name="palantir", exchange="NASDAQ")
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        subject = Investing.search_subject(subject, headless=True)
        database_config = DatabaseConfig(database_path=Path(f.name))
        subject.save(database_config)
        loaded_subject = subject.load(database_config)
        assert loaded_subject


@pytest.mark.skip("Until Chrome 139 is available on the image")
def test_yahoo_search() -> None:
    subject = Subject(symbol="LOTB.BR")
    yahoo = Yahoo.search(subject, headless=True)
    news = yahoo.news()
    price_target = yahoo.get_price_target_news()
    assert news
    assert price_target


@pytest.mark.skip("Until Chrome 139 is available on the image")
def test_market_watch_search() -> None:
    subject = Subject(symbol="PLTR")
    market_watch = Marketwatch.search(subject, headless=True)
    news = market_watch.news()
    assert news
