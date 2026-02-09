from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yt_dlp
import os
import uuid
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
import csv
from datetime import datetime, timedelta
import shutil
import threading

app = FastAPI(title="YouTube Downloader")

# Create necessary directories
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Cache file for tracking downloads
CACHE_FILE = DOWNLOADS_DIR / "download_cache.csv"
CACHE_DURATION = timedelta(minutes=30)  # Files kept for 30 minutes

# CSV lock for thread safety
cache_lock = threading.Lock()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Thread pool for async downloads
executor = ThreadPoolExecutor(max_workers=3)


def init_cache_file():
    """Initialize cache CSV file if it doesn't exist"""
    if not CACHE_FILE.exists():
        with open(CACHE_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['url', 'download_id', 'file_name', 'file_path', 'download_time', 'format_type'])


def check_cache(url: str, format_type: str) -> Optional[dict]:
    """Check if URL exists in cache and file is still valid (less than 30 minutes old)"""
    if not CACHE_FILE.exists():
        return None
    
    with cache_lock:
        try:
            with open(CACHE_FILE, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['url'] == url and row['format_type'] == format_type:
                        download_time = datetime.fromisoformat(row['download_time'])
                        age = datetime.now() - download_time
                        
                        # Check if file still exists and is within cache duration
                        file_path = Path(row['file_path'])
                        if age < CACHE_DURATION and file_path.exists():
                            return {
                                'download_id': row['download_id'],
                                'file_name': row['file_name'],
                                'file_path': row['file_path'],
                                'cached': True
                            }
        except Exception as e:
            print(f"Cache check error: {e}")
            return None
    
    return None


def add_to_cache(url: str, download_id: str, file_name: str, file_path: str, format_type: str):
    """Add successful download to cache"""
    with cache_lock:
        try:
            with open(CACHE_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    url,
                    download_id,
                    file_name,
                    file_path,
                    datetime.now().isoformat(),
                    format_type
                ])
        except Exception as e:
            print(f"Cache add error: {e}")


