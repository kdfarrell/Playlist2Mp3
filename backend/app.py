from flask import Flask, request, render_template, session, redirect, url_for, send_file, after_this_request, Response, stream_with_context
from downloader import download_audio, fetch_video_info, cleanup_downloads
from utils import safe_filename, is_valid_url
import os
import io
import tempfile
import zipfile
import shutil
import json
import queue
import threading
import uuid

from pathlib import Path

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

# In-memory progress store: job_id -> list of events
fetch_progress_store = {}
download_progress_store = {}

# Download uses a simple queue (one download at a time)
download_queue = queue.Queue()


# ---------------- Routes ---------------- #
@app.route("/")
def home():
    return render_template("index.html", video_info=None)


# ---------------- Fetch Info ---------------- #
@app.route("/fetch_info")
def fetch_info():
    url = request.args.get("url")
    if not url:
        return redirect(url_for("home"))

    if not is_valid_url(url):
        return render_template("index.html", video_info=None,
                               fetch_error="Invalid URL. Please enter a valid YouTube URL.")

    job_id = str(uuid.uuid4())
    fetch_progress_store[job_id] = {"events": [], "done": False}

    result_holder = {}

    def progress_callback(data):
        fetch_progress_store[job_id]["events"].append(data)

    def run_fetch():
        video_info, skipped = fetch_video_info(url, progress_callback=progress_callback)
        result_holder["video_info"] = video_info
        result_holder["skipped"] = skipped
        fetch_progress_store[job_id]["done"] = True

    t = threading.Thread(target=run_fetch)
    t.start()
    t.join()

    # Clean up progress store
    fetch_progress_store.pop(job_id, None)

    video_info = result_holder.get("video_info", {})
    skipped = result_holder.get("skipped", [])

    if "error" in video_info:
        return render_template("index.html", video_info=None,
                               fetch_error=video_info["error"])

    session["video_info"] = video_info
    session["skipped_count"] = len(skipped)
    return render_template("index.html", video_info=video_info, skipped=skipped)


# ---------------- Fetch Info JSON (async polling endpoint) ---------------- #
@app.route("/fetch_info_async")
def fetch_info_async():
    """
    Kicks off a background fetch and returns a job_id immediately.
    The client polls /fetch_progress/<job_id> for updates.
    When done, the client calls /fetch_result/<job_id> for the final HTML.
    """
    url = request.args.get("url")
    if not url or not is_valid_url(url):
        return {"error": "Invalid URL. Please enter a valid YouTube URL."}, 400

    job_id = str(uuid.uuid4())
    fetch_progress_store[job_id] = {
        "events": [],
        "done": False,
        "video_info": None,
        "skipped": [],
        "error": None
    }

    def progress_callback(data):
        fetch_progress_store[job_id]["events"].append(data)

    def run_fetch():
        video_info, skipped = fetch_video_info(url, progress_callback=progress_callback)
        store = fetch_progress_store.get(job_id)
        if store is None:
            return
        if "error" in video_info:
            store["error"] = video_info["error"]
        else:
            store["video_info"] = video_info
            store["skipped"] = skipped
        store["done"] = True

    t = threading.Thread(target=run_fetch)
    t.start()

    return {"job_id": job_id}


# ---------------- Poll fetch progress ---------------- #
@app.route("/fetch_progress/<job_id>")
def fetch_progress_poll(job_id):
    store = fetch_progress_store.get(job_id)
    if store is None:
        return {"error": "Job not found"}, 404

    # Return all pending events and whether done
    events = store["events"][:]
    store["events"] = []  # clear consumed events

    return {
        "events": events,
        "done": store["done"],
        "error": store.get("error"),
        "skipped": store.get("skipped", []) if store["done"] else []
    }


