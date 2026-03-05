# Playlist2Mp3

## Overview

Playlist2Mp3 is a web application that converts YouTube videos and playlists into MP3 audio files for download. Users can download single videos or entire playlists, with playlists packaged into a ZIP archive. The app simplifies downloading multiple songs at once and provides an easy-to-use interface for all users.

---

## Motivation

Downloading music from YouTube can be tedious because most free tools only allow one video at a time. Playlist2Mp3 was created to automate this process. By providing a single playlist link, users can quickly convert all videos to MP3s, saving time and effort.

This project also served as a learning exercise for backend development, frontend–backend integration, media processing, and file management.

---

## Goals

### Primary Goals

- Convert a single YouTube video to MP3
- Convert entire playlists to MP3
- Download single MP3s or ZIP archives for playlists

### Secondary Goals

- Cleanup of temporary files
- Progress indicators during conversion
- Improved frontend design and responsiveness
- Support for additional audio formats
- Deployment as an online web service

---

## Scope & Limitations

### In Scope

- Single video to MP3 conversion
- Playlist to MP3 conversion with ZIP packaging
- Audio quality selection
- Browser downloads via frontend interface
- Basic error handling for invalid URLs and unavailable videos

### Out of Scope

- Allow users to choose audio quality
- Video downloads in MP4 format
- Downloads from platforms other than YouTube
- User accounts or authentication
- Permanent server-side storage of files
- Streaming or playback features
- Mobile applications

### Ethical / Legal Considerations

The app is intended for personal and educational use. Users must ensure downloaded content complies with copyright laws. Playlist2Mp3 does not host or distribute media; it only processes publicly accessible URLs provided by the user.

---

## Target Users

Playlist2Mp3 is designed for anyone who wants to download YouTube music playlists or videos without technical knowledge. Typical users include individuals who want to save albums, playlists, or personal music collections for offline listening.

---

## Technology Stack

| Layer | Technology/Library | Purpose/Role |
| --- | --- | --- |
| Frontend | HTML | Structure the user interface |
|  | CSS | Style the interface and layout |
|  | JavaScript | Fetch API requests and handle downloads |
| Backend | Python | Server logic, file handling, media processing |
|  | Flask | Web framework for backend routes |
| Tools | yt-dlp | Download videos and playlists from YouTube |
|  | FFmpeg | Convert video audio to MP3 |
|  | Python Std Lib | File management, temporary directories, ZIP creation |