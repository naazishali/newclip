
# CLIP REEL PRO - AGENT 3 DEVELOPMENT PACKAGE
# =============================================
# Ye package Agent 3 ko dein taake wo following features add kar sake:
# 1. TikTok/FB Login Integration
# 2. AI Title Generation
# 3. Auto Posting to Social Media
#

## ARCHITECTURE OVERVIEW
## =====================

Current Stack:
- Backend: FastAPI (Python)
- Frontend: HTML/CSS/JS (vanilla)
- Video Processing: yt-dlp + ffmpeg + librosa
- Storage: Local filesystem

New Features Required:
1. Social Media Auth (TikTok + Facebook)
2. AI Title Generation (OpenAI/Local LLM)
3. Auto Publishing API

## FEATURE 1: TIKTOK LOGIN INTEGRATION
## ===================================

### TikTok API Setup:
- TikTok for Developers: https://developers.tiktok.com/
- Create app, get Client Key and Client Secret
- OAuth 2.0 flow for user authentication
- Scopes needed: video.upload, video.publish, user.info.basic

### Required Python Packages:
tiktok-api-python>=0.2.0
requests-oauthlib>=1.3.0
python-jose>=3.3.0

### Code Structure (tiktok_auth.py):

```python
import os
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import requests

TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = "http://localhost:8765/auth/tiktok/callback"

router = APIRouter(prefix="/auth", tags=["auth"])

# Store tokens (use Redis/DB in production)
TOKENS_FILE = "tokens.json"

def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE) as f:
            return json.load(f)
    return {}

def save_tokens(tokens):
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=2)

@router.get("/tiktok/login")
def tiktok_login():
    """Redirect user to TikTok OAuth."""
    auth_url = (
        "https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={TIKTOK_CLIENT_KEY}"
        f"&redirect_uri={TIKTOK_REDIRECT_URI}"
        "&scope=video.upload,video.publish,user.info.basic"
        "&response_type=code"
        "&state=random_state_string"
    )
    return RedirectResponse(auth_url)

@router.get("/tiktok/callback")
def tiktok_callback(code: str, state: str):
    """Handle TikTok OAuth callback."""
    # Exchange code for access token
    token_url = "https://open.tiktokapis.com/v2/oauth/token/"

    response = requests.post(token_url, data={
        "client_key": TIKTOK_CLIENT_KEY,
        "client_secret": TIKTOK_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": TIKTOK_REDIRECT_URI,
    })

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="TikTok auth failed")

    tokens = response.json()
    tokens["expires_at"] = (datetime.now() + timedelta(seconds=tokens["expires_in"])).isoformat()

    save_tokens({"tiktok": tokens})
    return {"message": "TikTok connected successfully!"}

@router.post("/tiktok/post")
def post_to_tiktok(video_path: str, title: str, description: str = ""):
    """Post video to TikTok."""
    tokens = load_tokens().get("tiktok", {})
    access_token = tokens.get("access_token")

    if not access_token:
        raise HTTPException(status_code=401, detail="Not connected to TikTok")

    # Step 1: Initialize upload
    init_url = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    init_response = requests.post(init_url, headers=headers, json={
        "source_info": {"source": "PULL_FROM_URL", "url": video_path},
        "title": title,
        "description": description,
        "privacy_level": "PUBLIC",  # or "FRIENDS", "PRIVATE"
        "disable_duet": False,
        "disable_comment": False,
        "disable_stitch": False,
    })

    return init_response.json()
```

## FEATURE 2: FACEBOOK LOGIN INTEGRATION
## ======================================

### Facebook API Setup:
- Facebook for Developers: https://developers.facebook.com/
- Create app, get App ID and App Secret
- Graph API v18.0+
- Permissions: pages_manage_posts, pages_read_engagement, publish_video

### Required Packages:
facebook-sdk>=3.1.0
requests-oauthlib>=1.3.0

### Code Structure (facebook_auth.py):

