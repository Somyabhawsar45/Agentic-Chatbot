from langchain_tavily import TavilySearch
from langgraph.prebuilt import ToolNode


def get_tools(tavily_api_key=None):
    """
    Return the list of tools to be used in the chatbot.
    The key is passed explicitly (not via os.environ) so each user's key stays
    with their own graph; with no key, TavilySearch falls back to the env var.
    """
    kwargs = {"tavily_api_key": tavily_api_key} if tavily_api_key else {}
    tools = [TavilySearch(max_results=2, topic="general", **kwargs)]
    return tools


def create_tool_node(tools):
    """
    creates and returns a tool node for the graph
    """
    return ToolNode(tools=tools)
