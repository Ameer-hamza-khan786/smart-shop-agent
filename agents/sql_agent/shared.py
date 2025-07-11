# shared.py
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from config import GLOBAL_LLM, DATABASE_URL
from langchain_community.utilities import SQLDatabase


# Shared DB schema
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


# Agent State class
class AgentState(TypedDict):
    question: str
    curr_question: str
    sql_query: str
    query_result: str
    attempts: int
    relevance: bool
    sql_error: list[str]


# Output Models
class CheckRelevance(BaseModel):
    is_relevant: bool = Field(...)


class ConvertToSQL(BaseModel):
    sql_query: str = Field(...)


class HumanAnswer(BaseModel):
    answer: str = Field(...)


class RewrittenQuestion(BaseModel):
    question: str = Field(...)


# Database instance
_db = SQLDatabase.from_uri(DATABASE_URL)
