import google.generativeai as genai
import os
import dotenv

dotenv.load_dotenv("app.env")

# Set your key
genai.configure(api_key=os.getenv("LLM_API_KEY"))

print("Available Models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f" - {m.name} ({m.display_name})")