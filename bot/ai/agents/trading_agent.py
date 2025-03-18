from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from bot.ai.state.agent_state import AgentState
from bot.ai.tools.wallet_tools import show_wallet_info, export_wallet_key, withdraw_tokens,get_token_details
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage
import logging

logger = logging.getLogger(__name__)

# Define tools
tools = [show_wallet_info, export_wallet_key, withdraw_tokens,get_token_details]

# Initialize ChatGroq with the latest model
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.7,
    max_tokens=100
).bind_tools(tools)

# Define the chatbot node
async def chatbot(state: AgentState) -> AgentState:
    logger.info(f"Processing state: {state}")
    user_id = state["user_id"]
    messages = state["messages"]
    
    # Invoke the LLM with the current messages
    response = await llm.ainvoke(messages)
    
    if response.tool_calls:
        # Add the tool call message to the state
        messages.append(response)
        # Prepare tool calls with correct user_id
        for tool_call in response.tool_calls:
            tool_call["args"]["user_id"] = user_id  # Ensure user_id is correct
    else:
        messages.append(AIMessage(content=response.content))
    
    return {"messages": messages}

# Build the graph
graph_builder = StateGraph(AgentState)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", ToolNode(tools))

# Define edges
graph_builder.add_edge(START, "chatbot")
graph_builder.add_conditional_edges("chatbot", tools_condition, {"tools": "tools", END: END})
graph_builder.add_edge("tools", "chatbot")

# Add memory
memory = MemorySaver()
trading_agent = graph_builder.compile(checkpointer=memory)