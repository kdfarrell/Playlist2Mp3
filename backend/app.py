from flask import Flask, request, render_template, session, redirect, url_for, send_file
from downloader import download_audio, fetch_video_info
from pathlib import Path
import os
import tempfile
import zipfile

# Base directories
BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
PROJECT_DOWNLOADS = os.path.join(os.path.dirname(BASE_DIR), "downloads")
os.makedirs(PROJECT_DOWNLOADS, exist_ok=True)

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"),
    static_url_path="/static"
)
app.secret_key = "supersecret"  # required for session

# ---------------- Routes ---------------- #

@app.route("/")
def home():
    return render_template("index.html", video_info=None)

@app.route("/fetch_info")
def fetch_info():
    url = request.args.get("url")
    if not url:
        return redirect(url_for("home"))

    video_info = fetch_video_info(url)
    if "error" in video_info:
        return render_template("index.html", error=video_info["error"])

    # Store info in session
    session["video_info"] = video_info
    return render_template("index.html", video_info=video_info)

@app.route("/download")
def download():
    video_info = session.get("video_info")
    if not video_info:
        return redirect(url_for("home"))

    try:
        path = Path(download_audio(video_info["url"], video_info["type"], PROJECT_DOWNLOADS))
        session.pop("video_info", None)  # clear session

        # Single video → send MP3 directly
        if video_info["type"] == "video":
            if path.exists():
                return send_file(path, as_attachment=True, download_name=path.name)
            else:
                return "File not found.", 404

        # Playlist → zip folder on-the-fly
        elif video_info["type"] == "playlist":
            zip_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            with zipfile.ZipFile(zip_temp.name, "w", zipfile.ZIP_DEFLATED) as zipf:
                for mp3_file in path.glob("*.mp3"):
                    zipf.write(mp3_file, arcname=mp3_file.name)
            return send_file(zip_temp.name, as_attachment=True, download_name=f"{path.name}.zip")

        else:
            return "Invalid type.", 400

    except Exception as e:
        return f"Error during download: {str(e)}", 500

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