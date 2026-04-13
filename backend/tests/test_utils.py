import pytest
from utils import is_valid_url, safe_filename, format_duration


# ----- URL VALIDATION -----

class TestIsValidUrl:
    def test_valid_watch(self):
        assert is_valid_url("https://www.youtube.com/watch?v=abc123")

    def test_valid_playlist(self):
        assert is_valid_url("https://www.youtube.com/playlist?list=PLabc")

    def test_valid_short_url(self):
        assert is_valid_url("https://youtu.be/abc123")

    def test_valid_shorts(self):
        assert is_valid_url("https://www.youtube.com/shorts/abc123")

    def test_invalid_no_scheme(self):
        assert not is_valid_url("youtube.com/watch?v=abc")

    def test_invalid_non_youtube(self):
        assert not is_valid_url("https://vimeo.com/123456")

    def test_invalid_empty_youtu_be(self):
        assert not is_valid_url("https://youtu.be/")

    def test_invalid_wrong_path(self):
        assert not is_valid_url("https://www.youtube.com/channel/UC123")

    def test_http_allowed(self):
        assert is_valid_url("http://www.youtube.com/watch?v=abc")

    def test_mobile_url(self):
        assert is_valid_url("https://m.youtube.com/watch?v=abc")


# ----- SAFE FILENAME -----

class TestSafeFilename:
    def test_removes_illegal_chars(self):
        assert safe_filename("my/file*name?.mp3") == "myfilename.mp3"

    def test_keeps_normal_chars(self):
        assert safe_filename("Normal Title 123") == "Normal Title 123"

    def test_removes_all_illegal(self):
        assert safe_filename('\\/*?:"<>|') == ""


# ----- DURATION FORMATTING -----

class TestFormatDuration:
    def test_seconds_only(self):
        assert format_duration(45) == "0:45"

    def test_minutes_and_seconds(self):
        assert format_duration(90) == "1:30"

    def test_hours(self):
        assert format_duration(3661) == "1:01:01"

    def test_zero(self):
        assert format_duration(0) == "0:00"

    def test_none_returns_none(self):
        assert format_duration(None) is None

    def test_exact_hour(self):
        assert format_duration(3600) == "1:00:00"