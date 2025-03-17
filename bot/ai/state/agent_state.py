from typing import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: int