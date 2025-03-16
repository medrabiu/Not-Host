from langgraph.graph import StateGraph, END
from bot.ai.state.agent_state import AgentState
from bot.ai.prompts.trading_prompts import TRADING_PROMPT
from bot.ai.groq_client import query_groq
from langchain_core.messages import HumanMessage, AIMessage
import logging

logger = logging.getLogger(__name__)

def process_input(state: AgentState) -> AgentState:
    logger.info(f"Processing state: {state}")
    
    # Get the latest user input (last message)
    user_input = state["messages"][-1].content if state["messages"] else "Hi"
    
    # Format history for the prompt
    history = "\n".join(
        [f"{msg.type}: {msg.content}" for msg in state["messages"][:-1]]
    ) if len(state["messages"]) > 1 else "No chit-chat yet!"
    
    # Query Groq
    prompt = TRADING_PROMPT.format(history=history, input=user_input)
    response = query_groq(prompt)
    
    # Update state
    state["output"] = response
    state["messages"].append(AIMessage(content=response))
    
    logger.info(f"Processed input '{user_input}' with output '{response}'")
    return state

# Build the graph
graph = StateGraph(AgentState)
graph.add_node("process", process_input)
graph.set_entry_point("process")
graph.add_edge("process", END)

trading_agent = graph.compile()