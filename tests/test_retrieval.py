import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from vector_store import VectorStore


def test_vector_store_empty_query(mocker):
    """Verifies vector store handles blank or whitespace queries cleanly."""
    mock_chroma = mocker.patch("vector_store.chromadb.Client")
    mock_collection = MagicMock()
    mock_collection.query.return_value = {"documents": [[]]}
    
    vs = VectorStore()
    vs.collection = mock_collection

    results = vs.query("   ", 3)
    assert isinstance(results, list)


def test_vector_store_retrieval_exception_handling(mocker):
    """Ensures vector database connection failures return an empty list rather than raising uncaught errors."""
    mock_chroma = mocker.patch("vector_store.chromadb.Client")
    vs = VectorStore()
    
    mock_collection = MagicMock()
    mock_collection.query.side_effect = Exception("ChromaDB Index Corrupted or Unavailable")
    vs.collection = mock_collection

    try:
        results = vs.query("app performance issue", 3)
        assert results == []
    except Exception as e:
        pytest.fail(f"VectorStore.query raised an uncaught exception during retrieval failure: {e}")


def test_vector_store_malformed_chroma_response(mocker):
    """Tests handling when ChromaDB returns missing or None structure keys."""
    mock_chroma = mocker.patch("vector_store.chromadb.Client")
    vs = VectorStore()
    
    mock_collection = MagicMock()
    mock_collection.query.return_value = {}  # Missing 'documents' key
    vs.collection = mock_collection

    results = vs.query("login failure", 3)
    assert results == []