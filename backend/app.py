from flask import Flask, request, render_template, session, url_for, send_file, after_this_request
from downloader import download_audio, fetch_video_info, cleanup_downloads
from utils import safe_filename, is_valid_url
from pathlib import Path
import os
import io
import tempfile
import zipfile
import shutil
import threading
import uuid
import sys
import logging


# ----- APP SETUP -----

BASE_DIR     = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
    force=True,
)

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"),
    static_url_path="/static"
)

app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret-key-change-me")
app.logger.setLevel(log_level)

# In-memory job stores keyed by job_id
fetch_progress_store    = {}
download_progress_store = {}


# ----- HOME -----

@app.route("/")
def home():
    return render_template("index.html", video_info=None)


# ----- FETCH INFO ASYNC -----

@app.route("/fetch_info_async")
def fetch_info_async():
    """Kick off a background fetch job and return a job_id immediately.
    The client polls /fetch_progress/<job_id>, then loads /fetch_result/<job_id>."""
    url = request.args.get("url")
    if not url or not is_valid_url(url):
        return {"error": "Invalid URL. Please enter a valid YouTube URL."}, 400

    job_id = str(uuid.uuid4())
    fetch_progress_store[job_id] = {
        "events":     [],
        "done":       False,
        "video_info": None,
        "skipped":    [],
        "error":      None,
    }

    def progress_callback(data):
        fetch_progress_store[job_id]["events"].append(data)

    def run_fetch():
        store = fetch_progress_store.get(job_id)
        if store is None:
            return

        try:
            video_info, skipped = fetch_video_info(url, progress_callback=progress_callback)

            if "error" in video_info:
                store["error"] = video_info["error"]
            else:
                store["video_info"] = video_info
                store["skipped"]    = skipped
        except Exception as ex:
            store["error"] = f"Failed to fetch video info: {ex}"
        finally:
            # Always mark the job as done so the client never gets stuck polling.
            store["done"] = True

    threading.Thread(target=run_fetch).start()
    return {"job_id": job_id}


# ----- FETCH PROGRESS POLL -----

@app.route("/fetch_progress/<job_id>")
def fetch_progress_poll(job_id):
    """Return and drain any pending fetch progress events for a job."""
    store = fetch_progress_store.get(job_id)
    if store is None:
        return {"error": "Job not found"}, 404

    events          = store["events"][:]
    store["events"] = []

    return {
        "events":  events,
        "done":    store["done"],
        "error":   store.get("error"),
        "skipped": store.get("skipped", []) if store["done"] else [],
    }


# ----- FETCH RESULTS PAGE -----

@app.route("/fetch_result/<job_id>")
def fetch_result(job_id):
    """Render the results page once the fetch job is complete."""
    store = fetch_progress_store.pop(job_id, None)
    if store is None:
        return render_template("index.html", video_info=None,
                               fetch_error="Session expired. Please try again.")

    if store.get("error"):
        return render_template("index.html", video_info=None,
                               fetch_error=store["error"])

    video_info = store.get("video_info")
    skipped    = store.get("skipped", [])

    if not video_info:
        return render_template("index.html", video_info=None,
                               fetch_error="Failed to load video info.")

    session["video_info"]    = video_info
    session["skipped_count"] = len(skipped)
    return render_template("index.html", video_info=video_info, skipped=skipped)


# ----- DOWNLOAD -----

@app.route("/download")
def download():
    """Step 1: validate the session, start the download job, return a job_id."""
    video_info = session.get("video_info")
    if not video_info:
        return {"error": "Session expired."}, 400

    video_type = video_info.get("type")
    if video_type not in ("video", "playlist"):
        return {"error": "Invalid video type."}, 400

    if video_type == "playlist" and video_info.get("count", 0) == 0:
        return {"error": "No downloadable videos found in this playlist."}, 400

    cleanup_downloads(max_age_seconds=3600)

    skipped_count    = session.get("skipped_count", 0)
    total_videos     = video_info.get("count", 1) if video_type == "playlist" else 1
    urls_to_download = (
        [v["url"] for v in video_info.get("videos", [])]
        if video_type == "playlist"
        else [video_info["url"]]
    )

    job_id = str(uuid.uuid4())
    download_progress_store[job_id] = {
        "events":        [],
        "done":          False,
        "error":         None,
        "path":          None,
        "video_info":    video_info,
        "skipped_count": skipped_count,
    }

    def progress_callback(d):
        store = download_progress_store.get(job_id)
        if store:
            store["events"].append(d)

    def run_download():
        store = download_progress_store.get(job_id)
        try:
            path, _ = download_audio(
                urls_to_download,
                video_type,
                total_videos=total_videos,
                progress_callback=progress_callback,
            )
            if store:
                store["path"] = str(path)
        except Exception as ex:
            if store:
                store["error"] = str(ex)
        finally:
            if store:
                store["done"] = True

    threading.Thread(target=run_download).start()
    return {"job_id": job_id}


# ----- DOWNLOAD PROGRESS POLL -----

@app.route("/download_progress/<job_id>")
def download_progress_poll(job_id):
    """Step 2: drain and return pending download progress events."""
    store = download_progress_store.get(job_id)
    if store is None:
        return {"error": "Job not found"}, 404

    events          = store["events"][:]
    store["events"] = []

    response = {
        "events": events,
        "done":   store["done"],
        "error":  store.get("error"),
    }

    # Include skipped_count in the final poll so the client can show a toast
    # without needing a separate request
    if store["done"] and not store.get("error"):
        response["skipped_count"] = store["skipped_count"]

    return response


# ----- DOWNLOAD FILE -----

@app.route("/download_file/<job_id>")
def download_file(job_id):
    """Step 3: serve the finished file. The browser treats this as a native download."""
    store = download_progress_store.pop(job_id, None)
    if store is None:
        return "Job not found or expired.", 404

    if store.get("error"):
        return f"Download failed: {store['error']}", 500

    download_path = Path(store["path"])
    video_info    = store["video_info"]
    mp3_files     = [f for f in download_path.iterdir() if f.suffix.lower() == ".mp3"]

    session.pop("video_info",    None)
    session.pop("skipped_count", None)

    if video_info["type"] == "video":
        if not mp3_files:
            return "File not found.", 404

        mp3_file   = mp3_files[0]
        clean_name = safe_filename(video_info.get("title", mp3_file.stem)) + ".mp3"

        @after_this_request
        def cleanup(response):
            shutil.rmtree(download_path, ignore_errors=True)
            return response

        return send_file(mp3_file, as_attachment=True, download_name=clean_name)

    if video_info["type"] == "playlist":
        if not mp3_files:
            return "No audio files found in playlist.", 404

        zip_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        zip_temp.close()

        with zipfile.ZipFile(zip_temp.name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for f in mp3_files:
                zipf.write(f, arcname=f.name)

        playlist_name = safe_filename(video_info.get("title", "playlist"))

        with open(zip_temp.name, "rb") as f:
            zip_bytes = io.BytesIO(f.read())

        os.unlink(zip_temp.name)
        shutil.rmtree(download_path, ignore_errors=True)

        return send_file(
            zip_bytes,
            as_attachment=True,
            download_name=f"{playlist_name}.zip",
            mimetype="application/zip",
        )

    return "Invalid type.", 400


# ----- ADDTIONAL PAGES -----

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")


if __name__ == "__main__":
    app.run(debug=True, threaded=True)