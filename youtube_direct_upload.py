r"""Upload a rendered clip directly to your YouTube channel using official Google YouTube Data API v3 (100% Free).

No paid subscriptions or third-party APIs required.
Uses your own free Google Cloud client_secrets.json.

Setup:
1. Go to Google Cloud Console (https://console.cloud.google.com/)
2. Create a project and enable "YouTube Data API v3"
3. Create OAuth 2.0 Client ID (Application type: Desktop App)
4. Download the JSON and save it in this project folder as "client_secrets.json"
5. Install client libraries:
   pip install google-api-python-client google-auth-oauthlib google-auth-httplib2

Usage:
  python youtube_direct_upload.py output\gta-CLIP-ID --privacy public
  python youtube_direct_upload.py output\gta-CLIP-ID --privacy private
  python youtube_direct_upload.py output\gta-CLIP-ID --schedule "2026-11-25T18:00:00Z"
"""

import argparse
import json
import os
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "youtube_token.json"
CLIENT_SECRETS = "client_secrets.json"


def get_authenticated_service():
    """Authenticate via OAuth 2.0 and return YouTube service."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        sys.exit(
            "Missing Google API libraries. Please run:\n"
            "pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
        )

    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS):
                sys.exit(
                    f"'{CLIENT_SECRETS}' not found.\n"
                    "Download your OAuth 2.0 Client Credentials JSON from Google Cloud Console "
                    f"and save it as '{CLIENT_SECRETS}' in this folder."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            print("\n" + "=" * 65)
            print("Action Required: Please complete Google sign-in in your browser.")
            print("If your browser didn't open automatically, copy the URL below:")
            print("=" * 65 + "\n")
            creds = flow.run_local_server(port=0, prompt="consent")
        with open(TOKEN_FILE, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_clip(video_path, metadata_path, privacy_status="public", scheduled_time=None):
    from googleapiclient.http import MediaFileUpload

    with open(metadata_path, encoding="utf-8") as f:
        meta = json.load(f)

    # Build title
    hook = meta.get("hook_title") or "Crazy GTA Moment"
    title = meta.get("title") or f"{hook}! #Shorts #GTA"
    title = title[:100]  # YouTube title limit is 100 characters

    # Build description & hashtags
    desc = meta.get("youtube_description")
    if not desc:
        transcript = meta.get("transcript") or ""
        credit = f"\nCredit / Streamer: {meta['streamer']}" if meta.get("streamer") else ""
        desc = f"{title}\n\n{transcript}{credit}\n\n#GTA6 #GTA #Shorts #Gaming #GTAOnline"

    tags = meta.get("hashtags") or ["GTA 6", "GTA", "Gaming", "Shorts", "Grand Theft Auto"]

    body = {
        "snippet": {
            "title": title,
            "description": desc,
            "tags": tags,
            "categoryId": "20",  # Gaming category
        },
        "status": {
            "privacyStatus": "private" if scheduled_time else privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }

    if scheduled_time:
        body["status"]["publishAt"] = scheduled_time
        body["status"]["privacyStatus"] = "private"

    print(f"Connecting to YouTube API...")
    youtube = get_authenticated_service()

    print(f"Uploading '{video_path.name}' to YouTube Shorts...")
    print(f"Title: {title}")
    print(f"Status: {body['status']['privacyStatus']}")

    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True, chunksize=1024 * 1024 * 5)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    video_url = f"https://youtube.com/shorts/{video_id}"
    print(f"\nUpload complete!")
    print(f"Shorts URL: {video_url}")

    # Set custom thumbnail if generated
    thumb_path = video_path.with_name(video_path.stem + "_thumb.jpg")
    if thumb_path.is_file():
        try:
            print(f"Setting custom thumbnail '{thumb_path.name}'...")
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumb_path), mimetype="image/jpeg")
            ).execute()
            print("Thumbnail set successfully!")
        except Exception as e:
            print(f"Note: Custom thumbnail could not be set ({e}). Channels require phone verification for custom thumbnails.")

    meta["youtube_video_id"] = video_id
    meta["youtube_url"] = video_url
    meta["uploaded_at"] = response.get("snippet", {}).get("publishedAt")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return video_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clip", type=Path, help="Path to .mp4 or .json file")
    parser.add_argument("--privacy", choices=("public", "unlisted", "private"), default="public")
    parser.add_argument("--schedule", help="ISO format future publish time, e.g. '2026-11-25T18:00:00Z'")
    args = parser.parse_args()

    base = args.clip.with_suffix("") if args.clip.suffix.lower() in {".mp4", ".json"} else args.clip
    video_path, metadata_path = base.with_suffix(".mp4"), base.with_suffix(".json")

    if not video_path.is_file() or not metadata_path.is_file():
        sys.exit(f"Clip files not found: {video_path} / {metadata_path}")

    upload_clip(video_path, metadata_path, privacy_status=args.privacy, scheduled_time=args.schedule)


if __name__ == "__main__":
    main()
