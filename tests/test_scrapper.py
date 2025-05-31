import tempfile
from pathlib import Path

from tickermood.source import Investing
from tickermood.subject import Subject


def test_investing_search() -> None:
    subject = Subject(symbol="IQV", name="IQVIA Holdings Inc.", exchange="NYSE")
    investing = Investing.search(subject, headless=True)
    assert investing is not None


def test_investing_news() -> None:
    subject = Subject(symbol="IQV", name="IQVIA Holdings Inc.", exchange="NYSE")
    investing = Investing.search(subject, headless=True)
    news = investing.news()
    assert news
    assert len(news) > 0
    assert all(n.content is not None for n in news)


def test_investing_consensus() -> None:
    subject = Subject(symbol="IQV", name="IQVIA Holdings Inc.", exchange="NYSE")
    investing = Investing.search(subject, headless=True)
    consensus = investing.get_price_target_news()
    assert consensus
    assert consensus[0].content is not None


def test_search_subject():
    subject = Subject(symbol="BEN.PA", name="beneteau", exchange="NASDAQ")
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        subject = Investing.search_subject(subject, headless=True)
        subject.save(Path(f.name))
        loaded_subject = subject.load(Path(f.name))
        assert loaded_subject
        assert loaded_subject.news
        assert loaded_subject.price_target_news


def test_search_subject_():
    subject = Subject(symbol="PLTR", name="palantir", exchange="NASDAQ")
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        subject = Investing.search_subject(subject, headless=True)
        subject.save(Path(f.name))
        loaded_subject = subject.load(Path(f.name))
        assert loaded_subject
        assert loaded_subject.news
        assert loaded_subject.price_target_news
