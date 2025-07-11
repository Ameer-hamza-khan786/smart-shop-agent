# main.py
from .langgraph_agent import app
from .shared import AgentState, _db

if __name__ == "__main__":
    query = input("Enter your business question: ")
    result = app.invoke(
        {
            "question": query,
            "attempts": 0,
            "curr_question": "",
            "sql_query": "",
            "query_result": "",
            "relevance": False,
            "sql_error": [],
        }
    )

    print("\n" + "=" * 50)
    print(result["query_result"])
    print("=" * 50)

    _db._engine.dispose()
    print("🔌 Database connection closed.")
