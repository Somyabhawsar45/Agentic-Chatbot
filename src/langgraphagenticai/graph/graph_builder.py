from langgraph.graph import StateGraph
from src.langgraphagenticai.state.state import State, AINewsState
from langgraph.graph import START,END
from src.langgraphagenticai.nodes.basic_chatbot_node import BasicChatbotNode
from src.langgraphagenticai.tools.search_tool import get_tools,create_tool_node
from langgraph.prebuilt import tools_condition
from src.langgraphagenticai.nodes.chatbot_with_Tool_node import ChatbotWithToolNode
from src.langgraphagenticai.nodes.ai_news_node import AINewsNode


class GraphBuilder:
    def __init__(self, model, tavily_api_key=None):
        self.llm=model
        self.tavily_api_key = tavily_api_key
        self.graph_builder=StateGraph(State)
        self.checkpointer = None  # only the Netra Agent uses LangGraph memory

    def netra_agent_build_graph(self):
        """
        The unified Netra Agent (ReAct loop with long-term memory):

            START -> agent --(tool calls?)--> tools -> agent -> ... -> END

        The agent LLM decides on every turn whether to answer directly, search
        the web, search the PDF attached to the conversation, or save a fact to
        the user's long-term memory.

        Two kinds of memory:
          * short-term: the checkpointer stores each conversation (thread_id)
          * long-term:  `save_memory` stores user facts shared by ALL conversations
        """
        from src.langgraphagenticai.nodes.netra_agent_node import NetraAgentNode
        from src.langgraphagenticai.tools.pdf_tool import search_pdf
        from src.langgraphagenticai.tools.memory_tool import save_memory
        from src.langgraphagenticai.memory.checkpointer import get_checkpointer

        web_tools = get_tools(self.tavily_api_key) if self.tavily_api_key else []
        pdf_tools = [search_pdf]
        memory_tools = [save_memory]

        agent = NetraAgentNode(self.llm, web_tools=web_tools, pdf_tools=pdf_tools, memory_tools=memory_tools)

        self.graph_builder.add_node("agent", agent.process)
        self.graph_builder.add_node("tools", create_tool_node(web_tools + pdf_tools + memory_tools))
        self.graph_builder.add_edge(START, "agent")
        self.graph_builder.add_conditional_edges("agent", tools_condition)
        self.graph_builder.add_edge("tools", "agent")

        self.checkpointer = get_checkpointer()

    def basic_chatbot_build_graph(self):
        """
        Builds a basic chatbot graph using LangGraph.
        This method initializes a chatbot node using the `BasicChatbotNode` class 
        and integrates it into the graph. The chatbot node is set as both the 
        entry and exit point of the graph.
        """

        self.basic_chatbot_node=BasicChatbotNode(self.llm)

        self.graph_builder.add_node("chatbot",self.basic_chatbot_node.process)
        self.graph_builder.add_edge(START,"chatbot")
        self.graph_builder.add_edge("chatbot",END)

    def pdf_rag_build_graph(self, conversation_id):
        """
        Builds a graph for PDF-based RAG question answering.
        """
        from src.langgraphagenticai.nodes.pdf_rag_node import PdfRagNode
        pdf_rag_node = PdfRagNode(self.llm, conversation_id)

        self.graph_builder.add_node("pdf_rag", pdf_rag_node.process)
        self.graph_builder.add_edge(START, "pdf_rag")
        self.graph_builder.add_edge("pdf_rag", END)


    def chatbot_with_tools_build_graph(self):
        """
        Builds an advanced chatbot graph with tool integration.
        This method creates a chatbot graph that includes both a chatbot node 
        and a tool node. It defines tools, initializes the chatbot with tool 
        capabilities, and sets up conditional and direct edges between nodes. 
        The chatbot node is set as the entry point.
        """
        ## Define the tool and tool node
        tools=get_tools(self.tavily_api_key)
        tool_node=create_tool_node(tools)

        ## Define the LLM
        llm=self.llm

        ## Define the chatbot node

        obj_chatbot_with_node=ChatbotWithToolNode(llm)
        chatbot_node=obj_chatbot_with_node.create_chatbot(tools)
        ## Add nodes
        self.graph_builder.add_node("chatbot",chatbot_node)
        self.graph_builder.add_node("tools",tool_node)
        # Define conditional and direct edges
        self.graph_builder.add_edge(START,"chatbot")
        self.graph_builder.add_conditional_edges("chatbot",tools_condition)
        self.graph_builder.add_edge("tools","chatbot")


    def ai_news_builder_graph(self):
        # AI News carries its intermediate data in its own state schema
        self.graph_builder = StateGraph(AINewsState)

        ai_news_node=AINewsNode(self.llm, self.tavily_api_key)

        ## added the nodes

        self.graph_builder.add_node("fetch_news",ai_news_node.fetch_news)
        self.graph_builder.add_node("summarize_news",ai_news_node.summarize_news)
        self.graph_builder.add_node("save_result",ai_news_node.save_result)

        #added the edges

        self.graph_builder.set_entry_point("fetch_news")
        self.graph_builder.add_edge("fetch_news","summarize_news")
        self.graph_builder.add_edge("summarize_news","save_result")
        self.graph_builder.add_edge("save_result", END)

    def deep_research_build_graph(self):
        """
        Multi-agent Deep Research with a human in the loop:

            planner -> human_review (interrupt: user edits/approves the plan)
                    -> researcher x N (parallel, Send API) -> writer <-> critic -> finalize

        Researchers' findings are merged by the `operator.add` reducer in ResearchState.
        `interrupt` needs a checkpointer to pause and later resume the run.
        """
        from src.langgraphagenticai.state.state import ResearchState
        from src.langgraphagenticai.nodes.research_nodes import ResearchTeam
        from src.langgraphagenticai.memory.checkpointer import get_checkpointer

        team = ResearchTeam(self.llm, self.tavily_api_key)
        self.graph_builder = StateGraph(ResearchState)

        self.graph_builder.add_node("planner", team.planner)
        self.graph_builder.add_node("human_review", team.human_review)
        self.graph_builder.add_node("researcher", team.researcher)
        self.graph_builder.add_node("writer", team.writer)
        self.graph_builder.add_node("critic", team.critic)
        self.graph_builder.add_node("finalize", team.finalize)

        self.graph_builder.add_edge(START, "planner")
        self.graph_builder.add_edge("planner", "human_review")
        self.graph_builder.add_conditional_edges("human_review", team.dispatch, ["researcher"])
        self.graph_builder.add_edge("researcher", "writer")
        self.graph_builder.add_edge("writer", "critic")
        self.graph_builder.add_conditional_edges("critic", team.after_critic, ["writer", "finalize"])
        self.graph_builder.add_edge("finalize", END)

        self.checkpointer = get_checkpointer()

    def setup_graph(self, usecase: str, conversation_id=None):
        """
        Sets up the graph for the selected use case.
        """
        if usecase == "Netra Agent":
            self.netra_agent_build_graph()
        if usecase == "Deep Research":
            self.deep_research_build_graph()
        if usecase == "Basic Chatbot":
            self.basic_chatbot_build_graph()
        if usecase == "Chatbot With Web":
            self.chatbot_with_tools_build_graph()
        if usecase == "AI News":
            self.ai_news_builder_graph()
        if usecase == "Chat with PDF":
            self.pdf_rag_build_graph(conversation_id)

        return self.graph_builder.compile(checkpointer=self.checkpointer)
