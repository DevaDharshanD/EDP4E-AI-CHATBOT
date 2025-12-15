import os
from dotenv import load_dotenv
load_dotenv("app.env")
print("Gemini key is:", os.getenv("LLM_API_KEY"),type(os.getenv("LLM_API_KEY")))