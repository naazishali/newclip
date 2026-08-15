# CLIP REEL PRO - COMPLETE DEPLOYMENT GUIDE
# ===========================================
# Is guide mein 3 tareeqe hain app ko live karne ke:
# 1. Shared Hosting (cPanel) - Domain + Hosting
# 2. GitHub + Free Cloud (Railway/Render/Heroku)
# 3. VPS (DigitalOcean/Linode/AWS)
#

# ============================================================
# OPTION 1: SHARED HOSTING (cPanel) - RECOMMENDED FOR BEGINNERS
# ============================================================

## Requirements:
# - Python 3.8+ support (check with hosting provider)
# - SSH access (optional but recommended)
# - Domain name

## Steps:

### 1. Files Upload karein (File Manager ya FTP)
```
public_html/
├── app_privacy.py          <- Main backend
├── clipper_v2.py           <- Video processing
├── requirements.txt        <- Dependencies
├── index.html              <- Frontend (static)
├── static/
│   ├── app_v2.js
│   └── style_v2.css
├── .htaccess               <- Apache config
└── passenger_wsgi.py       <- WSGI entry point
```

### 2. .htaccess file banayein:
```apache
RewriteEngine On
RewriteCond %{HTTP_HOST} ^www\.(.*)$ [NC]
RewriteRule ^(.*)$ https://%1/$1 [R=301,L]

# For Python apps (if supported)
RewriteRule ^$ app_privacy.py [L]
```

### 3. cPanel mein Python App setup karein:
# - cPanel login karein
# - "Setup Python App" search karein
# - Python 3.8+ select karein
# - App folder select karein (public_html)
# - WSGI file: app_privacy:app

### 4. Dependencies install karein (SSH se):
```bash
ssh username@yourdomain.com
cd public_html
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Domain point karein:
# - Domain registrar pe jayein
# - Nameservers ya A record update karein
# - Hosting provider ke nameservers use karein

## IMPORTANT - Shared Hosting Limitations:
# - ffmpeg install nahi ho sakta (shared server pe)
# - Isliye video processing limited hogi
# - Solution: VPS use karein ya cloud hosting

# ============================================================
# OPTION 2: GITHUB + FREE CLOUD HOSTING (BEST FREE OPTION)
# ============================================================

## A) GitHub Repository Setup

### 1. GitHub pe new repo banayein:
# - https://github.com/new
# - Name: clipreel-pro
# - Public select karein

### 2. Local files push karein:
```bash
# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit"

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/clipreel-pro.git

# Push
git push -u origin main
```

### 3. .gitignore IMPORTANT:
```
temp/
clips/
jobs/
uploads/
*.mp4
*.wav
.env
```
# Ye files commit mat karein - user data hai!

## B) Railway.app (Free Tier - RECOMMENDED)

### 1. Railway pe signup karein:
# - https://railway.app/
# - GitHub se login karein

### 2. New Project:
# - "New Project" -> "Deploy from GitHub repo"
# - Apni repo select karein

### 3. Environment Variables set karein:
# - Project Settings -> Variables
# - Add: PORT = 8000

### 4. Auto Deploy:
# - Har push pe auto deploy hoga!
# - URL milegi: https://your-app.up.railway.app

### 5. Custom Domain:
# - Settings -> Domains
# - Apna domain add karein
# - DNS records update karein

## C) Render.com (Free Tier)

### 1. Render pe signup:
# - https://render.com/
# - GitHub se connect karein

### 2. New Web Service:
# - "New +" -> "Web Service"
# - GitHub repo select karein

### 3. Settings:
```
Name: clipreel-pro
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn app_privacy:app --host 0.0.0.0 --port $PORT
```

### 4. Deploy:
# - "Create Web Service"
# - Free tier mein 15 min sleep hota hai
# - Custom domain add kar sakte hain

## D) Heroku (Free tier discontinued, paid only)

### 1. Heroku CLI install karein
### 2. Login:
```bash
heroku login
```

### 3. Create app:
```bash
heroku create clipreel-pro
```

### 4. Deploy:
```bash
git push heroku main
```

### 5. Add buildpacks:
# - heroku/python
# - heroku-buildpack-apt (for ffmpeg)

# ============================================================
# OPTION 3: VPS (DigitalOcean/Linode/AWS) - MOST POWERFUL
# ============================================================

## Best for: Video processing (ffmpeg chahiye!)

### 1. VPS Create karein (DigitalOcean example):
# - https://cloud.digitalocean.com/
# - Droplet create karein
# - Ubuntu 22.04 select karein
# - $6/month plan (sufficient)

### 2. SSH se connect karein:
```bash
ssh root@YOUR_SERVER_IP
```

### 3. Setup karein:
```bash
# Update
apt update && apt upgrade -y

