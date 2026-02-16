from utils import SilentLogger
import os
from yt_dlp import YoutubeDL


def fetch_video_info(video_url):
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "logger": SilentLogger(),
        "ffmpeg_location": os.path.join(os.path.dirname(os.getcwd()), "ffmpeg")
    }

    with YoutubeDL(ydl_opts) as ydl:
        video_info = ydl.extract_info(video_url, download=False)

    return {
        "url": video_url,
        "title": video_info.get("title"),
        "thumbnail": video_info.get("thumbnail"),
        "duration": video_info.get("duration"),
        "uploader": video_info.get("uploader"),
    }


def download_audio(video_url):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "downloads/%(title)s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "logger": SilentLogger(),
        "ffmpeg_location": os.path.join(os.path.dirname(os.getcwd()), "ffmpeg")
    }

    with YoutubeDL(ydl_opts) as ydl:
        video_info = ydl.extract_info(video_url, download=True)

    return video_info.get("title")



