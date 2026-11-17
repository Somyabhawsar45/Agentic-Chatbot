from src.langgraphagenticai.state.state import State
from src.langgraphagenticai.nodes.tool_limits import answer_without_tools, tools_exhausted

class ChatbotWithToolNode:
    """
    Chatbot logic enhanced with tool integration.
    """
    def __init__(self,model):
        self.llm = model

    def create_chatbot(self, tools):
        """
        Returns a chatbot node function.
        """
        llm_with_tools = self.llm.bind_tools(tools)

        def chatbot_node(state: State):
            """
            Chatbot logic for processing the input state and returning a response.
            After MAX_TOOL_ROUNDS searches the model must answer with no tools available (prevents search loops).
            """
            if tools_exhausted(state["messages"]):
                return {"messages": [answer_without_tools(self.llm, state["messages"])]}
            return {"messages": [llm_with_tools.invoke(state["messages"])]}

        return chatbot_node
