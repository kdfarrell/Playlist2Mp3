from yt_dlp import YoutubeDL
from utils import SilentLogger, safe_filename
import os


# ---------------------------
# Paths / Constants
# ---------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOWNLOADS_PATH = os.path.join(PROJECT_ROOT, "downloads")
FFMPEG_PATH = os.path.join(PROJECT_ROOT, "ffmpeg", "ffmpeg.exe")


# ---------------------------
# Fetch Video / Playlist Info
# ---------------------------

def fetch_video_info(video_url):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "ignoreerrors": True,
        "logger": SilentLogger(),
        "noplaylist": False,
    }

    with YoutubeDL(ydl_opts) as ydl:
        video_info = ydl.extract_info(video_url, download=False)

    if "entries" in video_info:
        entries = video_info.get("entries")

        return {
            "type": "playlist",
            "title": video_info.get("title"),
            "url": video_info.get("webpage_url"),
            "videos": [
                {
                    "url": entry.get("webpage_url"),
                    "title": entry.get("title"),
                    "thumbnail": entry.get("thumbnail"),
                    "duration": entry.get("duration"),
                    "uploader": entry.get("uploader"),
                }
                for entry in entries if entry
            ],
        }

    return {
        "type": "video",
        "url": video_info.get("webpage_url"),
        "title": video_info.get("title"),
        "thumbnail": video_info.get("thumbnail"),
        "duration": video_info.get("duration"),
        "uploader": video_info.get("uploader"),
    }


# ---------------------------
# Download Audio
# ---------------------------

def download_audio(video_url, video_type):

    if video_type == "video":

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(DOWNLOADS_PATH, "%(title)s.%(ext)s"),
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
            video_info = ydl.extract_info(video_url, download=True)

        filename = safe_filename(video_info.get("title"))
        return os.path.join(DOWNLOADS_PATH, f"{filename}.mp3")


    elif video_type == "playlist":

        with YoutubeDL({
            "quiet": True,
            "ignoreerrors": True,
            "logger": SilentLogger()
        }) as ydl:
            video_info = ydl.extract_info(video_url, download=False)

        playlist_title = safe_filename(video_info.get("title", "playlist"))
        playlist_folder = os.path.join(DOWNLOADS_PATH, playlist_title)

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