from yt_dlp import YoutubeDL
from pathlib import Path
import sys

# -----------------------------
# Setup downloads folder
# -----------------------------
DOWNLOADS_DIR = Path(__file__).parent / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

# -----------------------------
# Check for ffmpeg binaries
# -----------------------------
FFMPEG_DIR = Path(__file__).parent / "bin"
ffmpeg_exe = FFMPEG_DIR / "ffmpeg.exe"
ffprobe_exe = FFMPEG_DIR / "ffprobe.exe"

if not ffmpeg_exe.exists() or not ffprobe_exe.exists():
    print("❌ ffmpeg or ffprobe not found in 'bin/' folder!")
    print("Please make sure 'ffmpeg.exe' and 'ffprobe.exe' are in the bin folder at the project root.")
    sys.exit(1)

# -----------------------------
# Ask user for URL
# -----------------------------
url = input("Please enter a YouTube video or playlist URL: ")

# -----------------------------
# Step 1: Extract metadata only
# -----------------------------
ydl_opts_metadata = {
    'quiet': True,
    'no_warnings': True,
    'skip_download': True,
    'extract_flat': True,  # Only metadata
}

try:
    with YoutubeDL(ydl_opts_metadata) as ydl:
        info = ydl.extract_info(url, download=False)

    # Determine if playlist or single video
    if 'entries' in info:
        playlist_entries = []
        valid_videos = 0
        skipped_videos = 0

        print(f"\n✅ This is a playlist with {len(info['entries'])} items.\n")

        for entry in info['entries']:
            title = entry.get('title', 'Untitled')
            if title in ["[Private video]", "[Deleted video]"]:
                skipped_videos += 1
                continue
            playlist_entries.append(entry['url'])
            valid_videos += 1
            print(f"{valid_videos}. 🎵 {title}")

        print(f"\n✅ Found {valid_videos} valid videos.")
        if skipped_videos > 0:
            print(f"⚠️ Skipped {skipped_videos} unavailable/private videos.")

    else:
        # Single video
        print("🎬 This is a single video.")
        title = info.get('title', 'Untitled')
        print(f"Title: {title}")
        playlist_entries = [url]

except Exception as e:
    print("❌ Invalid URL or video not available.")
    print("Error details:", e)
    sys.exit(1)

# -----------------------------
# Step 2: Download Audio
# -----------------------------
ydl_opts_download = {
    'format': 'bestaudio/best',
    'ignoreerrors': True,
    'outtmpl': str(DOWNLOADS_DIR / '%(title)s.%(ext)s'),
    'quiet': True,
    'noprogress': True,
    'no_warnings': True,
    'ffmpeg_location': str(FFMPEG_DIR),
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

# Perform downloads with progress info
with YoutubeDL(ydl_opts_download) as ydl:
    total_videos = len(playlist_entries)
    for idx, video_url in enumerate(playlist_entries, start=1):
        try:
            print(f"\n⬇️ Downloading video {idx} of {total_videos}...")
            ydl.download([video_url])
        except Exception as e:
            print(f"\n❌ Failed to download {video_url}: {e}")

print("\n✅ All downloads finished!")
