import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from llm_service import analyze_ticket_with_gemini


def test_gemini_503_service_unavailable(mocker):
    """Tests system recovery when Gemini API returns 503 Service Unavailable."""
    mock_client = mocker.patch("llm_service.client")
    mock_client.models.generate_content.side_effect = Exception(
        "503 UNAVAILABLE. This model is currently experiencing high demand."
    )

    results = analyze_ticket_with_gemini(
        subject="System Error",
        description="Application timeout",
        context=["No context"]
    )

    assert results == []


def test_gemini_429_rate_limit_exceeded(mocker):
    """Tests system recovery when API quota or rate limit is hit."""
    mock_client = mocker.patch("llm_service.client")
    mock_client.models.generate_content.side_effect = Exception(
        "429 RESOURCE_EXHAUSTED. You exceeded your current quota."
    )

    results = analyze_ticket_with_gemini(
        subject="Quota Test",
        description="Rate limit simulation",
        context=[]
    )

    assert results == []


def test_gemini_malformed_json_response(mocker):
    """Tests system handling when LLM output contains invalid JSON syntax."""
    mock_client = mocker.patch("llm_service.client")
    mock_response = MagicMock()
    mock_response.text = "{'tickets': [malformed json string without closing braces..."
    mock_client.models.generate_content.return_value = mock_response

    results = analyze_ticket_with_gemini(
        subject="JSON Error",
        description="Corrupted JSON payload",
        context=[]
    )

    assert results == []


def test_gemini_file_upload_processing_failed(mocker, tmp_path):
    """Tests failure recovery when Google File API fails during document processing."""
    dummy_file = tmp_path / "test_doc.pdf"
    dummy_file.write_text("Dummy content")

    mock_client = mocker.patch("llm_service.client")
    
    mock_file_obj = MagicMock()
    mock_file_obj.name = "files/test_failed_id"
    mock_file_obj.state.name = "FAILED"
    
    mock_client.files.upload.return_value = mock_file_obj
    mock_client.files.get.return_value = mock_file_obj

    results = analyze_ticket_with_gemini(
        subject="PDF Batch",
        description="Uploaded PDF file",
        context=[],
        file_path=str(dummy_file)
    )

    assert results == []


def test_gemini_file_upload_missing_filepath(mocker):
    """Ensures providing a non-existent file path falls back gracefully without raising FileNotFoundError."""
    mock_client = mocker.patch("llm_service.client")
    mock_response = MagicMock()
    # Corrected dictionary format expected by llm_service parsing logic
    mock_response.text = '{"tickets": [{"ai_subject": "Fallback", "ai_description": "Valid", "category": "Technical", "sentiment": "Negative", "priority": "Low", "ai_summary": "Summary", "requires_human_review": false, "ai_response": "Response"}]}'
    mock_client.models.generate_content.return_value = mock_response

    results = analyze_ticket_with_gemini(
        subject="Missing File",
        description="Path does not exist",
        context=[],
        file_path="/invalid/path/to/nonexistent_file.pdf"
    )

    assert len(results) == 1
    assert results[0]["category"] == "Technical"