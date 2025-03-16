import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
AVAILABLE_MODELS = [
    "llama-3.3-70b-versatile",  # Default versatile model
    "gemma2-9b-it",            # Lightweight, fast
    "qwen-qwq-32b"            # Powerful, newer model
]
DEFAULT_MODEL = "llama-3.3-70b-versatile"