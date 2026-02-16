from flask import Flask, request, render_template
from downloader import download_audio, fetch_video_info
from utils import is_valid_url
import os

BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(
    __name__,
    template_folder=FRONTEND_DIR,   
    static_folder=FRONTEND_DIR, 
    static_url_path=""
)

@app.route("/")
def home():
    return render_template("index.html", video_info=None)

@app.route("/fetch_info")
def fetch_info():
    url = request.args.get("url")

    if not is_valid_url(url):
        return "Provide a valid url.", 400
    
    try:
        video_info = fetch_video_info(url)
        return render_template("index.html", video_info=video_info)
    except Exception as e:
        return f"Error: {str(e)}", 500


@app.route("/download")
def download():
    url = request.args.get("url")
    
    if not url:
        return "No url provided.", 404

    try:
        title = download_audio(url)
        return f"Downloaded: {title}"
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)