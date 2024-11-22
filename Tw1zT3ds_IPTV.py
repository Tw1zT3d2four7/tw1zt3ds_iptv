import ffmpeg
import requests
from flask import Flask, Response, stream_with_context
import yaml
import subprocess

# Load configuration from config.yml
with open("config.yml", "r") as config_file:
    config = yaml.safe_load(config_file)

# Get M3U and EPG URLs from the config
M3U_URL = config['sources']['m3u_url']
EPG_URL = config['sources']['epg_url']

# Flask app configuration
app = Flask(__name__)

# FFmpeg command profile settings
ffmpeg_command = [
    config['ffmpeg']['command']['input_url'].format(url=M3U_URL),
    '-c:v', config['ffmpeg']['command']['video_codec'],
    '-c:a', config['ffmpeg']['command']['audio_codec'],
    '-b:a', config['ffmpeg']['command']['audio_bitrate'],
    '-ac', config['ffmpeg']['command']['audio_channels'],
    '-f', config['ffmpeg']['command']['output_format'],
    '-strict', config['ffmpeg']['command']['strict'],
    '-pix_fmt', config['ffmpeg']['command']['pix_fmt'],
    '-bf', config['ffmpeg']['command']['bf'],
    '-preset', config['ffmpeg']['command']['preset'],
    '-tune', config['ffmpeg']['command']['tune'],
    '-rc', config['ffmpeg']['command']['rc'],
    '-multipass', config['ffmpeg']['command']['multipass'],
    '-fflags', config['ffmpeg']['command']['fflags'],
    '-timeout', config['ffmpeg']['command']['timeout'],
    '-muxdelay', config['ffmpeg']['command']['muxdelay'],
    '-max_interleave_delta', config['ffmpeg']['command']['max_interleave_delta'],
    '-async', config['ffmpeg']['command']['async'],
    '-copyts', config['ffmpeg']['command']['copyts'],
    '-'
]

# Flask route to serve the M3U playlist
@app.route('/playlist.m3u')
def playlist():
    try:
        # Fetch the M3U playlist from the provided URL
        response = requests.get(M3U_URL)
        response.raise_for_status()

        # Return the M3U data as the response
        return Response(response.text, content_type='application/x-mpegURL')
    except requests.exceptions.RequestException as e:
        return f"Error fetching M3U playlist: {e}"

# Flask route to serve the EPG XML data
@app.route('/epg.xml')
def epg():
    try:
        # Fetch the EPG XML data from the provided URL
        response = requests.get(EPG_URL)
        response.raise_for_status()

        # Return the EPG XML data as the response
        return Response(response.text, content_type='application/xml')
    except requests.exceptions.RequestException as e:
        return f"Error fetching EPG data: {e}"

# Flask route to stream the video directly via FFmpeg
@app.route('/stream')
def stream():
    def generate():
        # Start FFmpeg process and pipe the output to Flask
        process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        while True:
            # Read the output from FFmpeg
            output = process.stdout.read(1024)
            if not output:
                break
            yield output

    return Response(stream_with_context(generate()), content_type='video/mp2t')

# Flask server configuration (host and port)
if __name__ == "__main__":
    # Run the Flask server in the background
    app.run(host=config['flask_server']['ip_address'], port=config['flask_server']['port'])

