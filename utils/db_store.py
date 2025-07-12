import os
import datetime
from typing import List
from config import EMBEDDING_MODEL
from langchain.schema import Document
import psycopg2


embedding_model = EMBEDDING_MODEL


def get_pg_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        dbname=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
    )


def insert_chunks(conn, chunks: List[Document], source_file: str = "Unknown"):
    cursor = conn.cursor()
    inserted = 0
    for chunk in chunks:
        try:
            content = chunk.page_content.strip()
            if not content:
                continue

            embedding = embedding_model.embed_query(content)

            cursor.execute(
                """
                INSERT INTO documents (content, source_file , timestamp , embedding)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    content,
                    source_file,
                    datetime.datetime.now(),
                    embedding,
                ),
            )
            inserted += 1
        except Exception as e:
            print(f"[⚠️] Error inserting chunk: {e}")
            continue
    conn.commit()
    print(f"[✅] Inserted {inserted}/{len(chunks)} chunks from {source_file}")


def delete_temp_file():
    """Delete rows from 'documents' table where source_file contains 'temp_file'"""
    try:
        conn = get_pg_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM documents
            WHERE source_file ILIKE %s
        """,
            ("%temp_file%",),
        )

        deleted = cursor.rowcount
        conn.commit()
        print(f"[🗑️] Deleted {deleted} rows where source_file contains 'temp_file'.")

    except Exception as e:
        print(f"[❌] Error deleting temp files: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("[🔒] Connection closed after deletion.")


def main():
    from utils.chunker import chunk_splitter  # Your earlier file
    from utils.ingestor import RobustIngestor

    FILE_PATH = (
        "/Users/hamza/Developer/Imp_Projects/smart_shop_ai/documents/laptop_bill.pdf"
    )
    # Extract text
    ingestor = RobustIngestor(input_file=FILE_PATH)
    markdown_text = ingestor.run()

    # Chunk it
    tables, texts = chunk_splitter(markdown_text)

    all_chunks = tables + texts  # Still distinguished by metadata

    try:
        conn = get_pg_conn()
        insert_chunks(conn, all_chunks, FILE_PATH)
    except Exception as e:
        print(f"[❌] DB Error: {e}")
    finally:
        if conn:
            conn.close()
            print("[🔒] Connection closed.")


if __name__ == "__main__":
    main()


# CREATE TABLE IF NOT EXISTS documents (
#     id SERIAL PRIMARY KEY,
#     content TEXT,
#     source_file TEXT,
#     timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#     embedding VECTOR(768)
# );


# psql -h localhost -U hamza -d vector_db -> Connect to the vector_db database
# DELETE FROM documents;
