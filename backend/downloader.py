from yt_dlp import YoutubeDL
from utils import SilentLogger, safe_filename, format_duration
import os

# FFMPEG path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FFMPEG_PATH = os.path.join(PROJECT_ROOT, "ffmpeg", "ffmpeg.exe")

# ---------------- Fetch Video / Playlist Info ---------------- #
def fetch_video_info(video_url):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
        "logger": SilentLogger(),
        "noplaylist": False,
        "extract_flat": False,
        "no_warnings": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
    except Exception:
        return {"error": "Failed to extract video information"}

    if not info:
        return {"error": "No video information found"}

    entries = info.get("entries")

    # Playlist
    if entries:
        videos = []
        for entry in entries:
            if not entry or entry.get("availability") != "public":
                continue
            entry_url = entry.get("webpage_url")
            if not entry_url:
                continue

            videos.append({
                "url": entry_url,
                "title": entry.get("title"),
                "thumbnail": entry.get("thumbnail"),
                "duration": format_duration(entry.get("duration")),
                "uploader": entry.get("uploader"),
            })

        return {
            "type": "playlist",
            "title": info.get("title"),
            "url": info.get("webpage_url"),
            "videos": videos,
            "count": len(videos),
        }

    # Single video
    if info.get("availability") != "public":
        return {"error": "Video is private, unlisted, or unavailable"}

    return {
        "type": "video",
        "url": info.get("webpage_url"),
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "duration": format_duration(info.get("duration")),
        "uploader": info.get("uploader"),
    }

# ---------------- Download Audio ---------------- #
def download_audio(video_url, video_type, downloads_path):
    os.makedirs(downloads_path, exist_ok=True)

    if video_type == "video":
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(downloads_path, "%(title)s.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "concurrent_fragment_downloads": 4,
            "ignoreerrors": True,
            "logger": SilentLogger(),
            "ffmpeg_location": FFMPEG_PATH,
            "quiet": True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

        filename = safe_filename(info.get("title"))
        return os.path.join(downloads_path, f"{filename}.mp3")

    elif video_type == "playlist":
        with YoutubeDL({"quiet": True, "ignoreerrors": True, "logger": SilentLogger()}) as ydl:
            info = ydl.extract_info(video_url, download=False)

        playlist_title = safe_filename(info.get("title", "playlist"))
        playlist_folder = os.path.join(downloads_path, playlist_title)
        os.makedirs(playlist_folder, exist_ok=True)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(playlist_folder, "%(title)s.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "concurrent_fragment_downloads": 4,
            "ignoreerrors": True,
            "logger": SilentLogger(),
            "ffmpeg_location": FFMPEG_PATH,
            "quiet": True,
            "noplaylist": False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(video_url, download=True)

        return playlist_folder