import os
import sys
import json
import time
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List, Optional

class NarrationItem(BaseModel):
    timestamp_seconds: float
    shot_number: Optional[int] = None
    shot_type: str
    rating: Optional[str] = None
    bat: Optional[str] = None
    narrated_text: str

class NarrationList(BaseModel):
    narrations: List[NarrationItem]

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # try loading from .env
        dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(dotenv_path):
            with open(dotenv_path, "r") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break
    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    
    # Let's test on session-2026-06-26_12-22-13
    audio_path = "/Users/neilkloot/Code/Batting Sensor Stats/live_watch_sessions/session-2026-06-26_12-22-13/narration_20260626_122207.m4a"
    if not os.path.exists(audio_path):
        print(f"Audio file not found at {audio_path}")
        sys.exit(1)
        
    print(f"Uploading {audio_path}...")
    uploaded_file = client.files.upload(file=audio_path)
    print(f"Uploaded: {uploaded_file.name}")
    
    while uploaded_file.state.name == "PROCESSING":
        print("Processing audio...")
        time.sleep(5)
        uploaded_file = client.files.get(name=uploaded_file.name)
        
    if uploaded_file.state.name == "FAILED":
        print("Upload failed.")
        sys.exit(1)
        
    prompt = (
        "You are an audio transcription expert. The attached audio recording contains a cricket batter narrating the shots they are playing. "
        "Transcribe the audio with timestamps.\n\n"
        "In addition to shot type and rating, identify which bat was used for each shot if mentioned or announced in the audio. "
        "The batter uses three bats:\n"
        "- 'Gray Nicolls Giant' (or 'Giant', heavy bat)\n"
        "- 'Eye In' (very thin and light bat)\n"
        "- 'Game bat' (normal bat on the heavy end)\n\n"
        "If the batter mentions a bat (e.g. 'Gray Nicolls Giant' or 'Eye In' or 'Game bat'), map it to the 'bat' field of the narration item. "
        "Assume the batter continues to use the same bat for subsequent shots until they explicitly mention changing to a different bat.\n\n"
        "Output JSON matching the schema."
    )
    
    print("Requesting transcription from gemini-3.5-flash...")
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=NarrationList,
            )
        )
        print("Success! Response text:")
        print(response.text)
        
        # Write results
        out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_bat_extraction_result.json")
        with open(out_path, "w") as f:
            f.write(response.text)
        print(f"Saved response to {out_path}")
    except Exception as e:
        print(f"Error during API call: {e}")
    finally:
        try:
            client.files.delete(name=uploaded_file.name)
            print("Cleaned up cloud file.")
        except Exception as e:
            print(f"Cleanup error: {e}")

if __name__ == "__main__":
    main()
