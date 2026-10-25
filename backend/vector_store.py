import os
import chromadb

class VectorStore:
    def __init__(self):
        db_path = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
        os.makedirs(db_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="tickets_knowledge_base")
        self._cached_count = None

    def query(self, query_text: str, n_results: int = 3):
        try:
            if self._cached_count is None:
                self._cached_count = self.collection.count()

            if self._cached_count == 0:
                return []

            results = self.collection.query(query_texts=[query_text], n_results=n_results)
            if not results or "documents" not in results or not results["documents"]:
                return []
            return results["documents"][0]
        except Exception as e:
            print(f"Vector Store Query Error: {e}")
            return []