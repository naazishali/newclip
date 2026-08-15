# Clip Reel Pro - Standalone Windows App

## Kya Hai Ye?

Ye **Clip Reel Pro** ka standalone version hai jo aapke **Windows computer pe** chalta hai — **bina kisi VPS ke**, **bina command line ke**! 

Sirf **double-click** karo, browser open hoga, app chal padega! 🚀

---

## 3 Tareeqe Se Chala Sakte Hain

### Option 1: Sabse Aasaan - START_APP.bat (Recommended)

```
1. Sab files ek folder mein rakhein
2. START_APP.bat pe DOUBLE-CLICK karein
3. Browser automatically open hoga
4. App ready!
```

**Kya hota hai:**
- Dependencies check honge (auto-install)
- Server start hoga
- Browser open hoga (http://127.0.0.1:8765)
- App chalne lagega

---

### Option 2: Python Se Direct

```bash
# 1. Dependencies install karein (pehli baar)
pip install fastapi uvicorn jinja2 python-multipart yt-dlp librosa numpy scipy soundfile

# 2. ffmpeg install karein (https://ffmpeg.org/download.html)
#    aur PATH mein add karein

# 3. Server chalayein
python -m uvicorn standalone_server:app --host 127.0.0.1 --port 8765

# 4. Browser mein kholein
http://127.0.0.1:8765
```

---

### Option 3: .EXE Banake (Professional)

```bash
# 1. PyInstaller install karein
pip install pyinstaller

# 2. Build script chalayein
python build_standalone.py

# 3. Output milega:
#    installer/ClipReelPro.exe

# 4. Double-click karo, app chal padega!
```

---

## File Structure

```
clipreel_pro/
├── START_APP.bat          <-- DOUBLE-CLICK KARO!
├── standalone_server.py   <-- FastAPI backend
├── clipper_v2.py          <-- Video processing
├── index_v2.html          <-- Web UI
├── app_v2.js              <-- Frontend logic
├── style_v2.css           <-- Styling
├── build_standalone.py    <-- .EXE builder
├── templates/             <-- (auto-created)
│   └── index.html
├── static/                <-- (auto-created)
│   ├── app_v2.js
│   └── style_v2.css
├── clips/                 <-- Generated clips yahan
└── jobs/                  <-- Temporary files
```

---

## Requirements

| Cheez | Kya Hai | Kahan Se |
|-------|---------|----------|
| Python 3.8+ | Programming language | https://python.org |
| ffmpeg | Video processing | https://ffmpeg.org |
| Internet | YouTube download | Aapka connection |
| 4GB RAM | Smooth processing | Computer mein honi chahiye |

---

## Use Karna

### Step 1: App Open Karein
- Browser mein `http://127.0.0.1:8765` kholein
- Ya START_APP.bat se auto-open hoga

### Step 2: Video URL Dalein
- YouTube link paste karein
- Example: `https://youtube.com/watch?v=abcd1234`

### Step 3: Settings Select Karein
- **Clip Count**: Kitne clips chahiye (1-15)
- **Duration**: Har clip kitni lambi (5-120 sec)
- **Quality**: 720p ya 1080p
- **Format**: 9:16 (TikTok), 1:1 (Instagram), 16:9 (YouTube)

### Step 4: Process Karein
- "Find the Clips" button dabayein
- Progress dekhein (5 steps)
- Wait karein (2-5 minutes)

### Step 5: Download Karein
- Clips ready hone pe download karein
- `clips/` folder mein bhi save honge

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Python not found" | Python 3.8+ install karein, PATH mein add karein |
| "ffmpeg not found" | ffmpeg download karein, PATH mein add karein |
| "Module not found" | `pip install -r requirements_v2.txt` chalayein |
| Browser nahi khulta | Manually `http://127.0.0.1:8765` open karein |
| Processing slow | 720p select karein, kam clips banayein |
| "Port already in use" | `netstat -ano` se port 8765 check karein |

---

## Advanced: .EXE Kaise Banayein

```bash
# 1. PyInstaller install
pip install pyinstaller

# 2. Icon create karein (optional)
python create_icon.py

# 3. Build karein
python build_standalone.py

# Output:
# installer/
#   └── ClipReelPro.exe    <-- Ye file distribute karein!
```

Ye .exe file kisi bhi Windows computer pe chalegi — bina Python ke!

---

## Support

Koi problem ho to:
1. README check karein
2. Requirements verify karein
3. Logs check karein (command prompt mein errors dekhein)

---

**Enjoy! 🎬**
