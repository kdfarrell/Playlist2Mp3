from yt_dlp import YoutubeDL
from utils import SilentLogger, format_duration
import os
import shutil
import uuid
import tempfile
import time
import base64
import binascii
import logging
from pathlib import Path
from contextlib import contextmanager


PROJECT_ROOT = Path(__file__).parent.parent
FFMPEG_PATH  = PROJECT_ROOT / "ffmpeg" / "ffmpeg.exe"
TEMP_DIR     = Path(tempfile.gettempdir()) / "playlist2mp3"
logger       = logging.getLogger(__name__)


def resolve_ffmpeg_location():
    """Use bundled ffmpeg on Windows, otherwise fallback to env/PATH."""
    env_ffmpeg_path = os.environ.get("FFMPEG_PATH")
    if env_ffmpeg_path:
        return env_ffmpeg_path

    if FFMPEG_PATH.exists():
        return str(FFMPEG_PATH)

    # On Linux hosts (Render), rely on system ffmpeg installed in PATH.
    return "ffmpeg"


def yt_dlp_js_options():
    """Build yt-dlp JS runtime/EJS options from env vars."""
    js_runtimes = os.environ.get("YT_DLP_JS_RUNTIMES", "node")
    remote_components = os.environ.get("YT_DLP_REMOTE_COMPONENTS", "ejs:github")

    opts = {}
    if js_runtimes.strip():
        opts["js_runtimes"] = [s.strip() for s in js_runtimes.split(",") if s.strip()]
    if remote_components.strip():
        opts["remote_components"] = [s.strip() for s in remote_components.split(",") if s.strip()]
    return opts


@contextmanager
def youtube_cookies_file():
    """Create a temporary cookies file from env vars if present."""
    cookies_file_path = os.environ.get("YOUTUBE_COOKIES_FILE")
    if cookies_file_path:
        path = Path(cookies_file_path)
        if path.exists():
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".txt", mode="w", encoding="utf-8"
                ) as tmp:
                    tmp.write(path.read_text(encoding="utf-8"))
                    tmp_path = tmp.name
                logger.info("YouTube cookies source=FILE path_exists=True")
                yield tmp_path
                return
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        logger.warning("YouTube cookies source=FILE path_exists=False")

    cookies_content = None
    source = "NONE"

    cookies_b64 = os.environ.get("YOUTUBE_COOKIES_B64")
    if cookies_b64:
        try:
            cookies_content = base64.b64decode(cookies_b64).decode("utf-8")
            source = "B64"
        except (binascii.Error, UnicodeDecodeError):
            logger.warning("YouTube cookies source=B64 decode_failed=True")
            cookies_content = None

    if not cookies_content:
        cookies_content = os.environ.get("YOUTUBE_COOKIES")
        if cookies_content:
            source = "RAW"

    if not cookies_content:
        logger.warning("YouTube cookies source=NONE cookies_loaded=False")
        yield None
        return

    contains_youtube = ".youtube.com" in cookies_content or "youtube.com" in cookies_content
    logger.info(
        "YouTube cookies source=%s cookies_len=%d contains_youtube_domain=%s",
        source,
        len(cookies_content),
        contains_youtube,
    )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".txt", mode="w", encoding="utf-8"
        ) as tmp:
            tmp.write(cookies_content)
            tmp_path = tmp.name
        logger.info("YouTube cookies temp_file_created=True")
        yield tmp_path
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------- FETCH VIDEO / PLAYLIST INFO ---------------- #

