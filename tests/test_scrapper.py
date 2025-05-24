from tickermood.source import Investing
from tickermood.subject import Subject


def test_investing_search():
    subject = Subject(    symbol="IQV", name="IQVIA Holdings Inc.", exchange="NYSE")
    investing = Investing.search(subject)
    assert investing is not None


def test_investing_news():
    subject = Subject(    symbol="IQV", name="IQVIA Holdings Inc.", exchange="NYSE")
    investing = Investing.search(subject)
    news = investing.news()
    assert news
    assert len(news) > 0
    assert all(n.content is not None for n in news)