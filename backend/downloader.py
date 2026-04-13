from yt_dlp import YoutubeDL
from utils import SilentLogger, format_duration, safe_filename
import os
import shutil
import uuid
import re
import tempfile
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).parent.parent
FFMPEG_PATH = PROJECT_ROOT / "ffmpeg" / "ffmpeg.exe"
TEMP_DIR = Path(tempfile.gettempdir()) / "playlist2mp3"


# ---------------- Fetch Video / Playlist Info ---------------- #
def fetch_video_info(video_url, progress_callback=None):
    """
    Fetch video or playlist info.
    For playlists, streams per-video progress via progress_callback.
    Returns (info_dict, skipped_list).
    """

    flat_opts = {
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
        "noplaylist": False,
        "extract_flat": True,
        "no_warnings": True,
        "logger": SilentLogger()
    }

    try:
        with YoutubeDL(flat_opts) as ydl:
            flat_info = ydl.extract_info(video_url, download=False)
    except Exception:
        return {"error": "Failed to extract video information"}, []

    if not flat_info:
        return {"error": "No video information found"}, []

    entries = flat_info.get("entries")

    # ---------------- Playlist ---------------- #
    if entries:
        all_entries = [e for e in entries if e]
        total = len(all_entries)
        videos = []
        skipped = []

        full_opts = {
            "quiet": True,
            "skip_download": True,
            "ignoreerrors": True,
            "noplaylist": True,
            "extract_flat": False,
            "no_warnings": True,
            "logger": SilentLogger()
        }

        for i, entry in enumerate(all_entries):
            entry_url = entry.get("url") or entry.get("webpage_url")
            if not entry_url:
                skipped.append(entry.get("title") or f"Video {i+1}")
                if progress_callback:
                    progress_callback({
                        "status": "fetch_progress",
                        "current": i + 1,
                        "total": total,
                        "title": entry.get("title") or f"Video {i+1}",
                        "skipped": True
                    })
                continue

            # Make sure it's a full URL
            if not entry_url.startswith("http"):
                entry_url = "https://www.youtube.com/watch?v=" + entry_url

            if progress_callback:
                progress_callback({
                    "status": "fetch_progress",
                    "current": i + 1,
                    "total": total,
                    "title": entry.get("title") or f"Video {i+1}",
                    "skipped": False
                })

            try:
                with YoutubeDL(full_opts) as ydl:
                    info = ydl.extract_info(entry_url, download=False)
            except Exception:
                info = None

            if not info or info.get("availability") not in (None, "public", ""):
                skipped.append(entry.get("title") or f"Video {i+1}")
                if progress_callback:
                    progress_callback({
                        "status": "fetch_progress",
                        "current": i + 1,
                        "total": total,
                        "title": entry.get("title") or f"Video {i+1}",
                        "skipped": True
                    })
                continue

            videos.append({
                "url": info.get("webpage_url") or entry_url,
                "title": info.get("title") or entry.get("title"),
                "duration": format_duration(info.get("duration")),
                "uploader": info.get("uploader") or info.get("channel")
            })

        if progress_callback:
            progress_callback({"status": "fetch_done"})

        return {
            "type": "playlist",
            "title": flat_info.get("title"),
            "url": flat_info.get("webpage_url") or video_url,
            "videos": videos,
            "count": len(videos)
        }, skipped

    # ---------------- Single Video ---------------- #
    if progress_callback:
        progress_callback({
            "status": "fetch_progress",
            "current": 1,
            "total": 1,
            "title": flat_info.get("title") or "Video",
            "skipped": False
        })

    full_opts = {
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
        "noplaylist": True,
        "extract_flat": False,
        "no_warnings": True,
        "logger": SilentLogger()
    }
    try:
        with YoutubeDL(full_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
    except Exception:
        info = None

    if progress_callback:
        progress_callback({"status": "fetch_done"})

    if not info:
        return {"error": "No video information found"}, []

    if info.get("availability") not in (None, "public", ""):
        return {"error": "Video is private, unlisted, or unavailable"}, []

    return {
        "type": "video",
        "url": info.get("webpage_url") or video_url,
        "title": info.get("title"),
        "duration": format_duration(info.get("duration")),
        "uploader": info.get("uploader") or info.get("channel")
    }, []


# ---------------- Download Audio ---------------- #
def download_audio(video_urls, video_type, total_videos=1, progress_callback=None):
    """
    video_urls: list of URL strings to download.
    Downloads each URL individually so unavailable videos are never encountered.
    """
    job_id = str(uuid.uuid4())
    download_path = TEMP_DIR / job_id
    os.makedirs(download_path, exist_ok=True)

    completed = [0]

    def ydl_progress_hook(d):
        if progress_callback is None:
            return

        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded = d.get("downloaded_bytes", 0)
            pct = int(downloaded / total * 100)
            display_name = Path(d.get("filename", "")).stem
            progress_callback({
                "status": "progress",
                "percent": pct,
                "filename": display_name,
                "current": completed[0] + 1,
                "total": total_videos
            })

        elif d["status"] == "finished":
            completed[0] += 1
            progress_callback({
                "status": "progress",
                "percent": 100,
                "current": completed[0],
                "total": total_videos
            })

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(download_path / "%(title)s.%(ext)s"),
        "ffmpeg_location": str(FFMPEG_PATH),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320"
        }],
        "concurrent_fragment_downloads": 4,
        "skip_unavailable_fragments": True,
        "ignoreerrors": True,
        "logger": SilentLogger(),
        "no_warnings": True,
        "noplaylist": True,   # each URL is a single video now
        "quiet": True,
        "progress_hooks": [ydl_progress_hook],
    }

    last_info = None
    with YoutubeDL(ydl_opts) as ydl:
        for url in video_urls:
            try:
                info = ydl.extract_info(url, download=True)
                if info:
                    last_info = info
            except Exception:
                pass  # ignoreerrors handles it, but belt-and-suspenders

    if progress_callback:
        progress_callback({"status": "done"})

    return download_path, last_info


# ---------------- Cleanup Old Downloads ---------------- #
def cleanup_downloads(max_age_seconds=3600):
    if not TEMP_DIR.exists():
        return
    now = TEMP_DIR.stat().st_mtime
    for item in TEMP_DIR.iterdir():
        if item.is_dir():
            folder_age = now - item.stat().st_mtime
            if folder_age > max_age_seconds:
                shutil.rmtree(item, ignore_errors=True)