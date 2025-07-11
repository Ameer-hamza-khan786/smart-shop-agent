from langchain_google_genai import GoogleGenerativeAIEmbeddings
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()


# Connect to DB
def get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        dbname=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
    )


def vector_search(query, top_k=5, filters=None):
    # Embed the query
    embedder = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    query_vector = embedder.embed_query(query)

    # Prepare values
    values = [query_vector, top_k]

    # Corrected SQL: cast embedding input to vector
    sql = """
        SELECT content, source_file, 
               1 - (embedding <=> %s::vector) AS similarity
        FROM documents
        ORDER BY similarity DESC
        LIMIT %s
    """

    # Execute query
    with get_pg_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, tuple(values))
        rows = cur.fetchall()

    # Format results
    results = [
        {
            "content": row[0],
            "source_file": row[1],
            "similarity": row[2],
        }
        for row in rows
    ]
    return results


if __name__ == "__main__":
    results = vector_search("bill of CIFSL ", top_k=3)

    for res in results:
        print(res["content"])
        print(f"\n[Chunk from {res['source_file']}]")
        print(f"(similarity: {res['similarity']:.4f})")
