import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
# openai/gpt-oss-20b is small, fast, and comfortably fits Groq's free-tier
# rate limits for the short extraction/description calls this app makes.
# Swap to openai/gpt-oss-120b in .env for higher-quality output if your
# free-tier quota allows it. Groq's model lineup changes fairly often, so
# this is deliberately overridable via .env rather than hardcoded deeper
# in the pipeline.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))

DATA_DIR = BASE_DIR / "data"
TAXONOMY_PATH = DATA_DIR / "taxonomy.json"
STORE_PATH = DATA_DIR / "store.json"
SEED_DIR = DATA_DIR / "seed_products"

LLM_ENABLED = bool(GROQ_API_KEY)
