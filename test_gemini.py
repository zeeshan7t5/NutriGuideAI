from dotenv import load_dotenv
import os
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

print("KEY FOUND:", bool(api_key))
print("PREFIX:", api_key[:5] if api_key else "NONE")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="Say hello in one short sentence."
)

print("\nGemini response:")
print(response.text)