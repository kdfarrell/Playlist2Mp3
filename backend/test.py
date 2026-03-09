from yt_dlp import YoutubeDL
import os
from utils import SilentLogger

# Ensures that the "downloads" folder exists
os.makedirs("downloads", exist_ok=True)

url = "https://youtu.be/BBJa32lCaaY?si=LpPc95QmW92QxEY9"

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
    print(f"Successfully Downloaded:\n\n\t{info.get('title') }")







