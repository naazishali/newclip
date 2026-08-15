"""
Clip Reel Pro - Privacy Edition v3.0
=====================================
Ye version aise design kiya gaya hai ke:
- User ka video server pe SAVE nahi hota
- Clips temporarily generate hote hain
- User download kar le, phir auto-delete
- Koi bhi data persist nahi hota
- Perfect for shared hosting!
"""

import os
import sys
import uuid
import threading
import traceback
import re
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

# Get the directory where this file is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Add base dir to path for imports
sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, Request, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator

import clipper_v2 as clipper

# Setup directories (all temp - auto cleanup!)
TEMP_DIR = os.path.join(BASE_DIR, "temp")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(title="Clip Reel Pro", version="3.0")

# CORS for any domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Setup templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# In-memory job store (RAM only - no disk!)
JOBS = {}
JOBS_LOCK = threading.Lock()

# Auto cleanup timer
def cleanup_old_files():
    """Delete files older than 10 minutes."""
    while True:
        time.sleep(300)  # Every 5 minutes
        try:
            now = time.time()
            for folder in [TEMP_DIR]:
                if not os.path.exists(folder):
                    continue
                for item in os.listdir(folder):
                    item_path = os.path.join(folder, item)
                    try:
                        if os.path.isfile(item_path):
                            if now - os.path.getmtime(item_path) > 600:  # 10 min
                                os.remove(item_path)
                        elif os.path.isdir(item_path):
                            if now - os.path.getmtime(item_path) > 600:
                                shutil.rmtree(item_path, ignore_errors=True)
                    except:
                        pass
        except:
            pass

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()


class ProcessRequest(BaseModel):
    url: str
    clips: int = 5
    duration: int = 30
    formats: list[str] = ["vertical"]
    quality: str = "720p"


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    try:
        return templates.TemplateResponse(request, "index.html")
    except:
        try:
            return templates.TemplateResponse("index.html", {"request": request})
        except Exception as e:
            return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html><head><title>Clip Reel Pro</title></head>
            <body style="background:#101211;color:#e9ece8;padding:40px;font-family:Arial;text-align:center;">
                <h1 style="color:#c8ff4d;">Clip Reel Pro</h1>
                <p>Loading...</p>
                <p style="color:#ff6b6b;">{str(e)}</p>
            </body></html>
            """)


@app.post("/api/process")
def start_process(req: ProcessRequest, background_tasks: BackgroundTasks):
    """
    Process video and return clips.
    Files auto-delete after 10 minutes!
    """
    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(TEMP_DIR, job_id)
    clips_dir = os.path.join(job_dir, "clips")

    os.makedirs(job_dir, exist_ok=True)
    os.makedirs(clips_dir, exist_ok=True)

    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "running",
            "message": "Starting...",
            "progress": 0,
            "results": [],
            "error": None,
            "clips_dir": clips_dir,
            "created_at": time.time(),
        }

    def run():
        try:
            def progress_cb(msg, step=None, progress=None):
                with JOBS_LOCK:
                    if job_id in JOBS:
                        JOBS[job_id]["message"] = msg
                        if step: JOBS[job_id]["step"] = step
                        if progress is not None: JOBS[job_id]["progress"] = progress

            results = clipper.process_job(
                url=req.url,
                num_clips=req.clips,
                duration=req.duration,
                formats=req.formats,
                quality=req.quality,
                job_dir=job_dir,
                clips_output_dir=clips_dir,
                progress_cb=progress_cb,
            )

            with JOBS_LOCK:
                JOBS[job_id]["status"] = "done"
                JOBS[job_id]["results"] = results
                JOBS[job_id]["progress"] = 100

        except Exception as e:
            traceback.print_exc()
            with JOBS_LOCK:
                JOBS[job_id]["status"] = "error"
                JOBS[job_id]["error"] = str(e)

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def get_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return job


@app.get("/api/download/{job_id}/{filename}")
def download(job_id: str, filename: str):
    """
    Serve clip file. File auto-deletes after download or timeout!
    """
    with JOBS_LOCK:
        job = JOBS.get(job_id)

    if not job:
        return JSONResponse({"error": "Job expired"}, status_code=404)

    clips_dir = job.get("clips_dir", "")
    path = os.path.join(clips_dir, filename)

    if not os.path.isfile(path):
        return JSONResponse({"error": "File not found"}, status_code=404)

    return FileResponse(
        path, 
        filename=filename, 
        media_type="video/mp4",
        background=None
    )


@app.delete("/api/cleanup/{job_id}")
def cleanup_job(job_id: str):
    """Manually cleanup a job's files."""
    with JOBS_LOCK:
        job = JOBS.pop(job_id, None)

    if job and "clips_dir" in job:
        job_dir = os.path.dirname(job["clips_dir"])
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir, ignore_errors=True)

    return {"message": "Cleaned up"}


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "3.0",
        "privacy": "No data stored",
        "auto_cleanup": "10 minutes",
    }


print(f"✅ Clip Reel Pro Privacy Edition started!")
print(f"📁 Temp directory: {TEMP_DIR}")
print(f"🔒 Privacy: No persistent storage")
print(f"🧹 Auto-cleanup: Every 5 minutes")
