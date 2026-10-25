import os
import json
import csv
import time
import pymupdf as fitz
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from config import FLASK_HOST, FLASK_PORT
import db
from vector_store import VectorStore
from llm_service import analyze_ticket_with_provider, analyze_document_tickets_with_provider

app = Flask(__name__)
CORS(app)

vs = VectorStore()
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def extract_pdf_content(pdf_path):
    """Extracts raw text content using PyMuPDF."""
    text_content = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text()
            if text.strip():
                text_content += text + "\n"
        doc.close()
    except Exception as e:
        print(f"PyMuPDF Extraction Error: {e}")
    return text_content.strip()


@app.route("/api/tickets/sync", methods=["POST"])
def sync_tickets():
    payload = request.get_json(silent=True) or {}
    selected_provider = payload.get("provider", "gemini")

    pending_tickets = db.get_and_lock_unprocessed_tickets()
    if not pending_tickets:
        return jsonify({"message": "No pending tickets to process."}), 200

    for raw_ticket in pending_tickets:
        raw_id = raw_ticket["id"]
        file_path = None

        if raw_ticket.get("file_url"):
            filename = raw_ticket["file_url"].split("/")[-1]
            candidate_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(candidate_path):
                file_path = candidate_path

        # Scenario 1: CSV File
        if file_path and file_path.lower().endswith('.csv'):
            rows_to_process = []
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    reader = csv.DictReader(f)
                    rows_to_process = list(reader)
            except Exception as e:
                print(f"CSV Reading Error: {e}")

            if rows_to_process:
                is_first = True
                for row in rows_to_process:
                    msg = row.get("customer_message") or row.get("description") or row.get("text") or str(row)
                    subj = row.get("product") or row.get("subject") or "CSV Ticket Issue"
                    context = vs.query(msg, 2)

                    res = analyze_ticket_with_provider(subj, msg, context=context, provider=selected_provider)
                    if res.get("status") == "success" and res.get("data"):
                        db.save_single_ticket_result(raw_id, res.get("data"), raw_ticket.get("file_url"), selected_provider, res.get("latency_ms", 0), is_first)
                        is_first = False
                    else:
                        print(f"[{selected_provider.upper()} CSV ERROR]: {res.get('error', 'Failed API response')}")
                    
                    time.sleep(1.5)

        # Scenario 2: PDF or Document File
        elif file_path and (file_path.lower().endswith('.pdf') or file_path.lower().endswith(('.txt', '.doc', '.docx'))):
            extracted_text = ""
            if file_path.lower().endswith('.pdf'):
                extracted_text = extract_pdf_content(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    extracted_text = f.read()

            content_payload = extracted_text if extracted_text else "[File Submission]"
            context = vs.query(content_payload[:500], 2)

            res = analyze_document_tickets_with_provider(
                description=content_payload, 
                context=context, 
                provider=selected_provider
            )

            extracted_tickets = res.get("data", [])
            if res.get("status") == "success" and extracted_tickets and len(extracted_tickets) > 0:
                is_first = True
                for ticket_data in extracted_tickets:
                    db.save_single_ticket_result(
                        original_ticket_id=raw_id,
                        analyzed_data=ticket_data,
                        file_url=raw_ticket.get("file_url"),
                        provider=selected_provider,
                        latency_ms=res.get("latency_ms", 0),
                        is_first_row=is_first
                    )
                    is_first = False
                    time.sleep(1.0)
            else:
                print(f"[{selected_provider.upper()} PDF SYNC ERROR]: {res.get('error', 'Rate limit or extraction error')}")
                db.mark_ticket_invalid(raw_id, selected_provider)

        # Scenario 3: Standard Text Input Submission (User-entered Individual Field)
        else:
            subj = raw_ticket.get("subject") or "Support Issue"
            msg = raw_ticket.get("description") or subj
            if msg == "[File Submission]":
                msg = subj

            context = vs.query(msg, 2)

            res = analyze_ticket_with_provider(subj, msg, context=context, provider=selected_provider)
            if res.get("status") == "success" and res.get("data"):
                db.save_single_ticket_result(raw_id, res.get("data"), raw_ticket.get("file_url"), selected_provider, res.get("latency_ms", 0), is_first_row=True)
            else:
                print(f"[{selected_provider.upper()} SINGLE ERROR]: {res.get('error')}")
                db.mark_ticket_invalid(raw_id, selected_provider)

            time.sleep(1.5)  # Rate-limit protection for individual requests

    return jsonify(db.get_dashboard_metrics()), 200


@app.route("/api/tickets/submit", methods=["POST"])
def submit_ticket():
    try:
        subject = ""
        description = ""
        attached_file = request.files.get("file") if request.files else None

        if request.is_json:
            data = request.get_json(silent=True) or {}
            subject = data.get("subject", data.get("title", ""))
            description = data.get("description", data.get("text", data.get("message", "")))
        elif request.form:
            subject = request.form.get("subject", request.form.get("title", ""))
            description = request.form.get("description", request.form.get("text", request.form.get("message", "")))

        # Dynamic fallback if only subject or only description is entered
        if not subject and description:
            subject = description[:40] + "..." if len(description) > 40 else description
        elif subject and not description:
            description = subject
        elif not subject and not description:
            subject = "User Submission"
            description = "[File Submission]" if attached_file else ""

        if not description and not attached_file:
            return jsonify({"error": "Provide text or a file."}), 400

        ticket_id = db.create_raw_ticket(subject, description)

        if attached_file:
            filename = f"ticket_{ticket_id}_doc{os.path.splitext(attached_file.filename)[1]}"
            attached_file.save(os.path.join(UPLOAD_DIR, filename))
            db.update_ticket_file(ticket_id, f"http://{FLASK_HOST}:{FLASK_PORT}/api/uploads/{filename}")

        return jsonify({"message": "Submitted successfully.", "ticket_id": ticket_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/summary", methods=["GET"])
def get_admin_summary():
    return jsonify(db.get_dashboard_metrics()), 200


@app.route("/api/tickets/<int:ticket_id>/solve", methods=["POST"])
def solve_ticket(ticket_id):
    db.mark_ticket_solved(ticket_id)
    return jsonify({"status": "success"}), 200


@app.route('/api/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True, use_reloader=False)