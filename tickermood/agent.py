import re

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from tickermood.subject import Subject, LLMSubject, PriceTarget


def remove_tagged_text(text):
    pattern = rf"<think>.*?</think>"
    return re.sub(pattern, "", text, flags=re.DOTALL).strip()


def summarize(state: LLMSubject) -> LLMSubject:
    llm = state.get_model()
    system_message = SystemMessage(
        "You are a helpful assistant that summarizes financial articles. Reasoning, thought process, or annotations like <think>. Only return the final summary in plain text. No tags, no notes, no process."
        "Only few sentences."
    )
    article = state.get_next_article()
    if article:
        human_message = HumanMessage(
            "Summarize the following. Only return the summary.:\n\n" + article.content
        )
        response = llm.invoke([system_message, human_message])
        state.add_news_summary(response.content, article)
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
        + state.combined_news()
    )
    response = llm.invoke([system_message, human_message])
    state.add_summary(remove_tagged_text(response.content))
    return state


def price_target(state: LLMSubject) -> LLMSubject:
    llm = state.get_model()
    chain = llm.with_structured_output(PriceTarget)
    system_message = SystemMessage(
        "You are a helpful assistant that summarizes financial articles."
    )
    human_message = HumanMessage(
        "Extract the high and low price target and give a summary of the text:\n\n"
        + state.combined_price_target_news()
    )
    response = chain.invoke([system_message, human_message])
    state.add_price_target(response)
    return state


def summarize_agent() -> CompiledStateGraph:
    graph = StateGraph(LLMSubject)

    graph.add_node("summarize", summarize)
    graph.add_node("reduce", reduce)
    graph.add_node("price_target", price_target)
    graph.set_entry_point("summarize")
    graph.add_conditional_edges(
        "summarize", has_more_articles, {True: "summarize", False: "reduce"}
    )
    graph.add_edge("reduce", "price_target")

    graph.set_finish_point("price_target")

    return graph.compile()
