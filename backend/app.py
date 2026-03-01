from flask import Flask, request, render_template
from downloader import download_audio, fetch_video_info
from utils import is_valid_url
import os

# Base directories
BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),  # templates/ folder
    static_folder=os.path.join(FRONTEND_DIR, "static"),       # static/ folder
    static_url_path="/static"
)

# ---------------- Routes ---------------- #

@app.route("/")
def home():
    return render_template("index.html", video_info=None)

@app.route("/fetch_info")
def fetch_info():
    url = request.args.get("url")

    if not is_valid_url(url):
        return "Provide a valid URL. /fetch_info route 400", 400
    
    try:
        video_info = fetch_video_info(url)
        return render_template("index.html", video_info=video_info)
    except Exception as e:
        return f"Error fetching video info: {str(e)}", 500

@app.route("/download")
def download():
    url = request.args.get("url")
    video_type = request.args.get("video_type")
    
    if not url:
        return "No URL provided.", 404

    try:
        title = download_audio(url, video_type)
        return f"Downloaded: {title}"
    except Exception as e:
        return f"Error: /download 500", 500

# ---------------- Additional Pages ---------------- #

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")

# ---------------- Run App ---------------- #

if __name__ == "__main__":
    app.run(debug=True)