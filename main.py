from yt_dlp import YoutubeDL
from pathlib import Path

# -----------------------------
# Setup downloads folder
# -----------------------------
DOWNLOADS_DIR = Path(__file__).parent / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

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
        print(f"\n✅ This is a playlist with {len(info['entries'])} items.\n")
        playlist_entries = []

        valid_videos = 0
        skipped_videos = 0

        for i, entry in enumerate(info['entries'], start=1):
            title = entry.get('title', 'Untitled')
            if title in ["[Private video]", "[Deleted video]"]:
                skipped_videos += 1
                continue
            print(f"{i - skipped_videos}. 🎵 {title}")
            playlist_entries.append(entry['url'])
            valid_videos += 1

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
    exit(1)

# -----------------------------
# Step 2: Download URL
# -----------------------------

ydl_opts_download = {
    'format': 'bestaudio/best',
    'ignoreerrors': True,
    'outtmpl': str(DOWNLOADS_DIR / '%(title)s.%(ext)s'),
    'quiet': True,
    'noprogress': True,
    'no_warnings': True,
}

# Perform downloads
with YoutubeDL(ydl_opts_download) as ydl:
    for video_url in playlist_entries:
        try:
            ydl.download([video_url])
        except Exception as e:
            print(f"\n❌ Failed to download {video_url}: {e}")

print("\n✅ All downloads finished!")
