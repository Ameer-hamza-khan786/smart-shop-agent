from utils.ingestor import RobustIngestor
from utils.chunker import chunk_splitter
from utils.db_store import get_pg_conn, insert_chunks, delete_temp_file
from config import DOCUMENTS_DIR
import os


def Store(file_path: str, temp_store: bool = False) -> None:
    """Extract text preview from uploaded file"""
    # Try to use your ingestor if available
    ingestor = RobustIngestor(input_file=file_path)
    markdown_text = ingestor.run()

    markdown_text = ingestor.run()

    # Chunk it
    tables, texts = chunk_splitter(markdown_text)
    all_chunks = tables + texts  # Still distinguished by metadata
    try:
        conn = get_pg_conn()
        if temp_store:
            insert_chunks(conn, all_chunks, "temp_file")
        else:
            insert_chunks(conn, all_chunks, file_path)
    except Exception as e:
        print(f"[❌] DB Error: {e}")
    finally:
        if conn:
            conn.close()
            print("[🔒] Connection closed.")


def delete_temp_files() -> None:
    delete_temp_file()


def process_all_documents():
    try:
        conn = get_pg_conn()

        for filename in os.listdir(DOCUMENTS_DIR):
            file_path = os.path.join(DOCUMENTS_DIR, filename)

            if not os.path.isfile(file_path):
                continue

            if not filename.lower().endswith(
                (".pdf", ".docx", ".pptx", ".jpg", ".jpeg", ".png")
            ):
                print(f"[⚠️] Skipped unsupported file: {filename}")
                continue

            print(f"[📄] Processing: {filename}")
            try:
                ingestor = RobustIngestor(input_file=file_path)
                markdown_text = ingestor.run()
                tables, texts = chunk_splitter(markdown_text)
                all_chunks = tables + texts
                # with open("chunks_result.txt", "a") as file:
                #     file.write(f"Processing {filename}:\n")
                #     for chunk in all_chunks:
                #         file.write(chunk.page_content + "\n\n")

                insert_chunks(conn, all_chunks, source_file=filename)
            except Exception as e:
                print(f"[❌] Failed to process {filename}: {e}")

        conn.close()
        print("[✅] All files processed. Connection closed.")

    except Exception as e:
        print(f"[❌] Failed to connect to DB: {e}")


if __name__ == "__main__":
    process_all_documents()
