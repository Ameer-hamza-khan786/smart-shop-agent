from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from langchain_community.utilities import SQLDatabase
from sqlalchemy.exc import SQLAlchemyError
from langchain_core.runnables import Runnable

from backend.config import (
    GLOBAL_LLM,
    DATABASE_URL,
)  # Import the global LLM from config

db = SQLDatabase.from_uri(DATABASE_URL)


def get_schema():
    return """
customers: stores customer information.
  - cust_id (Primary Key)
  - customer_name
  - phone_no

products: details about available products.
  - product_id (Primary Key)
  - product_name (Unique)
  - price_purchase
  - price_sale
  - quantity

vendors: stores vendor details.
  - vend_id (Primary Key)
  - vendor_name
  - phone_no

sales_data: records of customer purchases.
  - sales_id (Primary Key)
  - customer_id (Foreign Key → customers)
  - transaction_date
  - total_amount
  - total_quantity

purchase_data: records of purchases from vendors.
  - purch_id (Primary Key)
  - vendor_id (Foreign Key → vendors)
  - transaction_date
  - total_amount
  - total_quantity

sale_product: links sales to products (many-to-many).
  - sales_id (Foreign Key → sales_data)
  - prod_id (Foreign Key → products)

purchase_product: links purchases to products (many-to-many).
  - purch_id (Foreign Key → purchase_data)
  - prod_id (Foreign Key → products)

profit_loss: result of a sale, whether profit or loss.
  - sales_id (Primary Key, Foreign Key → sales_data)
  - is_profit (boolean)
  - amount

udhar_sales: sales done on credit.
  - udhar_id (Primary Key)
  - sales_id (Foreign Key → sales_data)
  - date_of_entry
  - date_of_payment

udhar_purchase: purchases done on credit.
  - udhar_id (Primary Key)
  - purch_id (Foreign Key → purchase_data)
  - date_of_entry
  - date_of_payment
"""


class AgentState(TypedDict):
    question: str
    curr_question: str
    sql_query: str
    query_result: str
    attempts: int
    relevance: bool
    sql_error: list[str]


class CheckRelevance(BaseModel):
    is_relevant: bool = Field(
        description="True if the question is related to the database schema, False otherwise"
    )


def check_relevance(state: AgentState):
    question = state["question"]
    schema = get_schema()
    print(f"Checking relevance of the question: {question}")
    system = """You are an assistant that determines whether a given question is related to the following database schema.

Schema:
{schema}

Respond with only True or False.
""".format(schema=schema)
    human = f"Question: {question}"
    check_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", human),
        ]
    )
    llm = GLOBAL_LLM
    structured_llm = llm.with_structured_output(CheckRelevance)
    relevance_checker = check_prompt | structured_llm
    relevance = relevance_checker.invoke({"schema": schema})
    state["relevance"] = relevance.is_relevant
    print(f"Relevance determined: {state['relevance']}")
    state["curr_question"] = question
    state["sql_error"] = []
    return state


class ConvertToSQL(BaseModel):
    sql_query: str = Field(
        description="The PostgreSQL query corresponding to the user's natural language question."
    )


def convert_nl_to_sql(state: AgentState) -> AgentState:
    question = state["curr_question"]
    schema = get_schema()
    sql_errors = state.get("sql_error", [])

    print(f"Converting question to SQL: {question}")

    # Add error context if there were previous attempts
    error_context = ""
    if sql_errors:
        error_context = f"""
Previous SQL errors to avoid:
{sql_errors[-1] if sql_errors else "None"}

Make sure to use the correct column names from the schema above."""

    system_prompt = f"""You are an expert SQL assistant. Convert the user's natural language question into a valid and correct **PostgreSQL SELECT query** using the schema provided below.

Schema:
{schema}

{error_context}

Instructions:
- ✅ Only generate read-only SELECT queries.
- ❌ Do NOT use INSERT, UPDATE, DELETE, DROP, ALTER, or CREATE — ever.
- Use proper PostgreSQL syntax.
- Use table aliases where helpful.
- NEVER use SELECT * — explicitly name columns and alias them meaningfully.
- If multiple tables are needed, join them correctly.
- Ensure all referenced tables and columns exist exactly as shown in the schema.
- Do not generate explanations — return only the SQL query string inside the `sql_query` field.

You must return a valid SQL SELECT statement wrapped inside the `sql_query` field.
"""

    convert_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "Question: {question}"),
        ]
    )

    structured_llm = GLOBAL_LLM.with_structured_output(ConvertToSQL)
    sql_generator: Runnable = convert_prompt | structured_llm

    result: ConvertToSQL = sql_generator.invoke({"question": question})
    state["sql_query"] = result.sql_query.strip()
    print(f"✅ Generated SQL query:\n{state['sql_query']}")

    return state


