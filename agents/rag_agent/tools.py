from langchain_tavily import TavilySearch
from langchain_core.tools import tool
import psycopg2
from dotenv import load_dotenv
from config import EMBEDDING_MODEL  # Ensure it's initialized correctly
import os

load_dotenv()


# Connect to PostgreSQL
def get_pg_conn():
    try:
        return psycopg2.connect(
            host=os.getenv("PG_HOST"),
            port=os.getenv("PG_PORT"),
            dbname=os.getenv("PG_DATABASE"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
        )
    except Exception as e:
        raise RuntimeError(f"Database connection error: {e}")


@tool
def rag_search_tool(query: str, top_k: int = 3) -> dict:
    """Search from PGVector DB using query embeddings"""
    try:
        embedder = EMBEDDING_MODEL
        query_vector = embedder.embed_query(query)

        sql = """
        SELECT content, source_file, 
               1 - (embedding <=> %s::vector) AS similarity
        FROM documents
        ORDER BY similarity DESC
        LIMIT %s
    """

        with get_pg_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (query_vector, top_k))
            rows = cur.fetchall()

        if not rows:
            return {"content": "No relevant documents found.", "source_file": []}

        Content = "\n\n".join(row[0] for row in rows)
        Source_file = [row[1] for row in rows]

        return {"content": Content, "source_file": Source_file}

    except Exception as e:
        return {"content": f"RAG_ERROR::{e}", "source_file": []}


# Tavily web search tool
tavily = TavilySearch(max_results=3, topic="general")


@tool
def web_search_tool(query: str) -> dict:
    """Get up-to-date web results via Tavily"""
    answer = {"content": "No search results returned from Tavily.", "source_url": []}
    try:
        result = tavily.invoke({"query": query})

        if isinstance(result, dict) and result.get("results"):
            formatted_results = []
            for item in result["results"]:
                title = item.get("title", "No title")
                content = item.get("content", "No content")
                url = item.get("url", "")
                formatted_results.append(
                    f"Title: {title}\nContent: {content}\nURL: {url}"
                )

            answer["content"] = "\n\n".join(formatted_results)
            answer["source_url"] = [item.get("url", "") for item in result["results"]]
            return answer
        else:
            return answer
    except Exception as e:
        answer["content"] = f"WEB_ERROR::{e}"
        answer["source_url"] = []
        return answer