def fetch_video_info(video_url, progress_callback=None):
    with youtube_cookies_file() as cookies_path:
        # Do a fast flat extraction first to check if this is a video or playlist
        flat_opts = {
            "quiet":         True,
            "skip_download": True,
            "ignoreerrors":  True,
            "noplaylist":    False,
            "extract_flat":  True,
            "no_warnings":   True,
            "logger":        SilentLogger()
        }
        flat_opts.update(yt_dlp_js_options())
        if cookies_path:
            flat_opts["cookiefile"] = cookies_path

        try:
            with YoutubeDL(flat_opts) as ydl:
                flat_info = ydl.extract_info(video_url, download=False)
        except Exception as ex:
            logger.exception("Flat metadata extraction failed for url=%s", video_url)
            message = str(ex).strip() or ex.__class__.__name__
            return {"error": f"Failed to extract video information: {message}"}, []

        if not flat_info:
            return {"error": "No video information found"}, []

        entries = flat_info.get("entries")


    # ---------------- PLAYLIST ---------------- #

        if entries:
            all_entries = [e for e in entries if e]
            total       = len(all_entries)
            videos      = []
            skipped     = []

            # Full extraction options used per individual video
            full_opts = {
                "quiet":         True,
                "skip_download": True,
                "ignoreerrors":  True,
                "noplaylist":    True,
                "extract_flat":  False,
                "no_warnings":   True,
                "logger":        SilentLogger()
            }
            full_opts.update(yt_dlp_js_options())
            if cookies_path:
                full_opts["cookiefile"] = cookies_path

            for i, entry in enumerate(all_entries):
                entry_url = entry.get("url") or entry.get("webpage_url")

                # Skip entries with no resolvable URL
                if not entry_url:
                    skipped.append(entry.get("title") or f"Video {i+1}")
                    if progress_callback:
                        progress_callback({
                            "status":  "fetch_progress",
                            "current": i + 1,
                            "total":   total,
                            "title":   entry.get("title") or f"Video {i+1}",
                            "skipped": True
                        })
                    continue

                # Flat extraction sometimes returns bare video IDs instead of full URLs
                if not entry_url.startswith("http"):
                    entry_url = "https://www.youtube.com/watch?v=" + entry_url

                if progress_callback:
                    progress_callback({
                        "status":  "fetch_progress",
                        "current": i + 1,
                        "total":   total,
                        "title":   entry.get("title") or f"Video {i+1}",
                        "skipped": False
                    })

                # Fetch full metadata for this video
                try:
                    with YoutubeDL(full_opts) as ydl:
                        info = ydl.extract_info(entry_url, download=False)
                except Exception:
                    info = None

                # Skip videos that are private, deleted, or otherwise unavailable
                if not info or info.get("availability") not in (None, "public", ""):
                    skipped.append(entry.get("title") or f"Video {i+1}")
                    if progress_callback:
                        progress_callback({
                            "status":  "fetch_progress",
                            "current": i + 1,
                            "total":   total,
                            "title":   entry.get("title") or f"Video {i+1}",
                            "skipped": True
                        })
                    continue

                videos.append({
                    "url":      info.get("webpage_url") or entry_url,
                    "title":    info.get("title") or entry.get("title"),
                    "duration": format_duration(info.get("duration")),
                    "uploader": info.get("uploader") or info.get("channel")
                })

            if progress_callback:
                progress_callback({"status": "fetch_done"})

            return {
                "type":   "playlist",
                "title":  flat_info.get("title"),
                "url":    flat_info.get("webpage_url") or video_url,
                "videos": videos,
                "count":  len(videos)
            }, skipped


    # ---------------- SINGLE VIDEO ---------------- #

        if progress_callback:
            progress_callback({
                "status":  "fetch_progress",
                "current": 1,
                "total":   1,
                "title":   flat_info.get("title") or "Video",
                "skipped": False
            })

    # Re-fetch with full metadata now that we know it is a single video
        full_opts = {
            "quiet":         True,
            "skip_download": True,
            "ignoreerrors":  True,
            "noplaylist":    True,
            "extract_flat":  False,
            "no_warnings":   True,
            "logger":        SilentLogger()
        }
        full_opts.update(yt_dlp_js_options())
        if cookies_path:
            full_opts["cookiefile"] = cookies_path

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
            "type":     "video",
            "url":      info.get("webpage_url") or video_url,
            "title":    info.get("title"),
            "duration": format_duration(info.get("duration")),
            "uploader": info.get("uploader") or info.get("channel")
        }, []


# ---------------- DOWNLOAD AUDIO ---------------- #

def download_audio(video_urls, video_type, total_videos=1, progress_callback=None):
    # Each URL is a single video — yt-dlp never sees unavailable playlist entries
    job_id        = str(uuid.uuid4())
    download_path = TEMP_DIR / job_id
    os.makedirs(download_path, exist_ok=True)

    completed = [0]

    def ydl_progress_hook(d):
        if progress_callback is None:
            return

        if d["status"] == "downloading":
            total        = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            downloaded   = d.get("downloaded_bytes", 0)
            pct          = int(downloaded / total * 100)
            display_name = Path(d.get("filename", "")).stem

            progress_callback({
                "status":   "progress",
                "percent":  pct,
                "filename": display_name,
                "current":  completed[0] + 1,
                "total":    total_videos
            })

        elif d["status"] == "finished":
            # Increment counter after each file finishes, before FFmpeg post-processing
            completed[0] += 1
            progress_callback({
                "status":  "progress",
                "percent": 100,
                "current": completed[0],
                "total":   total_videos
            })

    with youtube_cookies_file() as cookies_path:
        ydl_opts = {
            "format":  "bestaudio/best",
            "outtmpl": str(download_path / "%(title)s.%(ext)s"),
            "ffmpeg_location": resolve_ffmpeg_location(),
            "postprocessors": [{
                "key":              "FFmpegExtractAudio",
                "preferredcodec":   "mp3",
                "preferredquality": "320"
            }],
            "concurrent_fragment_downloads": 4,
            "skip_unavailable_fragments":    True,
            "ignoreerrors":   True,
            "logger":         SilentLogger(),
            "no_warnings":    True,
            "noplaylist":     True,   # each call receives exactly one video URL
            "quiet":          True,
            "progress_hooks": [ydl_progress_hook],
        }
        ydl_opts.update(yt_dlp_js_options())
        if cookies_path:
            ydl_opts["cookiefile"] = cookies_path

        last_info = None
        with YoutubeDL(ydl_opts) as ydl:
            for url in video_urls:
                try:
                    info = ydl.extract_info(url, download=True)
                    if info:
                        last_info = info
                except Exception:
                    pass  # ignoreerrors handles failures; this is belt-and-suspenders

    if progress_callback:
        progress_callback({"status": "done"})

    return download_path, last_info


# ---------------- CLEANUP OLD DOWNLOADS ---------------- #

def cleanup_downloads(max_age_seconds=3600):
    if not TEMP_DIR.exists():
        return

    now = time.time() 

    for item in TEMP_DIR.iterdir():
        if item.is_dir():
            folder_age = now - item.stat().st_mtime
            if folder_age > max_age_seconds:
                shutil.rmtree(item, ignore_errors=True)