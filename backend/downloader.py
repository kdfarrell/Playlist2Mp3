from utils import SilentLogger
import os
from yt_dlp import YoutubeDL

def download_url(url):

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
        info = ydl.extract_info(url, download=True)

    return info.get("title")

