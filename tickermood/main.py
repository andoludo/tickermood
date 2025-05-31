import logging
from pathlib import Path
from typing import List, Type

from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from tickermood.agent import invoke_summarize_agent
from tickermood.source import BaseSource, Investing
from tickermood.subject import Subject, LLM, LLMSubject

logger = logging.getLogger(__name__)


class TickerMood(BaseModel):
    sources: List[Type[BaseSource]] = Field(default=[Investing])
    subjects: List[Subject]
    headless: bool = True
    database_path: Path = Field(default=Path.cwd() / "tickermood.db")
    llm: LLM = Field(
        default_factory=lambda: LLM(
            model_name="qwen3:4b", model_type=ChatOllama, temperature=0.0
        )
    )

    @classmethod
    def from_symbols(cls, symbols: List[str]) -> "TickerMood":
        subjects = [Subject(symbol=symbol) for symbol in symbols]
        return cls(subjects=subjects)

    def search(self) -> None:
        for subject in self.subjects:
            for source in self.sources:
                try:
                    subject = source.search_subject(  # noqa: PLW2901
                        subject, headless=self.headless
                    )
                except Exception as e:  # noqa: PERF203
                    logger.warning(
                        f"Error searching for subject {subject.symbol} in {source.name}: {e}"
                    )
                    continue
            subject.save(self.database_path)

    def call_agent(self) -> None:
        for subject in self.subjects:
            llm_subject = LLMSubject.from_subject(subject, self.llm)
            summarized_subject = invoke_summarize_agent(llm_subject)
            summarized_subject.save(self.database_path)

    def run(self) -> None:
        self.search()
        self.call_agent()
        logger.info("TickerMood run completed.")