def execute_sql(state: AgentState) -> AgentState:
    sql_query = state["sql_query"]
    print(f"🔍 Executing SQL query:\n{sql_query}")

    # Enforce read-only SELECT-only policy
    if not sql_query.strip().lower().startswith("select"):
        state["query_result"] = "❌ Only SELECT queries are allowed."
        state["sql_error"] = ["Write operations are not permitted."]
        return state

    try:
        # Execute using LangChain's SQLDatabase.run() method
        result = db.run(sql_query)

        state["query_result"] = result if result else "No results found."
        state["sql_error"] = []
        print("✅ SQL SELECT executed successfully.")

    except SQLAlchemyError as e:
        state["query_result"] = f"❌ Error executing SQL query: {str(e)}"
        state["sql_error"].append(str(e))
        print(f"❌ SQL execution failed: {e}")

    return state


class HumanAnswer(BaseModel):
    answer: str = Field(description="A natural language explanation of the SQL result")


def generate_human_readable_answer(state: AgentState) -> AgentState:
    sql_query = state.get("sql_query", "")
    result = state.get("query_result", "")

    if not sql_query or not result:
        state["query_result"] += (
            "\n⚠️ Cannot generate explanation: SQL or result missing."
        )
        return state

    print("📄 Generating human-readable summary...")

    system_prompt = """You are a helpful assistant that explains SQL results in simple, clear language.
Turn the output of a SQL SELECT query into a user-friendly answer that can be understood by non-technical users.

- Use plain English.
- Summarize the key takeaways.
- Avoid repeating column headers literally unless needed.
- Don't include raw SQL or table names.
"""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            (
                "human",
                f"""Here is the SQL query:
{sql_query}

Here is the result of the query:
{result}

Explain this result to a non-technical user:
""",
            ),
        ]
    )

    structured_llm = GLOBAL_LLM.with_structured_output(HumanAnswer)

    try:
        explainer = prompt | structured_llm
        response = explainer.invoke({})
        state["query_result"] += f"\n\n🗣️ {response.answer}"
        print("✅ Human-readable summary added.")
    except Exception as e:
        print(f"❌ Failed to generate human explanation: {e}")
        state["query_result"] += f"\n⚠️ Failed to summarize: {str(e)}"

    return state


class RewrittenQuestion(BaseModel):
    question: str = Field(
        description="The rewritten natural language question for SQL query generation."
    )


def regenerate_query(state: AgentState) -> AgentState:
    original_question = state["question"]
    failed_question = state["curr_question"]
    sql_error = state.get("sql_error", "")
    last_query = state.get("sql_query", "")
    schema = get_schema()  # Add schema context

    print(
        "🔄 Regenerating the SQL query by reformulating the question based on error feedback..."
    )

    system = f"""You are an assistant that improves natural language questions based on SQL error feedback.
Your goal is to rewrite a user's original question in a way that:
- Avoids the SQL error that previously occurred
- Uses the correct column names from the schema below
- Includes all necessary information for a correct SQL query
- Keeps the user's original intent intact

Database Schema:
{schema}

Pay special attention to the actual column names in each table."""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            (
                "human",
                f"""Original Question:
{original_question}

Attempted Reformulation:
{failed_question}

Previous SQL Query Attempt:
{last_query}

SQL Error list (last one is latest error):
{sql_error}

Please rewrite the original question to improve SQL generation and avoid the above error. Only return the improved question.
""",
            ),
        ]
    )

    structured_llm = GLOBAL_LLM.with_structured_output(RewrittenQuestion)
    rewriter = prompt | structured_llm

    try:
        rewritten = rewriter.invoke({})
        state["curr_question"] = rewritten.question  # also re-set current question
        state["attempts"] += 1
        print(f"✅ Rewritten question: {rewritten.question}")
    except Exception as e:
        print(f"❌ Failed to rewrite question: {e}")
        # Optional: fallback to original question or mark a retry
        state["question"] = original_question
        state["curr_question"] = original_question

    return state


