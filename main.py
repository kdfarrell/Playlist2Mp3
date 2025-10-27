from yt_dlp import YoutubeDL

# playlist_url = "https://youtube.com/playlist?list=PLDcL5VwwHvEq4MxR9MHNg_Q0HkEHjqFop&si=eBFt522S7B7XAgkd"
# vid_url = "https://www.youtube.com/watch?v=tvpDjUClyGc"


url = input("Please enter a YouTube video or playlist url: ")

ydl_opts = {
    'quiet': True,               
    'no_warnings': True,        
    'skip_download': True,       
    'extract_flat': True,
}

with YoutubeDL(ydl_opts) as ydl:
    try:
        info = ydl.extract_info(url, download=False)
        
        # Check if it's a playlist
        if 'entries' in info:
            print(f"This is a playlist with {len(info['entries'])} videos.")
            for i, entry in enumerate(info['entries'], start=1):
                print(f"{i}. Video title: {entry.get('title')}")
        else:
            print("This is a single video.")
            print("Video title:", info.get('title'))
    
    except Exception as e:
        print("Invalid URL or video not available.")