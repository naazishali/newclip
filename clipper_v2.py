"""
Clip Reel Pro - Multi-Platform Core Logic v2.1

Supports: YouTube, Facebook, TikTok, Instagram, Twitter/X, Reddit,
Vimeo, Dailymotion, Twitch, and 1000+ other platforms via yt-dlp.

Features:
- Multi-platform URL support (not just YouTube)
- Cookies support for bot detection bypass
- Direct file upload fallback
- Better error messages
"""

import os
import subprocess
import shutil
import numpy as np


def download_video(url, out_dir, quality="720p", cookies_file=None):
    """
    Download video from any supported platform.
    yt-dlp supports 1000+ sites including:
    YouTube, Facebook, TikTok, Instagram, Twitter/X, Reddit,
    Vimeo, Dailymotion, Twitch, and many more.
    """
    import yt_dlp

    # Quality-based format selection
    if quality == "1080p":
        format_spec = "bestvideo[height<=1080][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best"
    else:
        format_spec = "bestvideo[height<=720][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best"

    out_template = os.path.join(out_dir, "source.%(ext)s")

    ydl_opts = {
        "format": format_spec,
        "outtmpl": out_template,
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
        "geo_bypass": True,
        "nocheckcertificate": True,
    }

    # Add cookies if provided (for YouTube bot bypass)
    if cookies_file and os.path.exists(cookies_file):
        ydl_opts["cookies"] = cookies_file
        print(f"Using cookies from: {cookies_file}")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video")
            duration = info.get("duration", 0)
            uploader = info.get("uploader", "unknown")
            platform = info.get("extractor", "unknown")
            print(f"Downloaded from {platform}: {title}")
    except Exception as e:
        error_msg = str(e)
        # Check for common errors
        if "Sign in to confirm" in error_msg:
            raise RuntimeError(
                "YouTube bot detection triggered!\n\n"
                "Solutions:\n"
                "1. Use --cookies-from-browser in yt-dlp\n"
                "2. Upload cookies.txt file to app folder\n"
                "3. Try a different video\n"
                "4. Wait a few hours and try again"
            )
        elif "Private video" in error_msg:
            raise RuntimeError("This video is private. Please use a public video URL.")
        elif "Video unavailable" in error_msg:
            raise RuntimeError("This video is unavailable. It may be deleted or region-blocked.")
        else:
            raise RuntimeError(f"Download failed: {error_msg}")

    # Find the downloaded file
    for f in os.listdir(out_dir):
        if f.startswith("source.") and f.endswith(".mp4"):
            return os.path.join(out_dir, f), title, duration

    raise FileNotFoundError("Video download ke baad file nahi mili.")


def extract_audio(video_path, out_dir):
    """Extract audio as WAV for analysis."""
    audio_path = os.path.join(out_dir, "audio.wav")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "22050", "-ac", "1",
        audio_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr}")

    return audio_path


def find_highlights(audio_path, num_clips, clip_duration, total_duration):
    """
    Find highlight moments using RMS energy with diversity scoring.
    """
    import librosa

    try:
        y, sr = librosa.load(audio_path, sr=22050)
    except Exception as e:
        print(f"Audio analysis failed ({e}), using fallback spacing")
        if total_duration <= clip_duration:
            return [0]
        step = (total_duration - clip_duration) / max(1, num_clips - 1)
        return [min(i * step, total_duration - clip_duration) for i in range(num_clips)]

    hop_length = 512
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    # Smooth the RMS curve
    window = max(1, int(sr / hop_length))
    smoothed = np.convolve(rms, np.ones(window) / window, mode="same")

    # Find local maxima (peaks)
    from scipy.signal import find_peaks
    peaks, properties = find_peaks(smoothed, distance=int(clip_duration * sr / hop_length / 2), 
                                    prominence=np.std(smoothed) * 0.3)

    if len(peaks) == 0:
        if total_duration <= clip_duration:
            return [0]
        step = (total_duration - clip_duration) / max(1, num_clips - 1)
        return [min(i * step, total_duration - clip_duration) for i in range(num_clips)]

    # Score peaks by prominence and apply diversity
    peak_times = times[peaks]
    peak_scores = properties["prominences"]

    half = clip_duration / 2
    min_gap = clip_duration * 1.5
    chosen = []

    sorted_indices = np.argsort(peak_scores)[::-1]

    for idx in sorted_indices:
        t = peak_times[idx]
        start = max(0, t - half)
        end = min(total_duration, start + clip_duration)
        start = max(0, end - clip_duration)

        if any(abs(start - c) < min_gap for c in chosen):
            continue

        if end > total_duration:
            start = max(0, total_duration - clip_duration)
            end = total_duration

        if end - start < clip_duration * 0.5:
            continue

        chosen.append(start)
        if len(chosen) >= num_clips:
            break

    # If we didn't find enough clips, add evenly spaced ones
    if len(chosen) < num_clips and total_duration > clip_duration * num_clips:
        remaining = num_clips - len(chosen)
        step = total_duration / (remaining + 1)
        for i in range(1, remaining + 1):
            candidate = i * step - clip_duration / 2
            candidate = max(0, min(candidate, total_duration - clip_duration))
            if all(abs(candidate - c) >= min_gap / 2 for c in chosen):
                chosen.append(candidate)
            if len(chosen) >= num_clips:
                break

    chosen.sort()
    return chosen[:num_clips]


def build_filter(fmt, quality="720p"):
    """Build ffmpeg video filter for format and quality."""
    scale = "1080:1920" if quality == "1080p" else "720:1280"
    scale_sq = "1080:1080" if quality == "1080p" else "720:720"
    scale_hz = "1920:1080" if quality == "1080p" else "1280:720"

    if fmt == "vertical":
        return f"crop=ih*9/16:ih,scale={scale}"
    elif fmt == "square":
        return f"crop=ih:ih,scale={scale_sq}"
    elif fmt == "horizontal":
        return f"crop=iw:iw*9/16,scale={scale_hz}"
    else:
        raise ValueError(f"Unknown format: {fmt}")


