import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Use official Google Gemini model string
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
BACKEND_URL = os.getenv("BACKEND_URL", f"http://{FLASK_HOST}:{FLASK_PORT}")

# Active Model Registry
MODELS = {
    "gemini": GEMINI_MODEL,
    "groq": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
    "huggingface": "Qwen/Qwen2.5-7B-Instruct",
    "featherless-ai": "Qwen/Qwen2.5-7B-Instruct"
}

DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "tickets.db"
CHROMA_PATH = DATA_DIR / "chroma_store"
KNOWLEDGE_BASE_DIR = ROOT_DIR / "knowledge_base"
METRICS_FILE = DATA_DIR / "metrics.json"