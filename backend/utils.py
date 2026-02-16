from urllib.parse import urlparse

class SilentLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        ignore_phrases = [
            "No supported JavaScript runtime",
            "ffmpeg not found",
            "unavailable videos are hidden"
        ]
        if not any(phrase in msg for phrase in ignore_phrases):
            print(msg)

    def error(self, msg):
        print(msg)  


def is_valid_url(url):
    parsed = urlparse(url)

    # Must be http or https
    if parsed.scheme not in ["https", "http"]:
        return False

    # Must be one of the allowed domains
    if parsed.netloc not in ["youtube.com", "m.youtube.com", "youtu.be"]:
        return False

    # For www/m.youtube.com, check path
    if parsed.netloc in ["www.youtube.com", "m.youtube.com"]:
        if parsed.path not in ["/watch", "/playlist"] and not parsed.path.startswith("/shorts"):
            return False

    # For youtu.be, must have a video ID
    if parsed.netloc == "youtu.be":
        if not parsed.path.strip("/"):
            return False

    return True


    
