import tempfile
from pathlib import Path

from tickermood.subject import Subject


def test_subject() -> None:
    with tempfile.NamedTemporaryFile() as f:
        subject = Subject(symbol="AAPL", name="Apple Inc.", exchange="NASDAQ")
        subject.save(Path(f.name))
        loaded_subject = subject.load(Path(f.name))
        assert loaded_subject
        assert loaded_subject.symbol == "AAPL"
