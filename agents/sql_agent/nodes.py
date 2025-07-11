# nodes.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from .shared import (
    AgentState,
    get_schema,
    GLOBAL_LLM,
    _db,
    CheckRelevance,
    ConvertToSQL,
    HumanAnswer,
    RewrittenQuestion,
)
from .tools import format_sql_results


def check_relevance(state: AgentState):
    print(f"Checking relevance of the question: {state['question']}")
    schema = get_schema()
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a database schema analyst... which analyze the 
             scheme : {schema} 
             
             and determine if the question is relevant to the schema. 
             
             answer with a boolean value only,
             True if relevant, False if not.""",
            ),
            ("human", "Question: {question}"),
        ]
    )
    try:
        result = (prompt | GLOBAL_LLM.with_structured_output(CheckRelevance)).invoke(
            {
                "schema": schema,
                "question": state["question"],
            }
        )
        state.update(
            {
                "relevance": result.is_relevant,
                "curr_question": state["question"],
                "sql_error": [],
            }
        )
    except Exception as e:
        state.update(
            {
                "query_result": f"⚠️ Error checking relevance: {str(e)}",
                "relevance": False,
            }
        )

    print(f"Relevance determined: {state['relevance']}")
    return state


def convert_nl_to_sql(state: AgentState):
    print(f"Converting question to SQL: {state['question']}")
    schema = get_schema()
    error_context = (
        "\nList of SQL Error you done previously : " + str(state["sql_error"])
        if state["sql_error"]
        else "None"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are an expert PostgreSQL query generator. Convert this natural language question into a valid PostgreSQL SELECT statement using schema info.

Database Schema:
{schema}

{error_context}

curr_timestamp: {timestamp}

Rules:
1. Only generate SELECT queries.
2. Use JOINs properly.
3. Use table aliases.
4. use LIMIT unless important to get full result.
5. Return only the SQL query, no explanation.
6. do learn from past errors and improve the query.
6. use today's timestamp in the query if needed.
""",
            ),
            ("human", "Question: {curr_question}"),
        ]
    )

    try:
        result = (prompt | GLOBAL_LLM.with_structured_output(ConvertToSQL)).invoke(
            {
                "curr_question": state["curr_question"],
                "schema": schema,
                "error_context": error_context,
                "timestamp": datetime.now().isoformat(),
            }
        )
        state["sql_query"] = result.sql_query.strip()
    except Exception as e:
        state.update(
            {
                "sql_error": [f"SQL generation failed: {str(e)}"],
                "query_result": f"❌ Failed to generate SQL: {str(e)}",
                "attempts": state["attempts"] + 1,
            }
        )
    print(f"✅ Generated SQL query:\n{state['sql_query']}")

    return state


def execute_sql(state: AgentState):
    if not state["sql_query"]:
        state["query_result"] = "No SQL query to execute"
        return state

    sql_query = state["sql_query"].strip()
    print(f"🔍 Executing SQL query:\n{sql_query}")

    if not sql_query.lower().startswith("select"):
        state.update(
            {
                "query_result": "❌ Only SELECT queries allowed",
                "sql_error": ["Disallowed query type"],
                "attempts": state["attempts"] + 1,
            }
        )
        return state

    try:
        result = _db.run(sql_query)
        state.update({"query_result": format_sql_results(result), "sql_error": []})
        print("✅ SQL SELECT executed successfully.")

    except SQLAlchemyError as e:
        state.update(
            {
                "query_result": f"❌ SQL Error: {str(e)}",
                "sql_error": [str(e)],
                "attempts": state["attempts"] + 1,
            }
        )

        print(f"❌ SQL execution failed: {e}")

    return state


def generate_human_readable_answer(state: AgentState):
    if not state["query_result"]:
        state["query_result"] = "No results to explain"
        return state

    if len(state["query_result"]) > 1000:  # Limit to avoid too long outputs
        return state

    print("📄 Generating human-readable summary...")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a data analyst explaining database results to a shop owner...""",
            ),
            (
                "human",
                f"Question: {state['curr_question']}\nData:\n{state['query_result']}",
            ),
        ]
    )

    try:
        result = (prompt | GLOBAL_LLM.with_structured_output(HumanAnswer)).invoke(
            {
                "curr_question": state["curr_question"],
                "query_result": state["query_result"],
            }
        )
        state["query_result"] = (
            f"🔍 Results:\n{state['query_result']}\n\n💡 Insights:\n{result.answer}"
        )

        print("✅ Human-readable summary added.")
    except Exception as e:
        print(f"❌ Failed to generate human explanation due to --> : {e}")
        state["query_result"] += f"\n(⚠️ Couldn't generate insights: {str(e)})"

    return state


def regenerate_query(state: AgentState):
    print(
        "🔄 Regenerating the SQL query by reformulating the question based on error feedback..."
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Improve this question for better SQL query generation based on error feedback {error} 
             and schema {schema}.""",
            ),
            ("human", "Original: {question}"),
        ]
    )
    try:
        result = (prompt | GLOBAL_LLM.with_structured_output(RewrittenQuestion)).invoke(
            {
                "schema": get_schema(),
                "error": str(state["sql_error"]) if state["sql_error"] else "No error",
                "question": state["curr_question"],
            }
        )
        state.update({"curr_question": result.question.strip(), "sql_query": ""})
        print(f"✅ Rewritten question: {result.question}")

    except Exception as e:
        print(f"❌ Failed to rewrite question: {e}")
        state.update(
            {
                "sql_error": [f"Question rewrite failed: {str(e)}"],
                "attempts": state["attempts"] + 1,
            }
        )
    return state


def generate_funny_response(state: AgentState):
    print(
        "🎭 Generating a funny but helpful response for an unrelated or irrelevant question..."
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are a assistant which sorry for not being able to answer the question,
                tell him some examples of question he can ask that you can answer
                for given schema {schema}""",
            ),
            ("human", "Question: {question}"),
        ]
    )
    try:
        result = (prompt | GLOBAL_LLM | StrOutputParser()).invoke(
            {
                "question": state["question"],
                "schema": get_schema(),
            }
        )
        print("✅ Funny helper response generated.")
        state["query_result"] = result
    except Exception:
        print(f"❌ Failed to generate funny response: {e}")
        state["query_result"] = (
            "I'd make a joke, but I'm all queried out! Try asking about our products or sales."
        )
    return state


def end_max_iterations(state: AgentState):
    state["query_result"] = """🔴 Maximum attempts reached (3)

Suggestions:
1. Simplify your question
2. Be more specific
3. Ask about customers, products, vendors, or sales"""
    return state
