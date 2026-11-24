from typing import Literal, Optional

from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

from src.langgraphagenticai.tools.tavily_pool import RotatingTavilyClient


def get_tools(tavily_api_key=None):
    """
    The web search tool for the Netra Agent and Web Search modes. It rotates through the app's
    Tavily keys (TAVILY_API_KEY + TAVILY_API_KEYS) when one runs out; a visitor's own key is used
    on its own. Each graph gets its own client, so each user's key stays with their own graph.
    """
    client = RotatingTavilyClient(tavily_api_key)

    @tool
    def tavily_search(query: str, time_range: Optional[Literal["day", "week", "month", "year"]] = None) -> dict:
        """Search the web for current events, recent facts, prices or anything that may have changed.
        Use a short, specific query. Optionally limit results to the past day, week, month or year."""
        kwargs = {"time_range": time_range} if time_range else {}
        return client.search(query=query, max_results=2, topic="general", **kwargs)

    return [tavily_search]


def create_tool_node(tools):
    """
    creates and returns a tool node for the graph
    """
    return ToolNode(tools=tools)