def cleanup_old_files():
    """Remove files and entries older than 30 minutes"""
    if not CACHE_FILE.exists():
        return
    
    with cache_lock:
        try:
            # Read all entries
            with open(CACHE_FILE, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Filter valid entries and delete old ones
            valid_rows = []
            current_time = datetime.now()
            
            for row in rows:
                try:
                    download_time = datetime.fromisoformat(row['download_time'])
                    age = current_time - download_time
                    
                    if age >= CACHE_DURATION:
                        # Delete the file and directory
                        file_path = Path(row['file_path'])
                        if file_path.exists():
                            file_path.unlink()
                        
                        # Delete the download directory if empty
                        download_dir = DOWNLOADS_DIR / row['download_id']
                        if download_dir.exists() and not any(download_dir.iterdir()):
                            download_dir.rmdir()
                        
                        print(f"Cleaned up old download: {row['file_name']}")
                    else:
                        valid_rows.append(row)
                except Exception as e:
                    print(f"Error cleaning entry: {e}")
                    # Keep the row if there's an error
                    valid_rows.append(row)
            
            # Rewrite cache file with valid entries
            with open(CACHE_FILE, 'w', newline='', encoding='utf-8') as f:
                if valid_rows:
                    writer = csv.DictWriter(f, fieldnames=['url', 'download_id', 'file_name', 'file_path', 'download_time', 'format_type'])
                    writer.writeheader()
                    writer.writerows(valid_rows)
                else:
                    # Write header only
                    writer = csv.writer(f)
                    writer.writerow(['url', 'download_id', 'file_name', 'file_path', 'download_time', 'format_type'])
        
        except Exception as e:
            print(f"Cleanup error: {e}")


async def periodic_cleanup():
    """Background task to clean up old files every 5 minutes"""
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        cleanup_old_files()


def get_video_info(url: str) -> dict:
    """Get video information including available formats"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get video formats
            formats = info.get('formats', [])
            
            # Find best quality options
            video_formats = {}
            for f in formats:
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    height = f.get('height')
                    filesize = f.get('filesize') or f.get('filesize_approx', 0)
                    if height and height >= 360:
                        quality = f"{height}p"
                        if quality not in video_formats or filesize > video_formats[quality].get('size', 0):
                            video_formats[quality] = {
                                'quality': quality,
                                'size': filesize,
                                'size_mb': round(filesize / (1024 * 1024), 1) if filesize else 0
                            }
            
            # Estimate audio sizes (approximate)
            duration = info.get('duration', 0)
            
            return {
                "success": True,
                "title": info.get('title', 'Unknown'),
                "duration": duration,
                "thumbnail": info.get('thumbnail'),
                "video_formats": sorted(video_formats.values(), key=lambda x: int(x['quality'].replace('p', '')), reverse=True),
                "audio_estimates": {
                    "mp3_320": round(duration * 320 / 8 / 1024, 1) if duration else 0,  # MB
                    "mp3_192": round(duration * 192 / 8 / 1024, 1) if duration else 0,
                    "wav": round(duration * 1411 / 8 / 1024, 1) if duration else 0,  # 16-bit stereo
                }
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


def download_video(url: str, format_type: str, output_id: str, quality: Optional[str] = None) -> dict:
    """Download video using yt-dlp"""
    try:
        output_path = DOWNLOADS_DIR / output_id
        
        if format_type == "mp3":
            # MP3 Audio (320kbps)
            bitrate = quality if quality else "320"
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': bitrate,
                }],
                'outtmpl': str(output_path / '%(title)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
            }
        elif format_type == "wav":
            # WAV Audio (16-bit)
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                }],
                'postprocessor_args': [
                    '-ar', '44100',  # Sample rate
                    '-ac', '2',       # Stereo
                    '-sample_fmt', 's16'  # 16-bit
                ],
                'outtmpl': str(output_path / '%(title)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
            }
        else:  # mp4
            # Video with quality selection
            if quality:
                # Specific quality requested
                quality_num = quality.replace('p', '')
                format_string = f'bestvideo[height<={quality_num}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality_num}][ext=mp4]/best'
            else:
                # Best quality
                format_string = 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best'
            
            ydl_opts = {
                'format': format_string,
                'outtmpl': str(output_path / '%(title)s.%(ext)s'),
                'merge_output_format': 'mp4',
                'quiet': False,
                'no_warnings': False,
            }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'video')
            
            # Find the downloaded file
            files = list(output_path.glob(f"*{title}*"))
            if files:
                downloaded_file = files[0]
                return {
                    "success": True,
                    "file_path": str(downloaded_file),
                    "file_name": downloaded_file.name,
                    "title": title
                }
            else:
                # Fallback: find any file in the directory
                extensions = ['mp3', 'wav', 'mp4']
                for ext in extensions:
                    files = list(output_path.glob(f"*.{ext}"))
                    if files:
                        downloaded_file = files[0]
                        return {
                            "success": True,
                            "file_path": str(downloaded_file),
                            "file_name": downloaded_file.name,
                            "title": title
                        }
        
        return {"success": False, "error": "File not found after download"}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render home page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/info")
async def get_info(url: str = Form(...)):
    """Get video information"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, get_video_info, url)
    return JSONResponse(content=result)


@app.post("/download")
async def download(
    url: str = Form(...), 
    format: str = Form(...),
    quality: Optional[str] = Form(None)
):
    """Handle download request"""
    if format not in ["mp4", "mp3", "wav"]:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Invalid format. Choose mp4, mp3, or wav."}
        )
    
    # Check if file exists in cache
    cached_result = check_cache(url, format)
    if cached_result:
        print(f"Serving cached file: {cached_result['file_name']}")
        return JSONResponse(content={
            "success": True,
            "message": f"Serving cached file",
            "download_url": f"/file/{cached_result['download_id']}/{cached_result['file_name']}",
            "cached": True
        })
    
    # Generate unique ID for this download
    download_id = str(uuid.uuid4())
    
    # Run download in thread pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        download_video,
        url,
        format,
        download_id,
        quality
    )
    
    if result["success"]:
        # Add to cache
        add_to_cache(
            url,
            download_id,
            result['file_name'],
            result['file_path'],
            format
        )
        
        return JSONResponse(content={
            "success": True,
            "message": f"Downloaded: {result['title']}",
            "download_url": f"/file/{download_id}/{result['file_name']}",
            "cached": False
        })
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": result["error"]}
        )


@app.get("/file/{download_id}/{file_name}")
async def get_file(download_id: str, file_name: str):
    """Serve downloaded file"""
    file_path = DOWNLOADS_DIR / download_id / file_name
    
    if not file_path.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "File not found"}
        )
    
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/octet-stream"
    )


@app.on_event("startup")
async def startup_event():
    """Initialize cache and cleanup old downloads on startup"""
    print("YouTube Downloader started!")
    print(f"Downloads directory: {DOWNLOADS_DIR.absolute()}")
    print(f"Cache duration: {CACHE_DURATION.total_seconds() / 60} minutes")
    
    # Initialize cache file
    init_cache_file()
    
    # Clean up old files from previous runs
    cleanup_old_files()
    
    # Start periodic cleanup task
    asyncio.create_task(periodic_cleanup())
    print("Periodic cleanup task started (runs every 5 minutes)")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
