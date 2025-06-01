import tempfile
from pathlib import Path

import pytest

from tickermood.main import TickerMood
from tickermood.subject import Subject


def test_subject() -> None:
    with tempfile.NamedTemporaryFile() as f:
        subject = Subject(symbol="AAPL", name="Apple Inc.", exchange="NASDAQ")
        subject.save(Path(f.name))
        loaded_subject = subject.load(Path(f.name))
        assert loaded_subject
        assert loaded_subject.symbol == "AAPL"


@pytest.mark.local
def test_tickermood() -> None:
    ticker_mood = TickerMood.from_symbols(["IQV", "GOOG", "VKTX"])
    ticker_mood.run()
    subject = ticker_mood.subjects[0]
