"""
Deep Research: a small multi-agent team built with LangGraph.

    START -> planner -> human_review --(Send x N, parallel)--> researcher -> writer -> critic
                                                                          ^          |
                                                                          +-- revise-+--> finalize -> END

* planner       splits the topic into focused web-search questions
* human_review  PAUSES the graph (interrupt) so the user can edit/approve the plan
* researcher  one agent per question, run in PARALLEL (LangGraph `Send` API):
              Tavily search + summarise into notes with numbered sources
* writer      writes a cited markdown report from all notes (or revises it)
* critic      reviews the draft; either approves or asks for one revision
* finalize    puts the report into the conversation
"""
import re
from datetime import date

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import Send, interrupt
from tavily import TavilyClient

from src.langgraphagenticai.state.state import ResearchState, ResearchTask

MAX_QUESTIONS = 4            # planner proposes up to this many
MAX_REVIEWED_QUESTIONS = 6   # the user may add a couple more when reviewing
MAX_REVISIONS = 1


def _text(response) -> str:
    content = getattr(response, "content", response)
    return content if isinstance(content, str) else str(content)


def parse_questions(text: str, limit: int = MAX_QUESTIONS) -> list:
    """Planner output (one question per line, maybe numbered/bulleted) -> clean list."""
    questions = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip().strip('"')
        if len(line) > 5:
            questions.append(line)
    return questions[:limit]


class ResearchTeam:
    def __init__(self, llm, tavily_api_key=None):
        self.llm = llm
        # api_key=None makes TavilyClient fall back to the TAVILY_API_KEY env var
        self.tavily = TavilyClient(api_key=tavily_api_key)

    # ---------------- PLANNER ----------------
    def planner(self, state: ResearchState) -> dict:
        topic = state["messages"][-1].content
        response = self.llm.invoke([
            SystemMessage(content=(
                f"You are a research planner. Today is {date.today().isoformat()}. "
                f"Break the user's topic into {MAX_QUESTIONS - 1} to {MAX_QUESTIONS} focused web-search "
                "queries that together cover it well (background, latest developments, numbers, "
                "different viewpoints). Return ONLY the queries, one per line, no numbering."
            )),
            HumanMessage(content=topic),
        ])
        plan = parse_questions(_text(response)) or [topic]
        return {"topic": topic, "plan": plan, "revisions": 0}

    # ---------------- HUMAN REVIEW (human-in-the-loop) ----------------
    def human_review(self, state: ResearchState) -> dict:
        """
        Pause the graph and hand the plan to the user. `interrupt()` stops here;
        the UI later resumes with Command(resume={"plan": [...edited questions...]}).
        """
        decision = interrupt({"topic": state.get("topic", ""), "plan": state.get("plan", [])})
        plan = state.get("plan", [])
        if isinstance(decision, dict) and decision.get("plan"):
            edited = [q.strip() for q in decision["plan"] if isinstance(q, str) and q.strip()]
            plan = edited[:MAX_REVIEWED_QUESTIONS] or plan
        return {"plan": plan}

    def dispatch(self, state: ResearchState) -> list:
        """Fan-out: one parallel researcher per planned question."""
        return [Send("researcher", {"query": q}) for q in state["plan"]]

    # ---------------- RESEARCHER (runs in parallel) ----------------
    def researcher(self, task: ResearchTask) -> dict:
        query = task["query"]
        try:
            results = self.tavily.search(query=query, max_results=3).get("results", [])
        except Exception as e:
            return {"findings": [{"query": query, "notes": f"(search failed: {e})", "sources": []}]}

        sources = [{"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
                   for r in results]
        material = "\n\n".join(
            f"[{i}] {s['title']} ({s['url']})\n{s['content'][:1500]}" for i, s in enumerate(sources, 1)
        )
        response = self.llm.invoke([
            SystemMessage(content=(
                "You are a research assistant. From the search results, write 3-6 concise factual "
                "bullet notes that answer the question. Keep numbers and dates. End each bullet with "
                "the source URL in parentheses. Do not invent facts."
            )),
            HumanMessage(content=f"Question: {query}\n\nSearch results:\n{material or '(no results)'}"),
        ])
        return {"findings": [{"query": query, "notes": _text(response), "sources": sources}]}

    # ---------------- WRITER ----------------
    def writer(self, state: ResearchState) -> dict:
        notes = "\n\n".join(f"### {f['query']}\n{f['notes']}" for f in state.get("findings", []))
        instructions = (
            "You are a report writer. Using ONLY the research notes, write a well-structured markdown "
            "report on the topic: a short summary first, then sections with headings, then a "
            "'Sources' list. Cite facts inline as markdown links to the source URLs. Be concise."
        )
        messages = [SystemMessage(content=instructions),
                    HumanMessage(content=f"Topic: {state['topic']}\n\nResearch notes:\n{notes}")]
        if state.get("draft") and state.get("critique"):
            messages.append(HumanMessage(content=(
                f"Here is your previous draft:\n{state['draft']}\n\n"
                f"Reviewer feedback:\n{state['critique']}\n\nRewrite the report fixing these issues."
            )))
        return {"draft": _text(self.llm.invoke(messages))}

    # ---------------- CRITIC ----------------
    def critic(self, state: ResearchState) -> dict:
        response = self.llm.invoke([
            SystemMessage(content=(
                "You are a strict reviewer. Check the report against the topic: is it accurate to the "
                "notes, complete, well cited and clear? If it is good, reply with exactly APPROVED. "
                "Otherwise reply with a short bullet list of concrete fixes."
            )),
            HumanMessage(content=f"Topic: {state['topic']}\n\nReport:\n{state['draft']}"),
        ])
        return {"critique": _text(response).strip(), "revisions": state.get("revisions", 0) + 1}

    def after_critic(self, state: ResearchState) -> str:
        approved = state.get("critique", "").upper().startswith("APPROVED")
        if approved or state.get("revisions", 0) > MAX_REVISIONS:
            return "finalize"
        return "writer"

    # ---------------- FINALIZE ----------------
    def finalize(self, state: ResearchState) -> dict:
        return {"messages": [AIMessage(content=state.get("draft", "I couldn't produce a report."))]}
