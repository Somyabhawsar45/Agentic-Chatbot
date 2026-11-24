from tavily import TavilyClient

from src.langgraphagenticai.tools.tavily_pool import RotatingTavilyClient
from src.langgraphagenticai.nodes.tool_limits import invoke_plain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage

from src.langgraphagenticai.state.state import AINewsState


TIME_RANGE_MAP = {"daily": "d", "weekly": "w", "monthly": "m"}
DAYS_MAP = {"daily": 1, "weekly": 7, "monthly": 30}


class AINewsNode:
    """
    Map-reduce AI news pipeline: fetch -> summarize each article -> combine.

    The node object holds only the LLM and Tavily client. All per-request data
    flows through the graph state, so the node is safe to share between users.
    """

    def __init__(self, llm, tavily_api_key=None):
        # the app's Tavily keys in turn (TAVILY_API_KEY + TAVILY_API_KEYS), or the visitor's own key
        self.tavily = RotatingTavilyClient(tavily_api_key, client_factory=TavilyClient)
        self.llm = llm

    # ==========================================================
    # FETCH NEWS
    # ==========================================================
    def fetch_news(self, state: AINewsState) -> dict:
        try:
            frequency = state["messages"][-1].content.lower().strip()
        except Exception:
            return {"news_data": [], "summary": "⚠️ Please select a valid timeframe (Daily / Weekly / Monthly)."}

        if frequency not in TIME_RANGE_MAP:
            return {"news_data": [], "summary": "⚠️ Invalid timeframe selected."}

        response = self.tavily.search(
            query="Latest Artificial Intelligence (AI) news India and globally",
            topic="news",
            time_range=TIME_RANGE_MAP[frequency],
            max_results=12,
            days=DAYS_MAP[frequency],
        )

        return {"frequency": frequency, "news_data": response.get("results", [])}

    # ==========================================================
    # MAP STEP — SUMMARIZE EACH ARTICLE, REDUCE STEP — COMBINE
    # ==========================================================
    def summarize_news(self, state: AINewsState) -> dict:
        if state.get("summary"):  # fetch_news already reported a problem
            return {"summary": state["summary"]}

        news_items = state.get("news_data") or []
        if not news_items:
            return {"summary": "⚠️ No news articles found."}

        map_prompt = ChatPromptTemplate.from_messages([
            ("system", "Summarize the following AI news article in 2–3 concise bullet points."),
            ("user", "{article}"),
        ])

        individual_summaries = []
        for item in news_items[:10]:  # hard limit to control cost/latency
            article_text = (
                f"Title: {item.get('title', '')}\n"
                f"Content: {item.get('content', '')}\n"
                f"URL: {item.get('url', '')}"
            )
            response = invoke_plain(self.llm, map_prompt.format(article=article_text))
            individual_summaries.append(f"- {response.content.strip()}")

        reduce_prompt = ChatPromptTemplate.from_messages([
            ("system",
             """
             Combine the following AI news summaries into a clean markdown report.

             Rules:
             - Group similar topics
             - Keep it concise
             - Use headings
             """),
            ("user", "{summaries}"),
        ])

        final_response = invoke_plain(self.llm, 
            reduce_prompt.format(summaries="\n".join(individual_summaries))
        )
        return {"summary": final_response.content}

    # ==========================================================
    # SAVE RESULT — put the report into the conversation
    # ==========================================================
    def save_result(self, state: AINewsState) -> dict:
        frequency = state.get("frequency") or "news"
        report = f"# {frequency.capitalize()} AI News Summary\n\n{state.get('summary', '')}"
        return {"messages": [AIMessage(content=report)]}
