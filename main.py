# main.py (project root)
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List

from agents.rag_agent.langgraph_agent import agent as rag_agent
from agents.sql_agent.langgraph_agent import agent as sql_agent
from agents.rag_agent.shared import AgentState as RagAgentState
from agents.sql_agent.shared import AgentState as SQLAgentState
from langchain_core.messages import HumanMessage

app = FastAPI(title="LangGraph Agent Hub")


# Request schema for unified endpoint
class QueryInput(BaseModel):
    question: str
    agent_type: str  # "rag" or "sql"


@app.post("/agent/execute")
def run_agent(query: QueryInput):
    user_message = HumanMessage(content=query.question)
    if query.agent_type == "rag":
        initial_state: AgentState = {
            "messages": user_message,
            "route": "rag",  # Start with RAG lookup
            "rag": "",
            "web": "",
            "Rag_Citation": None,
            "Web_Citation": None,
        }
        final_state = rag_agent.invoke(initial_state)

    elif query.agent_type == "sql":
        initial_state: SQLAgentState = {
            "question": query.question,
            "attempts": 0,
            "curr_question": "",
            "sql_query": "",
            "query_result": "",
            "relevance": False,
            "sql_error": [],
        }
        final_state = sql_agent.invoke(initial_state)

    else:
        return {"error": "Invalid agent_type. Use 'rag' or 'sql'."}

    if query.agent_type == "rag":
        return {"response": [msg.content for msg in final_state["messages"]]}
    else:
        return {"response": final_state.get("query_result", "No response generated")}


@app.get("/")
def root():
    return {"message": "LangGraph Agent API is running."}
