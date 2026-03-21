from flask import Flask, request, render_template, session, redirect, url_for, send_file, flash, after_this_request
from downloader import download_audio, fetch_video_info, cleanup_downloads
from utils import safe_filename, is_valid_url
from pathlib import Path
import os
import io
import tempfile
import zipfile
import shutil

# ---------------- App Setup ---------------- #
BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"),
    static_url_path="/static"
)

app.secret_key = "supersecret"

# ---------------- Routes ---------------- #
@app.route("/")
def home():
    return render_template("index.html", video_info=None)


 # Fetch video or playlist info and store in session
@app.route("/fetch_info") 
def fetch_info():

    url = request.args.get("url")
    if not url:
        return redirect(url_for("home"))

    if not is_valid_url(url):
        flash("Invalid URL! Please enter a valid URL.", "error")
        return redirect(url_for("home"))


    video_info = fetch_video_info(url)
    if "error" in video_info:
        return render_template("index.html", error=video_info["error"])

    session["video_info"] = video_info
    return render_template("index.html", video_info=video_info)

# ---------------- Download single video or playlist ---------------- #
@app.route("/download")
def download():
    video_info = session.get("video_info")
    if not video_info:
        return redirect(url_for("home"))

    try:
        # Clean old downloads first
        cleanup_downloads(max_age_seconds=3600)

        # Download audio
        download_path, info = download_audio(video_info["url"], video_info["type"])
        session.pop("video_info", None)

        # Gather all mp3 files in download folder
        mp3_files = []
        for f in download_path.iterdir():
            if f.suffix.lower() == ".mp3":
                mp3_files.append(f)

        # ---------------- Single Video ---------------- #

        if video_info["type"] == "video":
            if len(mp3_files) == 0:
                return "File not found.", 404

            mp3_file = mp3_files[0]

            @after_this_request
            def cleanup(response):
                shutil.rmtree(download_path, ignore_errors=True)
                return response

            return send_file(mp3_file, as_attachment=True, download_name=mp3_file.name)

        # ---------------- Playlist ---------------- #

        elif video_info["type"] == "playlist":
            if len(mp3_files) == 0:
                return "No audio files found in playlist.", 404

            zip_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            zip_temp.close()

            with zipfile.ZipFile(zip_temp.name, "w", zipfile.ZIP_DEFLATED) as zipf:
                for f in mp3_files:
                    zipf.write(f, arcname=f.name)

            playlist_name = safe_filename(info.get("title", video_info.get("title", "playlist")))

            # Read zip into memory, then delete files before sending
            with open(zip_temp.name, "rb") as f:
                zip_bytes = io.BytesIO(f.read())

            os.unlink(zip_temp.name)
            shutil.rmtree(download_path, ignore_errors=True)

            return send_file(zip_bytes, as_attachment=True, download_name=f"{playlist_name}.zip", mimetype="application/zip")

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