```python
import os
import json
import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
FACEBOOK_REDIRECT_URI = "http://localhost:8765/auth/facebook/callback"

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/facebook/login")
def facebook_login():
    """Redirect to Facebook OAuth."""
    auth_url = (
        "https://www.facebook.com/v18.0/dialog/oauth"
        f"?client_id={FACEBOOK_APP_ID}"
        f"&redirect_uri={FACEBOOK_REDIRECT_URI}"
        "&scope=pages_manage_posts,pages_read_engagement,publish_video"
        "&response_type=code"
    )
    return RedirectResponse(auth_url)

@router.get("/facebook/callback")
def facebook_callback(code: str):
    """Handle Facebook OAuth callback."""
    # Exchange code for token
    token_url = "https://graph.facebook.com/v18.0/oauth/access_token"

    response = requests.get(token_url, params={
        "client_id": FACEBOOK_APP_ID,
        "client_secret": FACEBOOK_APP_SECRET,
        "redirect_uri": FACEBOOK_REDIRECT_URI,
        "code": code,
    })

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Facebook auth failed")

    tokens = response.json()

    # Get page access token (for posting)
    pages_url = f"https://graph.facebook.com/v18.0/me/accounts?access_token={tokens['access_token']}"
    pages_response = requests.get(pages_url)
    pages = pages_response.json()

    save_tokens({"facebook": {"user_token": tokens, "pages": pages}})
    return {"message": "Facebook connected!", "pages": pages.get("data", [])}

@router.post("/facebook/post")
def post_to_facebook(video_path: str, title: str, page_id: str, page_access_token: str):
    """Post video to Facebook page."""

    # Upload video
    upload_url = f"https://graph.facebook.com/v18.0/{page_id}/videos"

    with open(video_path, "rb") as video_file:
        files = {"file": video_file}
        data = {
            "access_token": page_access_token,
            "title": title,
            "description": title,
            "published": "true",
        }

        response = requests.post(upload_url, files=files, data=data)

    return response.json()
```

## FEATURE 3: AI TITLE GENERATION
## ================================

### Option A: OpenAI GPT (Requires API Key)

```python
import os
import openai

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
openai.api_key = OPENAI_API_KEY

def generate_title(video_title: str, platform: str = "tiktok") -> str:
    """Generate catchy title using GPT."""

    prompt = f"""Create a catchy, engaging {platform} title for a video clip.

Original video title: {video_title}
Platform: {platform}

Requirements:
- Maximum 100 characters
- Include relevant hashtags (3-5)
- Use emojis where appropriate
- Make it viral-worthy
- Include call-to-action

Generate 3 options and return the best one."""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a social media expert who creates viral video titles."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.8,
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback: simple title
        return f"🔥 {video_title[:80]} #viral #trending #fyp"
```

### Option B: Local LLM (Ollama/Llama2 - No API Key Needed)

```python
import requests

def generate_title_local(video_title: str, platform: str = "tiktok") -> str:
    """Generate title using local Ollama LLM."""

    prompt = f"Create a catchy {platform} title with hashtags for: {video_title}"

    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama2",
            "prompt": prompt,
            "stream": False,
        })

        result = response.json()
        return result.get("response", f"🔥 {video_title[:80]} #viral")
    except:
        return f"🔥 {video_title[:80]} #viral #trending #fyp"
```

### Option C: Rule-Based (No AI Required)

```python
import random

TEMPLATES = {
    "tiktok": [
        "🔥 {title} #fyp #viral #trending",
        "😱 You won't believe this! {title} #foryou",
        "✨ {title} #tiktok #trending2024",
        "🎯 POV: {title} #pov #fyp",
        "💯 {title} #viral #mustwatch",
    ],
    "facebook": [
        "🎬 {title} - Watch till the end!",
        "😮 {title} | Share if you agree!",
        "🔥 {title} #VideoOfTheDay",
        "✨ Amazing: {title}",
    ],
}

def generate_title_simple(video_title: str, platform: str = "tiktok") -> str:
    """Generate title using templates."""
    templates = TEMPLATES.get(platform, TEMPLATES["tiktok"])
    template = random.choice(templates)

    # Clean title
    clean_title = video_title.replace("#", "").replace("@", "")[:60]

    return template.format(title=clean_title)
```

## FEATURE 4: AUTO POSTING WORKFLOW
## =================================

### Complete Workflow (auto_post.py):

