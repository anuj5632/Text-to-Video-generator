# list_models.py
from dotenv import load_dotenv
import os
import google.generativeai as genai

load_dotenv()                 # loads GEMINI_API_KEY from .env
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("GEMINI_API_KEY not set in .env")

# configure library (the package your repo uses)
genai.configure(api_key=api_key)

print("Listing models and supported generation methods...\n")
for m in genai.list_models():
    # model object has .name and .supported_generation_methods in many SDKs
    try:
        methods = getattr(m, "supported_generation_methods", None)
    except Exception:
        methods = None
    print(m.name, "→ methods:", methods)
