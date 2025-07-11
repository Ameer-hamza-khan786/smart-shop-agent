from .langgraph_agent import agent
from .shared import AgentState
from langchain_core.messages import HumanMessage


if __name__ == "__main__":
    user_question = input("Enter your question: ")

    # Initialize the agent with an empty state
    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_question)],
        "route": "rag",  # Start with RAG lookup
        "rag": "",
        "web": "",
        "Rag_Citation": None,
        "Web_Citation": None,
    }

    # Run the agent with the initial state
    final_state = agent.invoke(initial_state)

    # Print the final messages from the agent
    for message in final_state["messages"]:
        print(message.content)

    print("source files:", final_state.get("Rag_Citation", []))

    print("web sources:", final_state.get("Web_Citation", []))
