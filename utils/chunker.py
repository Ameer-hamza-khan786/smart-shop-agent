import re
from typing import List, Tuple
from langchain.schema import Document
from langchain.text_splitter import MarkdownTextSplitter
from .ingestor import RobustIngestor
from config import CHUNK_OVERLAP, CHUNK_SIZE


def clean_markdown_table(table: str) -> str:
    """
    Optimized cleanup of markdown tables for LLM processing:
    1. Removes empty columns and rows
    2. Normalizes formatting
    3. Strips currency symbols
    4. Minimizes string operations
    """
    # Precompile regex for better performance with repeated use
    CURRENCY_PATTERN = re.compile(r"[₹$,]")
    PIPE_PATTERN = re.compile(r"\s*\|\s*")

    # Fast initial processing
    lines: List[str] = []
    for line in table.splitlines():
        if stripped := line.strip():
            lines.append(stripped)

    # Early exit for invalid tables
    if len(lines) < 2:
        return table

    # Process header and separator more efficiently
    header_parts = [
        part.strip() for part in PIPE_PATTERN.split(lines[0]) if part.strip()
    ]
    if len(header_parts) < 2:
        return table

    num_columns = len(header_parts)
    cleaned_lines = [
        f"| {' | '.join(header_parts)} |",
        f"|{'|'.join(['---'] * num_columns)}|",
    ]

    # Process rows with minimal allocations
    for row in lines[2:]:
        cells = []
        for cell in PIPE_PATTERN.split(row):
            if cleaned := CURRENCY_PATTERN.sub("", cell.strip()):
                cells.append(cleaned)

        # Only keep rows with substantial content
        if len(cells) >= num_columns // 2:
            # Ensure we don't exceed original column count
            row_content = cells[:num_columns]
            cleaned_lines.append(f"| {' | '.join(row_content)} |")

    return "\n".join(cleaned_lines)


def chunk_splitter(text: str) -> Tuple[List[Document], List[Document]]:
    """
    Splits markdown into two types of Documents: tables and normal text.
    Returns: (table_docs, text_docs)
    """

    text_splitter = MarkdownTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    # 1. Extract markdown tables using regex
    table_pattern = re.compile(r"((?:\|.+\|\n)+)", re.MULTILINE)
    tables = table_pattern.findall(text)
    non_table_text = table_pattern.sub("", text)

    table_docs = []
    for table in tables:
        cleaned = clean_markdown_table(table)
        if cleaned:
            table_docs.append(Document(page_content=cleaned))

    # 2. Chunk non-table markdown text
    text_chunks = text_splitter.split_text(non_table_text)
    text_docs = [Document(page_content=chunk) for chunk in text_chunks]

    return table_docs, text_docs


if __name__ == "__main__":
    file_path = (
        "/Users/hamza/Developer/Imp_Projects/smart_shop_ai/documents/laptop_bill.pdf"
    )

    ingestor = RobustIngestor(input_file=file_path)
    text = ingestor.run()

    table_docs, text_docs = chunk_splitter(text)

    print(f"\n✅ {len(table_docs)} tables extracted:")
    for i, doc in enumerate(table_docs, 1):
        print(f"\n--- Table {i} ---\n{doc.page_content}\n{'=' * 40}")

    print(f"\n✅ {len(text_docs)} non-table chunks:")
    for i, doc in enumerate(text_docs, 1):
        print(f"\n--- Text Chunk {i} ---\n{doc.page_content}\n{'-' * 40}")
