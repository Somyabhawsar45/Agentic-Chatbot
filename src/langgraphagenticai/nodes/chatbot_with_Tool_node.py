from src.langgraphagenticai.state.state import State
from src.langgraphagenticai.nodes.tool_limits import ANSWER_NOW, tools_exhausted

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
        llm_must_answer = self.llm.bind_tools(tools, tool_choice="none")

        def chatbot_node(state: State):
            """
            Chatbot logic for processing the input state and returning a response.
            After MAX_TOOL_ROUNDS searches the LLM must answer (prevents search loops).
            """
            if tools_exhausted(state["messages"]):
                return {"messages": [llm_must_answer.invoke(state["messages"] + [ANSWER_NOW])]}
            return {"messages": [llm_with_tools.invoke(state["messages"])]}

        return chatbot_node
