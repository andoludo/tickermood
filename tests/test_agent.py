import json
import os
import tempfile
from pathlib import Path
from typing import Optional, List

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ChatMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.runnables import Runnable
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from tickermood.agent import invoke_summarize_agent
from tickermood.articles import News, PriceTargetNews
from tickermood.main import get_news
from tickermood.subject import LLMSubject, Subject, LLM
from tickermood.types import DatabaseConfig


class FakeLLM(BaseChatModel):
    def __init__(self, model: str, temperature: float = 0.0):
        super().__init__()

    def _generate(
        self, messages: List[ChatMessage], stop: Optional[List[str]] = None
    ) -> ChatResult:
        ai_message = AIMessage(content="This is a summary")

        return ChatResult(generations=[ChatGeneration(message=ai_message)])

    @property
    def _llm_type(self) -> str:
        return "fake-llm"

    def reset(self):
        self._counter = 0

    def bind_tools(self, tools, tool_choice=None, **kwargs):
        class SimpleRunnable(Runnable):
            def invoke(self, input, config=None):
                response = {
                    "tasks": [
                        {
                            "high_price_target": 100.0,
                            "low_price_target": 200,
                        }
                    ]
                }

                return AIMessage(
                    content="",
                    additional_kwargs={
                        "tool_calls": [
                            {
                                "id": "tool1",
                                "type": "function",
                                "function": {
                                    "name": (
                                        tools[0].__name__
                                        if hasattr(tools[0], "__name__")
                                        else "mock_tool"
                                    ),
                                    "arguments": json.dumps(response),
                                },
                            }
                        ]
                    },
                )

        return SimpleRunnable()


def test_summarize_agent():
    subject = LLMSubject(
        symbol="fake",
        name="Fake Subject",
        exchange="FAKE",
        model_type=FakeLLM,
        model_name="Fake LLM",
        price_target_news=[
            PriceTargetNews(
                source="Investing",
                content="This is a test article.",
                url="http://example.com/test1",
                title="Test Article",
            )
        ],
        news=[
            News(
                source="Investing",
                content="This is a test article.",
                url="http://example.com/test1",
                title="Test Article",
            ),
            News(
                source="Investing",
                content="This is a test article.",
                url="http://example.com/test2",
                title="Test Article",
            ),
        ],
    )
    result_subject = invoke_summarize_agent(subject)
    assert result_subject


@pytest.mark.local_llm
def test_summarize_agent_llm_gemma(palantir_subject: Subject) -> None:
    with tempfile.NamedTemporaryFile() as f:
        database_path = Path(f.name)
        database_config = DatabaseConfig(database_path=database_path)
        palantir_subject.save(database_config)
        loaded_subject = palantir_subject.load(database_config)
        llm = LLM(model_name="gemma3:4b", model_type=ChatOllama, temperature=0.0)
        subject = LLMSubject.from_subject(loaded_subject, llm)
        result_subject = invoke_summarize_agent(subject)
        result_subject.save(database_config)
        loaded_subject = subject.load(database_config)
        assert loaded_subject
        assert loaded_subject.symbol == "TEST"


@pytest.mark.local_llm
def test_summarize_agent_llm_qwen(palantir_subject: Subject) -> None:
    with tempfile.NamedTemporaryFile() as f:
        database_path = Path(f.name)
        database_config = DatabaseConfig(database_path=database_path)
        palantir_subject.save(database_config)
        loaded_subject = palantir_subject.load(database_config)
        llm = LLM(model_name="qwen3:4b", model_type=ChatOllama, temperature=0.0)
        subject = LLMSubject.from_subject(loaded_subject, llm)

        result_subject = invoke_summarize_agent(subject)

        result_subject.save(database_config)
        loaded_subject = subject.load(database_config)
        assert loaded_subject
        assert loaded_subject.symbol == "TEST"


@pytest.mark.local_llm
def test_summarize_agent_llm_qwen(palantir_subject: Subject) -> None:
    with tempfile.NamedTemporaryFile() as f:
        database_path = Path(f.name)
        database_config = DatabaseConfig(database_path=database_path)
        palantir_subject.save(database_config)
        loaded_subject = palantir_subject.load(database_config)
        llm = LLM(model_name="qwen3:4b", model_type=ChatOllama, temperature=0.0)
        subject = LLMSubject.from_subject(loaded_subject, llm)

        result_subject = invoke_summarize_agent(subject)

        result_subject.save(database_config)
        loaded_subject = subject.load(database_config)
        assert loaded_subject
        assert loaded_subject.symbol == "TEST"


@pytest.mark.local_llm
def test_summarize_agent_llm_chat_gpt(palantir_subject: Subject) -> None:
    with tempfile.NamedTemporaryFile() as f:
        database_path = Path(f.name)
        database_config = DatabaseConfig(database_path=database_path)
        palantir_subject.save(database_config)
        loaded_subject = palantir_subject.load(database_config)
        llm = LLM(model_name="gpt-4o-mini", model_type=ChatOpenAI, temperature=0.0)
        subject = LLMSubject.from_subject(loaded_subject, llm)

        result_subject = invoke_summarize_agent(subject)

        result_subject.save(database_config)
        loaded_subject = subject.load(database_config)
        assert loaded_subject
        assert loaded_subject.symbol == "TEST"


@pytest.mark.local_llm
def test_get_news() -> None:
    os.environ["OPENAI_API_KEY"] = "***"
    symbols = ["VKTX"]
    database_config = DatabaseConfig(
        database_path=Path.cwd() / "tickermood_get_news.db"
    )
    get_news(symbols, database_config, headless=False)