# Install Python & ffmpeg
apt install -y python3-pip python3-venv ffmpeg git

# Create app directory
mkdir -p /var/www/clipreel
cd /var/www/clipreel

# Clone repo
git clone https://github.com/YOUR_USERNAME/clipreel-pro.git .

# Virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create temp directory
mkdir -p temp
chmod 777 temp
```

### 4. Systemd service create karein:
```bash
# File: /etc/systemd/system/clipreel.service
```

```ini
[Unit]
Description=Clip Reel Pro
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/clipreel
Environment="PATH=/var/www/clipreel/venv/bin"
ExecStart=/var/www/clipreel/venv/bin/uvicorn app_privacy:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
systemctl enable clipreel
systemctl start clipreel
systemctl status clipreel
```

### 5. Nginx reverse proxy:
```bash
apt install -y nginx
```

```nginx
# /etc/nginx/sites-available/clipreel
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /var/www/clipreel/static;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/clipreel /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 6. SSL (Let's Encrypt):
```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 7. Domain point karein:
# - A record: @ -> YOUR_SERVER_IP
# - A record: www -> YOUR_SERVER_IP

# ============================================================
# PRIVACY SETTINGS (Koi data save na ho!)
# ============================================================

## app_privacy.py mein ye settings hain:

```python
# Temp files only - no persistent storage
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# Auto cleanup every 5 minutes
def cleanup_old_files():
    # Delete files older than 10 minutes

# No database
# No user accounts
# No analytics
# No cookies (except functional)
```

## User ke liye kya dikhta hai:
```
1. User URL dale
2. Video process hui (temp folder mein)
3. Clips generate hue (temp folder mein)
4. User download kare
5. 10 min baad sab delete!
```

# ============================================================
# MOBILE ACCESS (Kisi bhi phone se!)
# ============================================================

## After deployment, URL kuch bhi ho sakti hai:
# - https://clipreel.yourdomain.com
# - https://clipreel-pro.up.railway.app
# - https://clipreel-pro.onrender.com

## Mobile pe access:
# 1. Chrome/Safari kholen
# 2. URL type karein
# 3. Use karein!

## Progressive Web App (PWA) bana sakte hain:
# - "Add to Home Screen" option
# - Full-screen app experience
# - Offline support (limited)

# ============================================================
# IMPORTANT NOTES
# ============================================================

1. **ffmpeg REQUIRED**: 
   - Shared hosting pe nahi milega
   - VPS/Cloud pe install karein: `apt install ffmpeg`

2. **Memory**:
   - Video processing RAM use karti hai
   - Minimum 1GB RAM recommended
   - 2GB+ for 1080p processing

3. **Storage**:
   - Temp files auto-delete hoti hain
   - Server pe kuch save nahi hota
   - User responsible for downloads

4. **Rate Limits**:
   - Free tiers pe limits hain
   - Multiple users ke liye VPS best hai

5. **Security**:
   - HTTPS use karein (Let's Encrypt free)
   - CORS enabled for any domain
   - No authentication needed