```python
import os
from typing import List
from datetime import datetime

class AutoPoster:
    """Handles automatic posting of clips to social media."""

    def __init__(self):
        self.tiktok_enabled = os.path.exists("tokens.json")
        self.facebook_enabled = os.path.exists("fb_tokens.json")

    def process_and_post(
        self,
        video_path: str,
        original_title: str,
        platforms: List[str] = ["tiktok", "facebook"],
        use_ai_titles: bool = True
    ):
        """
        Complete workflow:
        1. Generate title
        2. Post to each platform
        3. Return post URLs
        """

        results = {}

        # Generate title
        if use_ai_titles:
            title = generate_title(original_title, platforms[0])
        else:
            title = generate_title_simple(original_title, platforms[0])

        # Post to each platform
        for platform in platforms:
            try:
                if platform == "tiktok" and self.tiktok_enabled:
                    result = post_to_tiktok(video_path, title)
                    results["tiktok"] = result

                elif platform == "facebook" and self.facebook_enabled:
                    # Get first page
                    result = post_to_facebook(video_path, title, page_id="", page_access_token="")
                    results["facebook"] = result

            except Exception as e:
                results[platform] = {"error": str(e)}

        return {
            "title": title,
            "platforms": results,
            "posted_at": datetime.now().isoformat(),
        }
```

## FRONTEND CHANGES NEEDED
## ========================

### New UI Elements to Add:

1. **Settings Panel** (settings icon pe click):
```html
<div class="settings-panel">
  <h3>Social Media Accounts</h3>

  <div class="account-row">
    <span>📱 TikTok</span>
    <button onclick="connectTikTok()">Connect</button>
    <span id="tiktok-status">Not connected</span>
  </div>

  <div class="account-row">
    <span>📘 Facebook</span>
    <button onclick="connectFacebook()">Connect</button>
    <span id="fb-status">Not connected</span>
  </div>

  <h3>AI Title Generation</h3>
  <label>
    <input type="checkbox" id="use-ai" checked> Use AI for titles
  </label>
  <select id="ai-provider">
    <option value="openai">OpenAI GPT</option>
    <option value="local">Local LLM (Ollama)</option>
    <option value="template">Template Based</option>
  </select>

  <h3>Auto Post</h3>
  <label>
    <input type="checkbox" id="auto-post-tiktok"> Auto-post to TikTok
  </label>
  <label>
    <input type="checkbox" id="auto-post-fb"> Auto-post to Facebook
  </label>
</div>
```

2. **Post Buttons on Results**:
```html
<!-- Add to each clip card -->
<div class="clip-actions">
  <a class="clip-dl" href="/api/download/...">Download</a>
  <button onclick="postToTikTok('filename.mp4')">📱 Post to TikTok</button>
  <button onclick="postToFacebook('filename.mp4')">📘 Post to FB</button>
</div>
```

## ENVIRONMENT VARIABLES NEEDED
## ==============================

Create `.env` file:
```
# TikTok
TIKTOK_CLIENT_KEY=your_client_key
TIKTOK_CLIENT_SECRET=your_client_secret

# Facebook
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret

# OpenAI (for AI titles)
OPENAI_API_KEY=your_openai_key

# Optional: Local LLM
OLLAMA_HOST=http://localhost:11434
```

## INSTALLATION STEPS FOR AGENT 3
## ===============================

1. Install new packages:
```bash
pip install tiktok-api-python facebook-sdk requests-oauthlib openai python-dotenv
```

2. Create developer accounts:
   - TikTok: https://developers.tiktok.com/
   - Facebook: https://developers.facebook.com/
   - OpenAI: https://platform.openai.com/ (optional)

3. Add auth routes to main app:
```python
from tiktok_auth import router as tiktok_router
from facebook_auth import router as fb_router

app.include_router(tiktok_router)
app.include_router(fb_router)
```

4. Update frontend with new UI elements

5. Test posting workflow

## IMPORTANT NOTES
## ===============

1. **TikTok API Limitations**:
   - Video must be 5 seconds to 10 minutes
   - Max file size: 500MB
   - Requires business/creator account

2. **Facebook API Limitations**:
   - Must have Facebook Page (not personal profile)
   - Page admin role required
   - Video format: MP4/MOV

3. **Rate Limits**:
   - TikTok: 10 posts/day for new apps
   - Facebook: 25 posts/page/day

4. **Security**:
   - Store tokens securely (use encryption)
   - Never commit tokens to git
   - Use HTTPS in production
