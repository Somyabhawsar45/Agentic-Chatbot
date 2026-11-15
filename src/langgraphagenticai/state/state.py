import operator
from typing import Annotated, List

from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class State(TypedDict):
    """
    Represent the structure of the state used in graph
    """
    messages: Annotated[List, add_messages]
    context: str
    citations: list   # PDF passages used for the latest answer: {"text", "page", "source"}


class AINewsState(TypedDict, total=False):
    """
    State for the AI News pipeline. Every intermediate value lives here (not on
    the node object), so concurrent users of the shared, cached graph can't
    overwrite each other's data.
    """
    messages: Annotated[List, add_messages]
    frequency: str
    news_data: list
    summary: str


class ResearchState(TypedDict, total=False):
    """
    State for the Deep Research multi-agent graph.
    `findings` uses operator.add so the parallel researcher agents can each
    append their result without overwriting each other.
    """
    messages: Annotated[List, add_messages]
    topic: str
    plan: list                                  # sub-questions from the planner
    findings: Annotated[list, operator.add]     # one entry per researcher
    draft: str
    critique: str
    revisions: int


class ResearchTask(TypedDict):
    """Payload sent (via Send) to each parallel researcher."""
    query: str
