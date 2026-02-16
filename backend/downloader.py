from yt_dlp import YoutubeDL
from utils import SilentLogger
import os


def fetch_video_info(video_url):
    ydl_opts = {
    "quiet": True,
    "skip_download": True,
    "ignoreerrors": True,
    "logger": SilentLogger(),
    "noplaylist": False,
    "js_runtimes": { "deno": {} },
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
    else:
        return {
                "type": "video",
                "url": video_info.get("webpage_url"),
                "title": video_info.get("title"),
                "thumbnail": video_info.get("thumbnail"),
                "duration": video_info.get("duration"),
                "uploader": video_info.get("uploader"),
            }


def download_audio(video_url, video_type):
    if video_type == "video":
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": "downloads/%(title)s.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "ignoreerrors": True, 
            "logger": SilentLogger(),
            "ffmpeg_location": os.path.join(os.path.dirname(__file__), "ffmpeg", "ffmpeg.exe"),
            "js_runtimes": { "deno": {} },
        }

        with YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(video_url, download=True)

        return f"{video_info.get('title')}.mp3"
    
    elif video_type == "playlist":
        with YoutubeDL({"quiet": True, "ignoreerrors": True}) as ydl:
            video_info = ydl.extract_info(video_url, download=False)

        playlist_title = video_info.get("title", "playlist")
        playlist_folder = os.path.join("downloads", playlist_title)
        os.makedirs(playlist_folder, exist_ok=True)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(playlist_folder, "%(title)s.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "ignoreerrors": True,
            "logger": SilentLogger(),
            "ffmpeg_location": os.path.join(os.path.dirname(os.getcwd()), "ffmpeg", "ffmpeg.exe"),
        }

        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(video_url, download=True)

        return playlist_folder




