from urllib.parse import urlparse
import re


# ---------------- SILENT LOGGER ---------------- #

class SilentLogger:
    # Suppress debug output entirely
    def debug(self, msg):
        pass

    # Only print warnings not in the ignore list
    def warning(self, msg):
        ignore_phrases = [
            "No supported JavaScript runtime",
            "ffmpeg not found",
            "unavailable videos are hidden"
        ]
        if not any(phrase in msg for phrase in ignore_phrases):
            print(msg)

    # Always print errors
    def error(self, msg):
        print(msg)


# ---------------- URL VALIDATION ---------------- #

def is_valid_url(url):
    # Reject anything that is not a recognised YouTube domain and path
    parsed = urlparse(url)

    # Must be http or https
    if parsed.scheme not in ["https", "http"]:
        return False

    # Must be a YouTube domain
    if parsed.netloc not in ["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"]:
        return False

    # Standard YouTube domains only allow /watch, /playlist, or /shorts paths
    if parsed.netloc in ["www.youtube.com", "m.youtube.com"]:
        if parsed.path not in ["/watch", "/playlist"] and not parsed.path.startswith("/shorts"):
            return False

    # youtu.be short links must have a video ID in the path
    if parsed.netloc == "youtu.be":
        if not parsed.path.strip("/"):
            return False

    return True


# ---------------- SAFE FILENAME ---------------- #

def safe_filename(name):
    # Strip characters that are illegal in Windows and Unix filenames
    return re.sub(r'[\\/*?:"<>|]', "", name)


# ---------------- DURATION FORMATTING ---------------- #

def format_duration(seconds):
    # Return None if no duration is available
    if seconds is None:
        return None

    hours   = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs    = seconds % 60

    # H:MM:SS for videos over an hour, M:SS otherwise
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"