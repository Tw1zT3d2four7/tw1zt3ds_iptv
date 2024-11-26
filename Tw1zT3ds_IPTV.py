import requests
import subprocess
import yaml
from flask import Flask, Response, stream_with_context

# Load configuration from config.yml
with open("config.yml", "r") as config_file:
    config = yaml.safe_load(config_file)

# Get M3U and EPG URLs from the config
M3U_URL = config['sources']['m3u_url']
EPG_URL = config['sources']['epg_url']
city = config.get('city', "charlotte.nc.us")  # Default to "charlotte.nc.us" if not specified

# Flask app configuration
app = Flask(__name__)

# FFmpeg command profile
ffmpeg_command = [
    "-hide_banner", "-loglevel", "info", "-reconnect", "1", "-reconnect_streamed", "1", 
    "-reconnect_delay_max", "4294", "-analyzeduration", "2000000", "-probesize", "10000000", 
    "-i", "{streamUrl}", "-map_metadata", "-1", "-map_chapters", "-1", "-rtbufsize", "5M", 
    "-thread_queue_size", "4096", "-map", "0:0", "-map", "0:1", "-map", "-0:s", "-c:v", "libx264", 
    "-pix_fmt", "yuv420p", "-preset", "fast", "-tune", "film", "-crf", "23", "-maxrate", "8000000", 
    "-bufsize", "16000000", "-profile:v", "main", "-level", "4.1", "-x264opts", "subme=0:me_range=4:rc_lookahead=10:partitions=none", 
    "-force_key_frames", '"expr:gte(t,n_forced*3)"', "-vf", "yadif=0:-1:0", "-c:a", "aac", "-ac", "2", 
    "-b:a", "192k", "-f", "mpegts", "-copyts", "1", "-async", "1", "-movflags", "+faststart", "pipe:1"
]

# Function to fetch M3U playlist and extract country group names
def get_country_groups(m3u_url, enable_us_local_filter=False, allowed_tvg_names=None, playlist_groups=None):
    """
    Fetches and filters an M3U playlist based on group-title and optionally tvg-name for US Local.
    """
    try:
        # Fetch the M3U playlist from the provided URL
        response = requests.get(m3u_url)
        response.raise_for_status()  # Raise an exception for any non-2xx status codes
        
        # Split the M3U playlist into lines
        lines = response.text.splitlines()
        
        # List to hold the filtered channels
        filtered_channels = []

        # Iterate through each line to find group names in the EXTINF lines
        for i, line in enumerate(lines):
            if line.startswith("#EXTINF"):
                # Extract the group-title
                group_start = line.find('group-title="') + len('group-title="')
                group_end = line.find('"', group_start)
                group_title = line[group_start:group_end] if group_start > 0 else None

                # Extract the tvg-name
                name_start = line.find('tvg-name="') + len('tvg-name="')
                name_end = line.find('"', name_start)
                tvg_name = line[name_start:name_end] if name_start > 0 else None

                # Apply filtering for `US Local` channels if us_local_filtering is enabled
                if enable_us_local_filter and group_title == "US Local":
                    # Only include channels whose tvg-name is in the allowed list
                    if allowed_tvg_names and tvg_name in allowed_tvg_names:
                        filtered_channels.append(line)  # Add metadata line
                        if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                            filtered_channels.append(lines[i + 1])  # Add URL line
                    continue  # Skip processing further for US Local channels if not in allowed list

                # General group-title filtering for other groups (not US Local)
                if group_title in playlist_groups and playlist_groups.get(group_title, False):
                    filtered_channels.append(line)  # Add metadata line
                    if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                        filtered_channels.append(lines[i + 1])  # Add URL line

        return filtered_channels

    except requests.exceptions.RequestException as e:
        print(f"Error fetching M3U playlist: {e}")
        return []

# Flask route to serve the M3U playlist
@app.route('/playlist.m3u')
def playlist():
    try:
        # Fetch the allowed tvg-names for US Local channels from the config
        allowed_tvg_names = config.get('us_local_filtering', {}).get('allowed_tvg_names', [])

        # Check if US Local filtering is enabled
        enable_us_local_filter = config.get('us_local_filtering', {}).get('enabled', False)

        # Get the group filter settings from the config
        playlist_groups = config['playlist_groups']

        # Fetch and filter the playlist
        filtered_channels = get_country_groups(
            m3u_url=M3U_URL, 
            enable_us_local_filter=enable_us_local_filter, 
            allowed_tvg_names=allowed_tvg_names,
            playlist_groups=playlist_groups
        )

        # Return the filtered M3U data as the response
        return Response("\n".join(filtered_channels), content_type='application/x-mpegURL')
    except requests.exceptions.RequestException as e:
        return f"Error fetching M3U playlist: {e}"

# Flask route to serve the EPG XML
@app.route('/epg.xml')
def epg():
    try:
        # Fetch the EPG data from the URL
        response = requests.get(EPG_URL)
        response.raise_for_status()  # Raise an exception for any non-2xx status codes

        # Return the EPG data as the response
        return Response(response.content, content_type='application/xml')
    except requests.exceptions.RequestException as e:
        return f"Error fetching EPG data: {e}", 500

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
    app.run(host=config['flask_server']['ip_address'], port=config['flask_server']['port'])