def cut_clip(video_path, start, duration, out_path, fmt, quality="720p"):
    """Cut and format a clip using ffmpeg."""
    vf = build_filter(fmt, quality)

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", video_path,
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        out_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Clip rendering failed: {result.stderr}")


def get_duration(video_path):
    """Get video duration using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Duration check failed: {result.stderr}")

    return float(result.stdout.strip())


def process_job(url, num_clips, duration, formats, quality, job_dir, clips_output_dir, 
                progress_cb=None, cookies_file=None):
    """
    Complete processing pipeline with multi-platform support.
    """
    def report(msg, step=None, progress=None):
        if progress_cb:
            progress_cb(msg, step, progress)

    os.makedirs(job_dir, exist_ok=True)
    os.makedirs(clips_output_dir, exist_ok=True)

    # Step 1: Download
    report("Video download ho raha hai...", "download", 10)
    video_path, title, yt_duration = download_video(url, job_dir, quality, cookies_file)
    safe_title = "".join(c for c in title if c.isalnum() or c in " -_")[:40].strip() or "video"

    # Step 2: Extract Audio
    report("Audio nikala ja raha hai...", "audio", 25)
    audio_path = extract_audio(video_path, job_dir)

    # Get actual duration
    total_duration = get_duration(video_path)

    # Step 3: Find Highlights
    report("Highlight moments dhoonde ja rahe hain...", "analyze", 40)
    starts = find_highlights(audio_path, num_clips, duration, total_duration)

    if not starts:
        raise ValueError("Koi highlight nahi mila — video shayad bohat chota hai.")

    # Step 4: Render Clips
    report(f"{len(starts)} highlights mile, ab clips ban rahe hain...", "render", 55)

    results = []
    total_steps = len(starts) * len(formats)
    step = 0

    for i, start in enumerate(starts, 1):
        for fmt in formats:
            step += 1
            progress_pct = 55 + int((step / total_steps) * 40)
            report(f"Clip {step}/{total_steps} ban raha hai ({fmt})...", "render", progress_pct)

            out_name = f"{safe_title}_clip{i}_{fmt}_{quality}.mp4"
            out_path = os.path.join(clips_output_dir, out_name)

            try:
                cut_clip(video_path, start, duration, out_path, fmt, quality)
                mm, ss = divmod(int(start), 60)
                results.append({
                    "filename": out_name,
                    "format": fmt,
                    "quality": quality,
                    "timestamp": f"{mm:02d}:{ss:02d}",
                    "duration": duration,
                })
            except Exception as e:
                print(f"Clip {i} ({fmt}) failed: {e}")
                continue

    # Cleanup temp files
    report("Cleanup ho raha hai...", "cleanup", 98)
    shutil.rmtree(job_dir, ignore_errors=True)

    if not results:
        raise ValueError("Koi clip successfully render nahi ho saka.")

    report("Mukammal!", "complete", 100)
    return results


def process_local_video(video_path, num_clips, duration, formats, quality, clips_output_dir, progress_cb=None):
    """
    Process a local video file (fallback when download fails).
    """
    import tempfile

    def report(msg, step=None, progress=None):
        if progress_cb:
            progress_cb(msg, step, progress)

    os.makedirs(clips_output_dir, exist_ok=True)

    # Create temp job dir
    job_dir = tempfile.mkdtemp(prefix="clipreel_job_")

    # Get video info
    report("Local video process ho raha hai...", "download", 10)

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file nahi mili: {video_path}")

    # Copy to job dir for processing
    import shutil as sh
    local_copy = os.path.join(job_dir, "source.mp4")
    sh.copy2(video_path, local_copy)

    title = os.path.splitext(os.path.basename(video_path))[0]

    # Step 2: Extract Audio
    report("Audio nikala ja raha hai...", "audio", 25)
    audio_path = extract_audio(local_copy, job_dir)

    # Get actual duration
    total_duration = get_duration(local_copy)

    # Step 3: Find Highlights
    report("Highlight moments dhoonde ja rahe hain...", "analyze", 40)
    starts = find_highlights(audio_path, num_clips, duration, total_duration)

    if not starts:
        raise ValueError("Koi highlight nahi mila — video shayad bohat chota hai.")

    # Step 4: Render Clips
    report(f"{len(starts)} highlights mile, ab clips ban rahe hain...", "render", 55)

    results = []
    total_steps = len(starts) * len(formats)
    step = 0

    for i, start in enumerate(starts, 1):
        for fmt in formats:
            step += 1
            progress_pct = 55 + int((step / total_steps) * 40)
            report(f"Clip {step}/{total_steps} ban raha hai ({fmt})...", "render", progress_pct)

            out_name = f"{title}_clip{i}_{fmt}_{quality}.mp4"
            out_path = os.path.join(clips_output_dir, out_name)

            try:
                cut_clip(local_copy, start, duration, out_path, fmt, quality)
                mm, ss = divmod(int(start), 60)
                results.append({
                    "filename": out_name,
                    "format": fmt,
                    "quality": quality,
                    "timestamp": f"{mm:02d}:{ss:02d}",
                    "duration": duration,
                })
            except Exception as e:
                print(f"Clip {i} ({fmt}) failed: {e}")
                continue

    # Cleanup
    report("Cleanup ho raha hai...", "cleanup", 98)
    sh.rmtree(job_dir, ignore_errors=True)

    if not results:
        raise ValueError("Koi clip successfully render nahi ho saka.")

    report("Mukammal!", "complete", 100)
    return results
