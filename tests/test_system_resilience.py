import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import db
from app import background_sync_worker


def test_background_worker_handles_empty_queue(mocker):
    """Ensures worker exits cleanly when no pending tickets exist in database."""
    mocker.patch("db.get_and_lock_unprocessed_tickets", return_value=[])
    mock_llm = mocker.patch("app.analyze_ticket_with_gemini")

    background_sync_worker()

    mock_llm.assert_not_called()


def test_background_worker_resilience_on_llm_crash(mocker):
    """Verifies that if LLM service returns empty results on error, db records ticket as invalid without thread crash."""
    mocker.patch("db.get_and_lock_unprocessed_tickets", return_value=[
        {"id": 999, "subject": "Crash Test", "description": "Causes Error", "file_url": None}
    ])
    mocker.patch("vector_store.VectorStore.query", return_value=[])
    mocker.patch("app.analyze_ticket_with_gemini", return_value=[])
    mock_save = mocker.patch("db.save_batch_tickets")

    try:
        background_sync_worker()
        mock_save.assert_called_once_with(999, [], None)
    except Exception as e:
        pytest.fail(f"background_sync_worker crashed on LLM invocation failure: {e}")


def test_save_batch_tickets_db_transaction_rollback(mocker):
    """Verifies database marks ticket status as 'failed_sync' if primary Supabase update fails."""
    mock_supabase = mocker.patch("db.supabase")

    def mock_update_side_effect(payload):
        mock_query = MagicMock()
        # Primary update fails, but fallback status update succeeds
        if payload.get("status") == "failed_sync":
            mock_query.eq.return_value.execute.return_value = None
            return mock_query
        else:
            mock_query.eq.return_value.execute.side_effect = Exception("Database Connection Lost")
            return mock_query

    mock_supabase.table.return_value.update.side_effect = mock_update_side_effect

    analyzed_tickets = [{
        "ai_subject": "Issue", "ai_description": "Desc", "category": "Technical",
        "sentiment": "Negative", "priority": "High", "ai_summary": "Summary",
        "requires_human_review": True, "ai_response": "Draft response"
    }]

    db.save_batch_tickets(original_ticket_id=500, analyzed_tickets=analyzed_tickets)

    # Verify fallback update call was executed with failed_sync
    mock_supabase.table.return_value.update.assert_called_with({"status": "failed_sync"})