import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))

def ask_gemini(prompt, retries=3):
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt
            )
            return response.text
        except errors.ServerError as e:
            print(f"Attempt {attempt + 1} failed ({e}), retrying...")
            time.sleep(2 * (attempt + 1))
    return None

result = ask_gemini('In one sentence, explain why supply chain management matters for a small business.')
print(result or "Failed after all retries.")
