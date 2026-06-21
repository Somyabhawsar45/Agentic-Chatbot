from tavily import TavilyClient
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage


class AINewsNode:
    def __init__(self, llm):
        self.tavily = TavilyClient()
        self.llm = llm
        self.state = {}

    # ==========================================================
    # FETCH NEWS
    # ==========================================================
    def fetch_news(self, state: dict) -> dict:
        try:
            frequency = state["messages"][0].content.lower().strip()
        except Exception:
            return {
                "messages": AIMessage(
                    content="⚠️ Please select a valid timeframe (Daily / Weekly / Monthly)."
                )
            }

        time_range_map = {
            "daily": "d",
            "weekly": "w",
            "monthly": "m",
        }

        days_map = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30,
        }

        if frequency not in time_range_map:
            return {
                "messages": AIMessage(
                    content="⚠️ Invalid timeframe selected."
                )
            }

        self.state["frequency"] = frequency

        response = self.tavily.search(
            query="Latest Artificial Intelligence (AI) news India and globally",
            topic="news",
            time_range=time_range_map[frequency],
            max_results=12,   # 🔴 LIMIT RESULTS
            days=days_map[frequency],
        )

        self.state["news_data"] = response.get("results", [])
        return state

    # ==========================================================
    # MAP STEP — SUMMARIZE EACH ARTICLE (SAFE)
    # ==========================================================
    def summarize_news(self, state: dict) -> dict:
        news_items = self.state.get("news_data", [])

        if not news_items:
            self.state["summary"] = "⚠️ No news articles found."
            return self.state

        individual_summaries = []

        map_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "Summarize the following AI news article in 2–3 concise bullet points."),
            ("user", "{article}")
        ])

        # 🔹 MAP: summarize each article separately
        for item in news_items[:10]:   # 🔴 HARD LIMIT
            article_text = (
                f"Title: {item.get('title','')}\n"
                f"Content: {item.get('content','')}\n"
                f"URL: {item.get('url','')}"
            )

            response = self.llm.invoke(
                map_prompt.format(article=article_text)
            )

            individual_summaries.append(
                f"- {response.content.strip()}"
            )

        # ======================================================
        # REDUCE STEP — FINAL SUMMARY
        # ======================================================
        reduce_prompt = ChatPromptTemplate.from_messages([
            ("system",
             """
             Combine the following AI news summaries into a clean markdown report.

             Rules:
             - Group similar topics
             - Keep it concise
             - Use headings
             """),
            ("user", "{summaries}")
        ])

        final_response = self.llm.invoke(
            reduce_prompt.format(
                summaries="\n".join(individual_summaries)
            )
        )

        self.state["summary"] = final_response.content
        return self.state

    # ==========================================================
    # SAVE RESULT
    # ==========================================================
    def save_result(self, state: dict) -> dict:
        frequency = self.state.get("frequency", "news")
        summary = self.state.get("summary", "")

        filename = f"./AINews/{frequency}_summary.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {frequency.capitalize()} AI News Summary\n\n")
            f.write(summary)

        self.state["filename"] = filename
        return self.state