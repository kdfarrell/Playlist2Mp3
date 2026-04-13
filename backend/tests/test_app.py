import logging
import sys
import io

import pytest
from unittest.mock import patch

logging.getLogger("yt_dlp").setLevel(logging.CRITICAL)

from app import app as flask_app


# ----- SUPPRESS YT-DLP STDERR NOISE -----
# yt-dlp writes some errors directly to stderr, bypassing Python logging.
# This session-scoped fixture silently swallows that output.

@pytest.fixture(autouse=True, scope="session")
def suppress_ydl_stderr():
    old        = sys.stderr
    sys.stderr = io.StringIO()
    yield
    sys.stderr = old


# ----- FIXTURES -----

@pytest.fixture
def client():
    flask_app.config["TESTING"]    = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    with flask_app.test_client() as c:
        yield c


# ----- HOME -----

class TestHomeRoute:
    def test_home_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_home_contains_form(self, client):
        r = client.get("/")
        assert b"convertForm" in r.data


# ----- FETCH INFO ASYNC -----

class TestFetchInfoAsyncRoute:
    def test_no_url_returns_400(self, client):
        r = client.get("/fetch_info_async")
        assert r.status_code == 400
        assert b"error" in r.data

    def test_invalid_url_returns_400(self, client):
        r = client.get("/fetch_info_async?url=https://vimeo.com/123")
        assert r.status_code == 400
        assert b"Invalid URL" in r.data

    def test_valid_url_returns_job_id(self, client):
        # Patch Thread.start so no background fetch actually runs
        with patch("threading.Thread.start"):
            r = client.get("/fetch_info_async?url=https://www.youtube.com/watch?v=abc123")
        assert r.status_code == 200
        assert "job_id" in r.get_json()


# ----- DOWNLOAD -----

class TestDownloadRoute:
    def test_no_session_returns_400(self, client):
        r = client.get("/download")
        assert r.status_code == 400
        assert "error" in r.get_json()

    def test_empty_playlist_returns_400(self, client):
        with client.session_transaction() as sess:
            sess["video_info"] = {
                "url":    "https://www.youtube.com/playlist?list=PLabc",
                "type":   "playlist",
                "videos": [],
                "count":  0,
                "title":  "Empty Playlist",
            }
            sess["skipped_count"] = 3
        r = client.get("/download")
        assert r.status_code == 400
        assert "error" in r.get_json()

    def test_invalid_type_returns_400(self, client):
        with client.session_transaction() as sess:
            sess["video_info"] = {
                "url":  "https://www.youtube.com/watch?v=fake",
                "type": "invalid_type",
            }
        r = client.get("/download")
        assert r.status_code == 400
        assert "error" in r.get_json()


# ----- DOWNLOAD PROGRESS POLL -----

class TestDownloadProgressRoute:
    def test_unknown_job_returns_404(self, client):
        r = client.get("/download_progress/nonexistent-job-id")
        assert r.status_code == 404
        assert "error" in r.get_json()


# ----- DOWNLOAD FILE -----

class TestDownloadFileRoute:
    def test_unknown_job_returns_404(self, client):
        r = client.get("/download_file/nonexistent-job-id")
        assert r.status_code == 404


# ----- STATIC PAGES -----

class TestStaticPages:
    def test_about(self, client):
        assert client.get("/about").status_code == 200

    def test_faq(self, client):
        assert client.get("/faq").status_code == 200

    def test_how_it_works(self, client):
        assert client.get("/how-it-works").status_code == 200