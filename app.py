import os
import uuid
import threading
import time
import requests
import subprocess

from flask import (
    Flask, render_template, request,
    jsonify, send_from_directory
)

app = Flask(__name__)

# Shared state (not for production, but fine here)
progress = {
    "progress": 0,
    "filename": None,
    "error": None
}

TMP_DIR = os.path.join(os.getcwd(), "tmp")
os.makedirs(TMP_DIR, exist_ok=True)


def process_video_task(video_url):
    """
    Downloads the video, runs ffmpeg (or any pipeline),
    updates progress, and sets progress['filename'] when done.
    """
    # Reset state
    progress["progress"] = 0
    progress["filename"] = None
    progress["error"] = None

    infile = os.path.join(TMP_DIR, f"{uuid.uuid4()}.mp4")
    outfile = os.path.join(TMP_DIR, f"{uuid.uuid4()}.mp4")

    try:
        # 1) Download (with progress report)
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            dl = 0
            with open(infile, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if not chunk:
                        break
                    f.write(chunk)
                    dl += len(chunk)
                    if total:
                        progress_pct = int(dl * 50 / total) 
                        progress["progress"] = min(progress_pct, 50)

        # 2) Run ffmpeg (fake a progress)
        #    Replace this command with your real ffmpeg call
        cmd = [
            "ffmpeg", "-y", "-i", infile,
            "-c:v", "libx264", "-c:a", "copy",
            "-preset", "ultrafast",
            "-t", "40",  # for demo
            outfile
        ]

        # We'll fake‐track the ffmpeg steps
        # by incrementing progress up to 100.
        proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)
        # In a real world you’d parse stderr for “time=” and compute %
        while proc.poll() is None:
            time.sleep(0.1)
            # bump from 50 to 100
            if progress["progress"] < 100:
                progress["progress"] += 1

        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd)

        # 3) Done!
        progress["progress"] = 100
        progress["filename"] = os.path.basename(outfile)

    except Exception as e:
        progress["error"] = str(e)

    finally:
        # clean up input file
        try:
            if os.path.exists(infile):
                os.remove(infile)
        except:
            pass


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def start_processing():
    video_url = request.form.get("video_url")
    if not video_url:
        return "Missing video URL", 400

    # Kick off background thread
    thread = threading.Thread(target=process_video_task, args=(video_url,))
    thread.daemon = True
    thread.start()

    return render_template("processing.html")


@app.route("/progress")
def get_progress():
    return jsonify(progress)


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(TMP_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    # dev server
    app.run(debug=True)
