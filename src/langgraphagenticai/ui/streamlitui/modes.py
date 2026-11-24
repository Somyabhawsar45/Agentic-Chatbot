"""Everything the UI shows about each mode, in one place."""

# internal value -> display info
MODES = {
    "Netra Agent": {
        "icon": "auto_awesome",
        "label": "Netra Agent",
        "caps": [("public", "Web search"), ("description", "Reads your PDFs"), ("psychology", "Remembers you"), ("route", "Picks its own tools")],
        "tagline": "Searches the web, reads your PDFs and remembers you, and decides how to answer each message.",
        "starters": [
            ("public", "What are the biggest AI announcements this week?"),
            ("psychology", "Remember that I prefer short, bullet-point answers"),
            ("table_chart", "Compare RAG and fine-tuning in a table"),
            ("person", "What do you remember about me?"),
        ],
        "pdf": True,
    },
    "Basic Chatbot": {
        "icon": "chat",
        "label": "Basic Chatbot",
        "caps": [("bolt", "Fast replies"), ("forum", "Multi-turn memory"), ("stream", "Streams as it types")],
        "tagline": "A fast, plain conversation with the model. No tools, just chat.",
        "starters": [
            ("school", "Explain transformers like I'm new to AI"),
            ("quiz", "Give me 5 interview questions on LangGraph"),
            ("edit_note", "Write a haiku about debugging at 2 AM"),
            ("flight", "Plan a relaxed 3-day trip to Goa"),
        ],
    },
    "Chatbot With Web": {
        "icon": "public",
        "label": "Web Search",
        "caps": [("public", "Live web results"), ("link", "Cited sources"), ("loop", "Up to 2 searches per question")],
        "tagline": "Live answers from the web with sources, powered by Tavily.",
        "starters": [
            ("bolt", "What's new with Groq this month?"),
            ("newspaper", "Today's top technology headlines"),
            ("sports_motorsports", "Who won the most recent Formula 1 race?"),
            ("currency_bitcoin", "What is the price of Bitcoin right now?"),
        ],
    },
    "Chat with PDF": {
        "icon": "description",
        "label": "Chat With PDF",
        "caps": [("description", "Page-cited answers"), ("format_quote", "Exact quoted passages"), ("lock", "Your file stays in your chat")],
        "tagline": "Ask questions about a document. Answers cite page numbers and quote the source passages.",
        "starters": [
            ("summarize", "Summarize this document in 5 bullet points"),
            ("format_list_numbered", "List the key findings with page numbers"),
            ("warning", "What risks or limitations does it mention?"),
            ("lightbulb", "Explain the conclusion in simple words"),
        ],
        "pdf": True,
    },
    "AI News": {
        "icon": "newspaper",
        "label": "News Summary",
        "caps": [("newspaper", "Many sources"), ("account_tree", "Map-reduce summary"), ("download", "Downloadable report")],
        "tagline": "A map-reduce digest of the latest AI news from across the web.",
        "starters": [
            ("today", "Daily"),
            ("date_range", "Weekly"),
            ("calendar_month", "Monthly"),
        ],
        "hints": ["What happened in AI this week?", "Any big model releases today?", "Latest AI news from India"],
    },
    "Deep Research": {
        "icon": "travel_explore",
        "label": "Deep Research",
        "caps": [("fact_check", "You approve the plan"), ("groups", "Parallel researchers"), ("rate_review", "Critic reviews the draft")],
        "tagline": "A team of agents: a planner, parallel researchers, a writer and a critic. You approve the plan before they start.",
        "starters": [
            ("bolt", "The future of small modular nuclear reactors"),
            ("smart_toy", "State of AI agents in 2026: tools, frameworks, adoption"),
            ("battery_charging_full", "Solid-state vs LFP batteries for EVs"),
            ("payments", "How UPI changed payments in India"),
        ],
    },
}

NAV_ORDER = ["Netra Agent", "Basic Chatbot", "Chatbot With Web", "Chat with PDF", "AI News", "Deep Research"]


def mode(usecase: str) -> dict:
    return MODES.get(usecase, {"icon": "chat", "label": usecase, "tagline": "", "starters": [], "caps": []})


def hints(usecase: str) -> list:
    """Example questions the empty message box types out for this mode."""
    info = mode(usecase)
    return info.get("hints") or [prompt for _, prompt in info.get("starters", [])]
