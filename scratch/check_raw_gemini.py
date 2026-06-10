import os
import sys
from google import genai
from google.genai import types

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        dotenv_path = ".env"
        if os.path.exists(dotenv_path):
            with open(dotenv_path, "r") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
    if not api_key:
        print("GEMINI_API_KEY not found")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    audio_path = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/sessions/session-2026-06-05_12-29-59/narration_20260605_122958.m4a"
    
    print("Uploading file to Gemini...")
    uploaded_file = client.files.upload(file=audio_path)
    print(f"Uploaded: {uploaded_file.name}")
    
    prompt_path = "docs/gemini_narration_prompt.md"
    with open(prompt_path, "r") as f:
        prompt_base = f.read().strip()
        
    prompt = prompt_base + "\n\nOutput the result as a JSON object with a list of narrations. Each narration must contain timestamp_seconds (float), shot_number (int/null), shot_type (str), rating (str/null), and narrated_text (str)."
    
    print("Calling Gemini generate_content...")
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=[uploaded_file, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    
    print("--- RAW GEMINI RESPONSE ---")
    print(response.text)
    print("---------------------------")
    
    # Clean up file
    client.files.delete(name=uploaded_file.name)

if __name__ == "__main__":
    main()
