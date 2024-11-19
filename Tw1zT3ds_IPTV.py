import os
import time
import requests
import subprocess
import logging
import threading
from flask import Flask, send_file, jsonify, Response
from flask_cors import CORS  # To handle CORS if needed for cross-origin access
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes to avoid issues with accessing resources across domains

# Set up logging to stdout for Flask (this will show in Docker logs or terminal)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)  # Make sure it's at least INFO level to show your messages
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Directory to save M3U and EPG files
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'M3U_&_EPG_Files')
M3U_FILE = os.path.join(DOWNLOAD_DIR, 'm3u_playlist.m3u')
EPG_FILE = os.path.join(DOWNLOAD_DIR, 'epg.xml')

# URLs for downloading M3U and EPG
M3U_URL = "https://bit.ly/ddy-m3u1-all"
EPG_URL = "https://bit.ly/ddy-epg1"

# Max age for files in seconds (12 hours)
MAX_FILE_AGE = 12 * 60 * 60  # 12 hours in seconds

# Path to store the last download timestamp
LAST_DOWNLOAD_TIMESTAMP_FILE = 'last_download_timestamp.json'

# Custom headers for download and streaming
HEADERS = {
    'Referer': 'https://ilovetoplay.xyz/',
    'Origin': 'https://ilovetoplay.xyz',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36'
}

def load_last_download_time():
    """Load the last download timestamp from the file, if it exists."""
    if os.path.exists(LAST_DOWNLOAD_TIMESTAMP_FILE):
        with open(LAST_DOWNLOAD_TIMESTAMP_FILE, 'r') as f:
            return json.load(f).get('last_download_time', None)
    return None

def save_last_download_time(timestamp):
    """Save the current timestamp as the last download time."""
    with open(LAST_DOWNLOAD_TIMESTAMP_FILE, 'w') as f:
        json.dump({'last_download_time': timestamp}, f)

def ensure_files_exist():
    """Ensure the M3U and EPG files exist or need to be downloaded."""
    app.logger.info(f"Ensuring the download folder exists: {DOWNLOAD_DIR}")
    
    # Check if directory exists, create it if not
    if not os.path.exists(DOWNLOAD_DIR):
        app.logger.info(f"Directory not found. Creating directory: {DOWNLOAD_DIR}")
        os.makedirs(DOWNLOAD_DIR)
    
    # Check if M3U and EPG files need to be downloaded based on last download time
    last_download_time = load_last_download_time()

    # If no last download time, or if it's time to redownload (12 hours passed)
    if last_download_time is None or time.time() - last_download_time > MAX_FILE_AGE:
        app.logger.info("Files need to be downloaded or redownloaded...")
        download_m3u()
        download_epg()
        save_last_download_time(time.time())  # Update the last download time
    else:
        app.logger.info("Files are up-to-date based on the last download time.")

def download_m3u():
    """Download the M3U file from the URL with headers."""
    try:
        app.logger.info(f"Downloading M3U file from {M3U_URL}...")
        response = requests.get(M3U_URL, headers=HEADERS)
        response.raise_for_status()  # Will raise an HTTPError if the status is 4xx/5xx
        with open(M3U_FILE, 'wb') as file:
            file.write(response.content)
        app.logger.info("M3U file downloaded successfully.")
    except requests.RequestException as e:
        app.logger.error(f"Error downloading M3U: {e}")

def download_epg():
    """Download the EPG file from the URL with headers."""
    try:
        app.logger.info(f"Downloading EPG file from {EPG_URL}...")
        response = requests.get(EPG_URL, headers=HEADERS)
        response.raise_for_status()  # Will raise an HTTPError if the status is 4xx/5xx
        with open(EPG_FILE, 'wb') as file:
            file.write(response.content)
        app.logger.info("EPG file downloaded successfully.")
    except requests.RequestException as e:
        app.logger.error(f"Error downloading EPG: {e}")

# Flask routes
@app.route('/playlist.m3u')
def serve_m3u():
    """Serve the M3U playlist file."""
    ensure_files_exist()  # Ensure files are downloaded before serving
    app.logger.info(f"Serving M3U playlist at http://0.0.0.0:3037/playlist.m3u")
    return send_file(M3U_FILE, mimetype='application/x-mpegURL')

@app.route('/epg.xml')
def serve_epg():
    """Serve the EPG XML file."""
    ensure_files_exist()  # Ensure files are downloaded before serving
    app.logger.info(f"Serving EPG XML at http://0.0.0.0:3037/epg.xml")
    return send_file(EPG_FILE, mimetype='application/xml')

@app.route('/stream/<path:url>')
def stream(url):
    """Process the stream and pipe it using FFmpeg."""
    try:
        ffmpeg_command = [
            'ffmpeg',
            '-user_agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            '-referer', 'https://ilovetoplay.xyz/',
            '-headers', 'Origin: https://ilovetoplay.xyz',  # Custom headers for streaming
            '-headers', 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            '-i', url,  # Input stream URL
            '-reconnect', '1',
            '-reconnect_streamed', '1',
            '-reconnect_delay_max', '4294',
            '-analyzeduration', '10000000',
            '-probesize', '10000000',
            '-re',
            '-thread_queue_size', '4096',
            '-rtbufsize', '2048k',
            '-map', '0',
            '-c:v', 'copy',
            '-c:a', 'ac3',
            '-b:a', '128k',
            '-ac', '2',
            '-strict', '-2',
            '-pix_fmt', 'yuv420p',
            '-bf', '0',
            '-preset', 'llhp',
            '-tune', 'ull',
            '-rc', 'cbr',
            '-multipass', 'disabled',
            '-fflags', '+genpts',
            '-timeout', '7000000',
            '-muxdelay', '0.001',
            '-max_interleave_delta', '0',
            '-f', 'mpegts',
            '-async', '1',
            '-copyts',
            'pipe:1'  # Output to pipe (for streaming)
        ]
        
        # Run FFmpeg and stream to the player
        process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Return the stream response (to pipe to player)
        return Response(process.stdout, content_type='video/mp2t')

    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return f"Error: {str(e)}", 500

def schedule_file_check():
    """This function will run every 12 hours to check and download files if needed."""
    while True:
        app.logger.info("Checking files every 12 hours...")
        ensure_files_exist()  # Check and download files if outdated or missing
        time.sleep(MAX_FILE_AGE)  # Sleep for 12 hours

if __name__ == "__main__":
    # Ensure the download folder exists and download files if necessary
    ensure_files_exist()
    
    # Print the URLs to the console before starting the Flask app
    app.logger.info(f"Flask app is running at:")
    app.logger.info(f"  M3U URL: http://0.0.0.0:3037/playlist.m3u")
    app.logger.info(f"  EPG URL: http://0.0.0.0:3037/epg.xml")
    
    # Start a background thread to check and update the files every 12 hours
    threading.Thread(target=schedule_file_check, daemon=True).start()
    
    app.run(host='0.0.0.0', port=3037)

