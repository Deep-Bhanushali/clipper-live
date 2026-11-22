"""AI metadata generation for ClipViral using Google Gemini API.

Generates viral titles, hooks, descriptions, and hashtags from Whisper transcripts.
Keeps your API key local in .env or environment variable (GEMINI_API_KEY).
"""

import json
import os
import re
import requests

HERE = os.path.dirname(os.path.abspath(__file__))


def load_api_key():
    """Retrieve Gemini API key from environment or local .env file."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if key:
        return key.strip()

    env_path = os.path.join(HERE, ".env")
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and v:
                            return v
        except Exception:
            pass
    return None


def generate_metadata_with_gemini(transcript, streamer=None, stream_title=None, default_hook=None):
    """Use Gemini 2.5 Flash to generate high-CTR title, hook banner, description, and hashtags.

    Returns dict with keys: 'title', 'hook', 'description', 'hashtags'
    """
    api_key = load_api_key()
    if not api_key:
        return None

    prompt = f"""You are an elite YouTube Shorts editor for the viral GTA gaming channel "ClipViral".
Analyze this 30-second GTA video clip and create viral, high-CTR metadata:

Source Title: {stream_title or 'GTA Gameplay'}
Streamer / Player: {streamer or 'Creator'}
Spoken Dialogue / Transcript: "{transcript or 'Intense gameplay action'}"

Generate:
1. "title": A viral, curiosity-inducing YouTube Shorts title under 75 characters with 1-2 emojis and ending with #Shorts. It should relate directly to the dialogue or funny moment.
2. "hook": 3 to 6 words in ALL CAPS with 1 emoji for the top video banner (e.g. "BRO THOUGHT HE WAS SAFE 💀", "NO WAY HE SAID THAT 😭", "INSTANT KARMA 💀").
3. "description": An engaging 2-3 sentence description summarizing the crazy moment, crediting the creator ({streamer or 'Original Creator'}), with viral tags at the end.
4. "hashtags": A list of 6-8 viral gaming and shorts hashtags (strings starting with #, like "#GTA6", "#Shorts", "#Gaming").

Respond ONLY with valid JSON in this exact structure:
{{
  "title": "string",
  "hook": "string",
  "description": "string",
  "hashtags": ["#tag1", "#tag2", ...]
}}"""

    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.7,
        },
    }

    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                meta = json.loads(raw_text)
                if meta.get("title") and meta.get("hook"):
                    meta["title"] = meta["title"].strip()
                    meta["hook"] = meta["hook"].strip().upper()
                    return meta
            elif resp.status_code in (503, 429):
                print(f"[Gemini AI] {model_name} busy ({resp.status_code}), switching to backup model...")
                continue
            else:
                print(f"[Gemini AI] {model_name} API error ({resp.status_code}): {resp.text[:200]}")
        except Exception as e:
            print(f"[Gemini AI] Failed on {model_name}: {e}")

    return None