def generate_funny_response(state: AgentState) -> AgentState:
    print(
        "🎭 Generating a funny but helpful response for an unrelated or irrelevant question..."
    )

    schema_summary = """
Available tables and key columns:
- customers (cust_id, customer_name, phone_no)
- products (product_id, product_name, price_purchase, price_sale, quantity)
- vendors (vend_id, vendor_name, phone_no)
- sales_data (sales_id, customer_id, transaction_date, total_amount, total_quantity)
- purchase_data (purch_id, vendor_id, transaction_date, total_amount, total_quantity)
- sale_product (sales_id, prod_id)
- purchase_product (purch_id, prod_id)
- profit_loss (sales_id, is_profit, amount)
- udhar_sales (udhar_id, sales_id, date_of_entry, date_of_payment)
- udhar_purchase (udhar_id, purch_id, date_of_entry, date_of_payment)
"""

    original_question = state.get("question", "")

    system_prompt = f"""
You are a helpful assistant with a charming and funny personality.

The user asked a question that could not be answered meaningfully using the SQL database schema.

Your job is to:
1. Playfully explain that the question is unrelated or unclear.
2. Briefly say **why** it doesn't match the available database schema.
3. Suggest how the user could rephrase their question to make it answerable.
4. Use humor — but be genuinely helpful.

Here is the database schema you can refer to:
{schema_summary}
"""

    human_prompt = f"""
The user asked this question:
"{original_question}"

But it wasn't relevant to the database, and state['relevance'] = False.


Please explain playfully what went wrong and suggest a better way to ask.
"""

    funny_prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt.strip()), ("human", human_prompt.strip())]
    )

    llm = GLOBAL_LLM
    funny_response = funny_prompt | llm | StrOutputParser()

    try:
        message = funny_response.invoke({})
        state["query_result"] = message
        print("✅ Funny helper response generated.")
    except Exception as e:
        print(f"❌ Failed to generate funny response: {e}")
        state["query_result"] = (
            "Sorry, I got confused trying to be funny about your question. Try rephrasing it!"
        )

    return state


def end_max_iterations(state: AgentState):
    state["query_result"] = "Please try again."
    print("Maximum attempts reached. Ending the workflow.")
    return state


def relevance_router(state: AgentState):
    if state["relevance"]:
        return "convert_to_sql"
    else:
        return "generate_funny_response"


def check_attempts_router(state: AgentState):
    if state["attempts"] < 5:
        return "convert_to_sql"
    else:
        return "end_max_iterations"


def execute_sql_router(state: AgentState):
    if state["sql_error"]:
        return "regenerate_query"
    else:
        return "generate_human_readable_answer"


workflow = StateGraph(AgentState)

workflow.add_node("check_relevance", check_relevance)
workflow.add_node("convert_to_sql", convert_nl_to_sql)
workflow.add_node("execute_sql", execute_sql)
workflow.add_node("generate_human_readable_answer", generate_human_readable_answer)
workflow.add_node("regenerate_query", regenerate_query)
workflow.add_node("generate_funny_response", generate_funny_response)
workflow.add_node("end_max_iterations", end_max_iterations)


workflow.add_conditional_edges(
    "check_relevance",
    relevance_router,
    {
        "convert_to_sql": "convert_to_sql",
        "generate_funny_response": "generate_funny_response",
    },
)

workflow.add_edge("convert_to_sql", "execute_sql")

workflow.add_conditional_edges(
    "execute_sql",
    execute_sql_router,
    {
        "generate_human_readable_answer": "generate_human_readable_answer",
        "regenerate_query": "regenerate_query",
    },
)

workflow.add_conditional_edges(
    "regenerate_query",
    check_attempts_router,
    {
        "convert_to_sql": "convert_to_sql",
        "end_max_iterations": "end_max_iterations",
    },
)

workflow.add_edge("generate_human_readable_answer", END)
workflow.add_edge("generate_funny_response", END)
workflow.add_edge("end_max_iterations", END)

workflow.set_entry_point("check_relevance")

app = workflow.compile()


if __name__ == "__main__":
    query = None
    a = 5
    while a > 0:
        query = input("Enter the query: ")
        result_1 = app.invoke(
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
        print("Result:", result_1["query_result"])
        a -= 1
