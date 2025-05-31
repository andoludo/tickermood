import json
import logging
import re
from typing import get_args, Type

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from tickermood.subject import Subject, LLMSubject, PriceTarget, Consensus
from tickermood.types import ConsensusType

logger = logging.getLogger(__name__)


def remove_tagged_text(text: str) -> str:
    pattern = r"<think>.*?</think>"
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()


def get_json_schema(model: Type[BaseModel]) -> str:

    return json.dumps(model.model_json_schema().get("properties", {}), indent=4)


def parse_json_output(model_response: str, model: Type[BaseModel]) -> BaseModel:
    parser = JsonOutputParser()
    try:
        parsed_output = parser.parse(remove_tagged_text(model_response))
        return model.model_validate(parsed_output)
    except Exception as e:
        logger.error(f"Failed to parse model response into {model.__name__}: {e}")
        return model()


def summarize(state: LLMSubject) -> LLMSubject:
    llm = state.get_model()
    system_message = SystemMessage(
        "You are a helpful assistant that summarizes financial articles. "
        "Reasoning, thought process, or annotations like <think>. "
        "Only return the final summary in plain text. No tags, no notes, no process."
        "Only few sentences."
    )
    article = state.get_next_article()
    if article:
        human_message = HumanMessage(
            "Summarize the following. Only return the summary.:\n\n" + article.content
        )
        response = llm.invoke([system_message, human_message])
        state.add_news_summary(remove_tagged_text(str(response.content)), article)
    return state


def has_more_articles(state: LLMSubject) -> bool:
    return state.get_next_article() is not None


def reduce(state: LLMSubject) -> LLMSubject:
    llm = state.get_model()
    system_message = SystemMessage(
        "You are a helpful and smart financial assistant that can summarizes finance articles."
    )
    human_message = HumanMessage(
        "Provide a concise summary of these articles. Is this stock a GO/NO-GO/Cautious?:\n\n"
        + state.combined_summary_news()
    )
    response = llm.invoke([system_message, human_message])
    state.add_summary(remove_tagged_text(str(response.content)))
    return state


def price_target(state: LLMSubject) -> LLMSubject:
    llm = state.get_model()
    system_message = SystemMessage(
        "You are a helpful assistant that summarizes financial articles."
    )
    human_message = HumanMessage(
        f"""Extract the high and low price target and give a summary of the text. 
        Return the answer strictly in this JSON format:
{get_json_schema(PriceTarget)}:\n\n"""
        + state.combined_price_target_news()
    )
    response = llm.invoke([system_message, human_message])
    state.add(parse_json_output(str(response.content), PriceTarget))
    return state


def get_consensus(state: LLMSubject) -> LLMSubject:
    llm = state.get_model()

    system_message = SystemMessage(
        "You are a helpful assistant that summarizes financial articles."
    )
    human_message = HumanMessage(
        f"Summarize the analyst consensus for the stock with symbol {state.symbol} and return using the following "
        f"JSON format:{get_json_schema(Consensus)}.\n\n"
        f"Note that the consensus field must be one of the following {list(get_args(ConsensusType))}\n\n"
        + state.get_consensus_data()
    )
    response = llm.invoke([system_message, human_message])
    state.add(parse_json_output(str(response.content), Consensus))
    return state


def summarize_agent() -> CompiledStateGraph:
    graph = StateGraph(LLMSubject)

    graph.add_node("summarize", summarize)
    graph.add_node("reduce", reduce)
    graph.add_node("price_target", price_target)
    graph.add_node("get_consensus", get_consensus)
    graph.set_entry_point("summarize")
    graph.add_conditional_edges(
        "summarize", has_more_articles, {True: "summarize", False: "reduce"}
    )
    graph.add_edge("reduce", "price_target")
    graph.add_edge("price_target", "get_consensus")

    graph.set_finish_point("get_consensus")

    return graph.compile()


def invoke_summarize_agent(subject: LLMSubject) -> Subject:

    graph = summarize_agent()
    subject = graph.invoke(subject)  # type: ignore
    return Subject.model_validate(subject)
