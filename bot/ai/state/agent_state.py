from typing import Annotated
from langgraph.graph import MessagesState
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages

# Custom state with messages managed by add_messages
class AgentState(MessagesState):
    # messages is inherited from MessagesState and annotated with add_messages
    messages: Annotated[list[AnyMessage], add_messages]
    output: str  # Keep output for the final response