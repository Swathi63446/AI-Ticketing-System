import os
import json
from supabase import create_client

supabase = create_client(os.getenv("SUPABASE_URL", ""), os.getenv("SUPABASE_KEY", ""))
METRICS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "metrics.json")


def _load_metrics():
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    all_completed = supabase.table("tickets").select("priority").eq("status", "completed").execute().data or []

    metrics = {
        "lifetime": {"Total": len(all_completed), "Critical": 0, "High": 0, "Medium": 0, "Low": 0},
        "just_now": {"Total": 0, "Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    }

    for t in all_completed:
        pri = t.get("priority", "Low")
        if pri in metrics["lifetime"]:
            metrics["lifetime"][pri] += 1

    os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
    _save_metrics(metrics)
    return metrics


def _save_metrics(metrics):
    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f)


def init_db(): pass


def create_raw_ticket(subject, description):
    res = supabase.table("tickets").insert({
        "subject": subject, "description": description, "status": "pending"
    }).execute()
    return res.data[0]['id']


def update_ticket_file(ticket_id, file_url):
    supabase.table("tickets").update({"file_url": file_url}).eq("id", ticket_id).execute()


def get_and_lock_unprocessed_tickets():
    res = supabase.table("tickets").update({"status": "processing"}).eq("status", "pending").execute()

    if res.data:
        metrics = _load_metrics()
        metrics["just_now"] = {"Total": 0, "Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        _save_metrics(metrics)

    return res.data or []


def mark_ticket_invalid(ticket_id, provider):
    supabase.table("tickets").update({"status": "invalid", "provider": provider}).eq("id", ticket_id).execute()


def sanitize_sentiment(raw_val):
    """Enforces strict sentiment categorization: Positive, Negative, or Neutral."""
    val = str(raw_val or "").strip().lower()

    if any(w in val for w in ["pos", "good", "great", "thanks", "happy", "pleased"]):
        return "Positive"
    elif any(w in val for w in ["neg", "concern", "urg", "crit", "frustr", "angr", "bad", "issue", "problem", "error", "fail"]):
        return "Negative"
    elif any(w in val for w in ["neutr", "inquir", "suggest", "info", "question", "req"]):
        return "Neutral"
    
    return "Neutral"


def sanitize_priority(raw_val):
    """Enforces strict priority categorization: Critical, High, Medium, or Low."""
    val = str(raw_val or "").strip().capitalize()
    if val in ["Critical", "High", "Medium", "Low"]:
        return val
    if "Urgent" in val or "Crit" in val:
        return "Critical"
    return "Low"


def normalize_ticket_payload(data):
    """Flexible Key Normalization & Strict Enums Enforcement."""
    if not isinstance(data, dict):
        data = {}
    
    return {
        "status": "completed",
        "subject": data.get("ai_subject") or data.get("subject") or data.get("title") or "Support Issue",
        "description": data.get("ai_description") or data.get("description") or data.get("details") or "Customer ticket description",
        "category": data.get("category") or data.get("type") or "General",
        "sentiment": sanitize_sentiment(data.get("sentiment")),
        "priority": sanitize_priority(data.get("priority")),
        "ai_summary": data.get("ai_summary") or data.get("summary") or "Summary unavailable",
        "requires_human_review": bool(data.get("requires_human_review", False)),
        "ai_response": data.get("ai_response") or data.get("response") or "Standard response"
    }


def save_single_ticket_result(original_ticket_id, analyzed_data, file_url=None, provider="gemini", latency_ms=0, is_first_row=True):
    payload = normalize_ticket_payload(analyzed_data)
    payload["file_url"] = file_url
    payload["provider"] = provider
    payload["latency_ms"] = latency_ms

    priority = payload["priority"]

    try:
        if is_first_row:
            supabase.table("tickets").update(payload).eq("id", original_ticket_id).execute()
        else:
            supabase.table("tickets").insert(payload).execute()

        metrics = _load_metrics()
        metrics["lifetime"]["Total"] += 1
        metrics["just_now"]["Total"] += 1
        if priority in metrics["lifetime"]:
            metrics["lifetime"][priority] += 1
            metrics["just_now"][priority] += 1
        _save_metrics(metrics)

    except Exception as e:
        print(f"Failed to persist ticket into Supabase: {e}")


def get_dashboard_metrics():
    metrics = _load_metrics()

    pending = len(supabase.table("tickets").select("id").eq("status", "pending").execute().data or [])
    processing = len(supabase.table("tickets").select("id").eq("status", "processing").execute().data or [])

    crit = supabase.table("tickets").select(
        "id, priority, category, ai_summary, description, file_url, subject"
    ).in_("priority", ["High", "Critical"]).neq("is_solved", True).execute().data or []

    return {
        "metrics": metrics,
        "pending_count": pending,
        "processing_count": processing,
        "critical_tickets": crit
    }


def mark_ticket_solved(ticket_id):
    supabase.table("tickets").update({"is_solved": True}).eq("id", ticket_id).execute()