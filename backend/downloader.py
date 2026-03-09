from yt_dlp import YoutubeDL
from utils import SilentLogger, format_duration
import os
import shutil
import uuid
from pathlib import Path

# ---------------- System Downloads Folder ---------------- #

DEVICE_DOWNLOADS = Path.home() / "Downloads"

# ---------------- Project FFmpeg path ---------------- #

PROJECT_ROOT = Path(__file__).parent.parent  # adjust if your project structure is different
FFMPEG_PATH = PROJECT_ROOT / "ffmpeg" / "ffmpeg.exe"  # Windows

# ---------------- Fetch Video / Playlist Info ---------------- #

def fetch_video_info(video_url):
    
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
        "noplaylist": False,
        "extract_flat": False,
        "no_warnings": True,
        "skip_unavailable_fragments": True,
        "logger": SilentLogger()
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
    except Exception:
        return {"error": "Failed to extract video information"}

    if not info:
        return {"error": "No video information found"}

    entries = info.get("entries")

    # ---------------- Playlist ---------------- #

    if entries:
        videos = []
        for entry in entries:
            if not entry:
                continue
            if entry.get("availability") != "public":
                continue
            entry_url = entry.get("webpage_url")
            if not entry_url:
                continue

            video_data = {
                "url": entry_url,
                "title": entry.get("title"),
                "thumbnail": entry.get("thumbnail"),
                "duration": format_duration(entry.get("duration")),
                "uploader": entry.get("uploader")
            }
            videos.append(video_data)

        return {
            "type": "playlist",
            "title": info.get("title"),
            "url": info.get("webpage_url"),
            "videos": videos,
            "count": len(videos)
        }

    # ---------------- Single Video ---------------- #

    if info.get("availability") != "public":
        return {"error": "Video is private, unlisted, or unavailable"}

    return {
        "type": "video",
        "url": info.get("webpage_url"),
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": format_duration(info.get("duration")),
        "uploader": info.get("uploader")
    }

# ---------------- Download Audio ---------------- #

def download_audio(video_url):

    # Unique folder per download
    job_id = str(uuid.uuid4())
    download_path = DEVICE_DOWNLOADS / job_id
    os.makedirs(download_path, exist_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(download_path / "%(title)s-%(id)s.%(ext)s"),
        "ffmpeg_location": str(FFMPEG_PATH),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }],
        "concurrent_fragment_downloads": 4,
        "skip_unavailable_fragments": True,
        "ignoreerrors": True,
        "restrictfilenames": True,
        "logger": SilentLogger(),
        "no_warnings": True, 
        "noplaylist": False,
        "quiet": True
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)

    return download_path, info

# ---------------- Cleanup Old Downloads ---------------- #

def cleanup_downloads(max_age_seconds=3600):
    # Delete old folders in the device Downloads folder
    
    now = os.path.getmtime(str(DEVICE_DOWNLOADS))
    for item in DEVICE_DOWNLOADS.iterdir():
        if item.is_dir():
            folder_age = now - item.stat().st_mtime
            if folder_age > max_age_seconds:
                shutil.rmtree(item, ignore_errors=True)