import os
import datetime
import hashlib
import psycopg2
from dotenv import load_dotenv
from typing import List
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Load environment variables
load_dotenv()

# Embedding model
embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")


def get_pg_connection():
    return psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        dbname=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
    )


def compute_file_hash(file_path: str) -> str:
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    return hashlib.sha256(file_bytes).hexdigest()


def document_exists(cur, doc_hash: str) -> bool:
    cur.execute("SELECT 1 FROM documents WHERE doc_hash = %s LIMIT 1", (doc_hash,))
    return cur.fetchone() is not None


def insert_chunks_manually(
    conn, cur, chunks: List[str], source_file: str, doc_type: str, doc_hash: str
):
    try:
        timestamp = datetime.datetime.now(datetime.UTC)
        total_chunks = len(chunks)

        for idx, chunk in enumerate(chunks):
            try:
                embedding = embedding_model.embed_query(chunk)
                cur.execute(
                    """
                    INSERT INTO documents (
                        embedding, content, source_file, doc_type,
                        timestamp, chunk_index, total_chunks, doc_hash
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        embedding,
                        chunk,
                        os.path.basename(source_file),
                        doc_type,
                        timestamp,
                        idx,
                        total_chunks,
                        doc_hash,
                    ),
                )
            except Exception as e:
                print(f"[⚠️] Failed to insert chunk {idx} from {source_file}: {e}")

        conn.commit()
        print(f"[✅] Inserted {total_chunks} chunks from {source_file}")

    except Exception as e:
        print(f"[❌] Insert failed for {source_file}: {e}")
        conn.rollback()


def process_document(file_path: str, conn, cur):
    print(f"[📄] Processing: {file_path}")

    doc_hash = compute_file_hash(file_path)

    if document_exists(cur, doc_hash):
        print(f"[⚠️] Skipped (duplicate detected): {file_path}")
        return

    from backend.utils.ingestor import RobustIngestor

    ingestor = RobustIngestor(input_file=file_path)

    try:
        chunks = ingestor.run()
    except Exception as e:
        print(f"[❌] Ingestor failed for {file_path}: {e}")
        return

    if not chunks:
        print(f"[⚠️] No chunks extracted from {file_path}")
        return

    doc_type = (
        "image" if file_path.lower().endswith((".jpg", ".jpeg", ".png")) else "document"
    )
    insert_chunks_manually(conn, cur, chunks, file_path, doc_type, doc_hash)


if __name__ == "__main__":
    DOCUMENTS_DIR = "./documents"
    conn = None
    cur = None

    try:
        conn = get_pg_connection()
        cur = conn.cursor()

        for filename in os.listdir(DOCUMENTS_DIR):
            file_path = os.path.join(DOCUMENTS_DIR, filename)

            if not os.path.isfile(file_path):
                continue

            if not filename.lower().endswith(
                (".pdf", ".docx", ".pptx", ".jpg", ".jpeg", ".png")
            ):
                print(f"[⚠️] Unsupported file type: {file_path}")
                continue

            process_document(file_path, conn, cur)

    except Exception as e:
        print(f"[❌] Fatal DB error: {e}")

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("[🔒] Database connection closed.")
