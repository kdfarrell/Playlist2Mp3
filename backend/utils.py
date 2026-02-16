from urllib.parse import urlparse

class SilentLogger:
    def debug(self, msg):
        pass
    def warning(self, msg):
        if "No supported JavaScript runtime" not in msg:
            print(msg)
    def error(self, msg):
        print(msg)


def is_valid_url(url):
    parsed = urlparse(url)

    # Must use https
    if parsed.scheme != "https":
        return False

    # Must be one of the allowed domains
    if parsed.netloc not in ["www.youtube.com", "m.youtube.com", "youtu.be"]:
        return False

    # Check path
    if parsed.netloc in ["www.youtube.com", "m.youtube.com"]:
        if parsed.path != "/watch" and not parsed.path.startswith("/shorts"):
            return False

    if parsed.netloc == "youtu.be":
        # Must have a video ID in the path
        if len(parsed.path.strip("/")) == 0:
            return False

    return True

    
