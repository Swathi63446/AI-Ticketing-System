import os
from pathlib import Path
from config import KNOWLEDGE_BASE_DIR
from vector_store import VectorStore

def chunk_markdown(content: str, source_name: str, chunk_size: int = 400):
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = []
    current_len = 0

    for para in paragraphs:
        current_chunk.append(para)
        current_len += len(para) + 2 # +2 accounts for the double newline characters

        if current_len >= chunk_size:
            # 1. Save the completed chunk
            chunks.append("\n\n".join(current_chunk))
            
            # 2. OVERLAP LOGIC: Keep the last paragraph as the start of the next chunk
            current_chunk = [para]
            current_len = len(para) + 2

    # Append any remaining text at the very end
    if current_chunk and (len(current_chunk) > 1 or not chunks):
        chunks.append("\n\n".join(current_chunk))

    return chunks

def ingest_knowledge_base():
    store = VectorStore()
    if not KNOWLEDGE_BASE_DIR.exists():
        print(f"Knowledge base folder not found at: {KNOWLEDGE_BASE_DIR}")
        return

    documents = []
    metadatas = []
    ids = []

    for file_path in KNOWLEDGE_BASE_DIR.glob("*.md"):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = chunk_markdown(content, file_path.name)
        for idx, chunk in enumerate(chunks):
            doc_id = f"{file_path.stem}_chunk_{idx}"
            documents.append(chunk)
            metadatas.append({"source": file_path.name, "chunk_id": idx})
            ids.append(doc_id)

    if documents:
        store.add_documents(documents=documents, metadatas=metadatas, ids=ids)
        print(f"Successfully ingested {len(documents)} chunks into ChromaDB from {KNOWLEDGE_BASE_DIR}")
    else:
        print("No markdown files found to ingest.")

if __name__ == "__main__":
    ingest_knowledge_base()