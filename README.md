# YouTube Downloader Web App

A simple and elegant web application built with FastAPI and Jinja2 templates that allows you to download YouTube videos as MP4 (video) or MP3/WAV (audio) files with customizable quality options.

## Features

- 🎥 Download YouTube videos as MP4 with quality selection (360p, 480p, 720p, 1080p, etc.)
- 🎵 Extract audio as MP3 (320 kbps - maximum quality)
- 🎼 Extract audio as WAV (16-bit uncompressed)
- 📊 View video information and estimated file sizes before downloading
- � Smart caching: Files are cached for 30 minutes - if someone requests the same video, it's served instantly
- 🧹 Automatic cleanup: Downloaded files are automatically deleted after 30 minutes
- �🚀 Fast and asynchronous downloads
- 🎨 Beautiful, responsive UI
- 📱 Mobile-friendly design
- ⚡ Built with FastAPI for high performance

## Prerequisites

Before running this application, make sure you have the following installed:

1. **Python 3.8+**
2. **ffmpeg** - Required for audio extraction and format conversion

### Installing ffmpeg

#### Windows
Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use chocolatey:
```bash
choco install ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
```

## Installation

1. **Clone or navigate to the project directory:**
```bash
cd f:/DEV/YTAV
```

2. **Create a virtual environment (recommended):**
```bash
python -m venv venv
```

3. **Activate the virtual environment:**

   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Usage

1. **Start the application:**
```bash
python main.py
```

   Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5000
```

2. **Open your web browser and navigate to:**
```
http://localhost:5000
```

3. **Download videos:**
   - Paste a YouTube URL in the input field
   - Click "Get Video Info" to see available qualities and estimated file sizes
   - Select your preferred format:
     - **MP4** - Video with quality options (Best, 1080p, 720p, 480p, 360p, etc.)
     - **MP3** - Audio at 320kbps (maximum quality)
     - **WAV** - Uncompressed 16-bit audio
   - Choose your preferred quality (optional, defaults to best available)
   - Click the "Download" button
   - Wait for the download to complete
   - Click the download link to save the file

## Project Structure

```
YTAV/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── .gitignore          # Git ignore file
├── README.md           # This file
├── templates/
│   └── index.html      # HTML template
├── static/
│   └── style.css       # CSS styles
└── downloads/          # Downloaded files (created automatically)
```

## API Endpoints

- `GET /` - Home page
- `POST /info` - Get video information
  - Form parameters:
    - `url`: YouTube video URL
  - Returns: Video title, duration, available formats with sizes, and estimated audio sizes
- `POST /download` - Download a video (with smart caching)
  - Form parameters:
    - `url`: YouTube video URL
    - `format`: Either "mp4", "mp3", or "wav"
    - `quality`: (Optional) Video quality (e.g., "720p") or audio bitrate (e.g., "320")
  - Returns: Download URL and whether file was served from cache
  - Note: If the same URL was downloaded within the last 30 minutes, returns cached file instantly
- `GET /file/{download_id}/{file_name}` - Serve downloaded file

## How Caching Works

1. When a video is successfully downloaded, its URL is stored in a CSV cache file along with file location and timestamp
2. If another user requests the same URL within 30 minutes, the server serves the existing file immediately (no re-download)
3. Every 5 minutes, a background task checks for files older than 30 minutes and deletes them
4. Both the cache entry and the actual file are removed together
5. On server restart, old files are immediately cleaned up

## Dependencies

- **FastAPI** - Modern web framework
- **Uvicorn** - ASGI server
- **Jinja2** - Template engine
- **yt-dlp** - YouTube downloader
- **python-multipart** - Form data parsing
- **aiofiles** - Async file operations

## Notes

- Downloaded files are stored in the `downloads/` directory with a CSV cache file
- Each download creates a unique subdirectory to avoid conflicts
- **Caching System**: URLs are cached for 30 minutes - requesting the same URL within this time serves the cached file instantly
- **Automatic Cleanup**: Files older than 30 minutes are automatically deleted from both the cache and filesystem
- Cleanup runs every 5 minutes and also on server startup
- The application uses async operations for better performance
- Video quality and file size information is fetched before download
- Estimated sizes are approximate and may vary
- MP3 uses 320kbps for maximum audio quality
- WAV format provides uncompressed 16-bit stereo audio at 44.1kHz
- Make sure you have sufficient disk space for downloads
- Respect YouTube's terms of service when downloading content

## Troubleshooting

### "ffmpeg not found" error
Make sure ffmpeg is installed and available in your system PATH.

### Download fails
- Check your internet connection
- Verify the YouTube URL is correct
- Some videos may be region-locked or have download restrictions
- Try updating yt-dlp: `pip install --upgrade yt-dlp`

### Port already in use
Change the port in `main.py` or when running uvicorn:
```bash
uvicorn main:app --port 8080
```

## License

This project is open source and available for educational purposes.

## Disclaimer

This tool is for personal use only. Respect copyright laws and YouTube's terms of service. Do not download copyrighted content without permission.
