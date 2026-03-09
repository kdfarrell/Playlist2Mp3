from urllib.parse import urlparse
import re

# ---------------- Logger ---------------- #
class SilentLogger:
    """
    Logger that ignores certain messages to reduce clutter
    """
    def debug(self, msg):
        pass

    def warning(self, msg):
        ignore_phrases = [
            "No supported JavaScript runtime",
            "ffmpeg not found",
            "unavailable videos are hidden"
        ]
        should_ignore = False
        for phrase in ignore_phrases:
            if phrase in msg:
                should_ignore = True
        if not should_ignore:
            print(msg)

    def error(self, msg):
        print(msg)

# ---------------- URL Validation ---------------- #
def is_valid_url(url):
    """
    Check if a URL is a valid YouTube video or playlist URL
    """
    parsed = urlparse(url)

    if parsed.scheme not in ["https", "http"]:
        return False

    if parsed.netloc not in ["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"]:
        return False

    if parsed.netloc in ["www.youtube.com", "m.youtube.com"]:
        if parsed.path not in ["/watch", "/playlist"] and not parsed.path.startswith("/shorts"):
            return False

    if parsed.netloc == "youtu.be":
        if not parsed.path.strip("/"):
            return False

    return True

# ---------------- Safe Filename ---------------- #
def safe_filename(name):
    """
    Remove characters that are illegal in file names
    """
    return re.sub(r'[\\/*?:"<>|]', "", name)

# ---------------- Duration Formatting ---------------- #
def format_duration(seconds):
    """
    Convert seconds to H:MM:SS or M:SS format
    """
    if seconds is None:
        return None

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"  # H:MM:SS
    else:
        return f"{minutes}:{secs:02d}"              # M:SS