# ---------------- Fetch result HTML ---------------- #
@app.route("/fetch_result/<job_id>")
def fetch_result(job_id):
    store = fetch_progress_store.pop(job_id, None)
    if store is None:
        return render_template("index.html", video_info=None,
                               fetch_error="Session expired. Please try again.")

    if store.get("error"):
        return render_template("index.html", video_info=None,
                               fetch_error=store["error"])

    video_info = store.get("video_info")
    skipped = store.get("skipped", [])

    if not video_info:
        return render_template("index.html", video_info=None,
                               fetch_error="Failed to load video info.")

    session["video_info"] = video_info
    session["skipped_count"] = len(skipped)
    return render_template("index.html", video_info=video_info, skipped=skipped)


# ---------------- SSE: Download Progress ---------------- #
@app.route("/progress")
def progress():
    def generate():
        while True:
            try:
                msg = download_queue.get(timeout=60)
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("status") in ("done", "error"):
                    break
            except queue.Empty:
                yield 'data: {"status":"heartbeat"}\n\n'

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


# ---------------- Download ---------------- #
# Replace the /download route
@app.route("/download")
def download():
    """Step 1: start the download job, return a job_id immediately."""
    video_info = session.get("video_info")
    if not video_info:
        return {"error": "Session expired."}, 400

    if video_info["type"] == "playlist" and video_info.get("count", 0) == 0:
        return {"error": "No downloadable videos found in this playlist."}, 400

    cleanup_downloads(max_age_seconds=3600)

    skipped_count = session.get("skipped_count", 0)
    total_videos = video_info.get("count", 1) if video_info["type"] == "playlist" else 1

    if video_info["type"] == "playlist":
        urls_to_download = [v["url"] for v in video_info.get("videos", [])]
    else:
        urls_to_download = [video_info["url"]]

    job_id = str(uuid.uuid4())
    download_progress_store[job_id] = {
        "events": [],
        "done": False,
        "error": None,
        "path": None,
        "video_info": video_info,
        "skipped_count": skipped_count
    }

    def progress_callback(d):
        store = download_progress_store.get(job_id)
        if store:
            store["events"].append(d)

    def run_download():
        store = download_progress_store.get(job_id)
        try:
            path, info = download_audio(
                urls_to_download,
                video_info["type"],
                total_videos=total_videos,
                progress_callback=progress_callback
            )
            if store:
                store["path"] = str(path)
        except Exception as ex:
            if store:
                store["error"] = str(ex)
        finally:
            if store:
                store["done"] = True

    t = threading.Thread(target=run_download)
    t.start()

    return {"job_id": job_id}


@app.route("/download_progress/<job_id>")
def download_progress_poll(job_id):
    """Step 2: poll this while the download runs."""
    store = download_progress_store.get(job_id)
    if store is None:
        return {"error": "Job not found"}, 404

    events = store["events"][:]
    store["events"] = []

    return {
        "events": events,
        "done": store["done"],
        "error": store.get("error")
    }


@app.route("/download_file/<job_id>")
def download_file(job_id):
    """Step 3: called once polling says done — streams the actual file."""
    store = download_progress_store.pop(job_id, None)
    if store is None:
        return "Job not found or expired.", 404

    if store.get("error"):
        return f"Download failed: {store['error']}", 500

    download_path = Path(store["path"])
    video_info = store["video_info"]
    skipped_count = store["skipped_count"]

    mp3_files = [f for f in download_path.iterdir() if f.suffix.lower() == ".mp3"]

    session.pop("video_info", None)
    session.pop("skipped_count", None)

    if video_info["type"] == "video":
        if not mp3_files:
            return "File not found.", 404
        mp3_file = mp3_files[0]
        clean_name = safe_filename(video_info.get("title", mp3_file.stem)) + ".mp3"

        @after_this_request
        def cleanup(response):
            shutil.rmtree(download_path, ignore_errors=True)
            return response

        response = send_file(mp3_file, as_attachment=True, download_name=clean_name)
        response.headers["X-Skipped-Count"] = str(skipped_count)
        return response

    elif video_info["type"] == "playlist":
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

        response = send_file(zip_bytes, as_attachment=True,
                             download_name=f"{playlist_name}.zip",
                             mimetype="application/zip")
        response.headers["X-Skipped-Count"] = str(skipped_count)
        return response

    return "Invalid type.", 400

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

if __name__ == "__main__":
    app.run(debug=True, threaded=True)