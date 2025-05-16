import os
import uuid
import threading
import time
import subprocess
import random
import textwrap
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, jsonify,
    send_from_directory
)

app = Flask(__name__)
app.secret_key = os.urandom(16)

# ensure these dirs exist
os.makedirs("processed", exist_ok=True)
ASSETS = os.path.join(os.getcwd(), "assets")

BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "lut": "Cobi_3.CUBE",
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ],
        "captions_file": "thick_asian_captions.txt"
    },
    "gym_baddie": {
        "metadata": "brand=gym_baddie",
        "lut": "Cobi_3.CUBE",
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png",
            "gym_baddie_watermark_3.png"
        ],
        "captions_file": "gym_baddie_captions.txt"
    },
    "polishedform": {
        "metadata": "brand=polishedform",
        "lut": None,
        "watermarks": [
            "polished_watermark.png",
            "polished_watermark_2.png",
            "polished_watermark_3.png"
        ],
        "captions_file": "polishedform_captions.txt"
    }
}

_progress = {}   # task_id -> int
_results   = {}  # task_id -> filename

def wrap_caption(caption, width=30):
    lines = textwrap.wrap(caption, width)
    if len(lines) > 2:
        lines = [" ".join(lines[:-1]), lines[-1]]
    return "\\n".join(lines)

def _simulate_real_process(task_id, url, brand):
    """ Replace this stub with your real ffmpeg pipeline. """
    for i in range(101):
        _progress[task_id] = i
        time.sleep(0.03)
    out = f"{task_id}.mp4"
    open(os.path.join("processed", out), "wb").close()
    _results[task_id] = out

@app.route("/")
def index():
    return render_template("index.html", brands=BRANDS)

@app.route("/process", methods=["POST"])
def process_video():
    video_url = request.form.get("video_url","").strip()
    brand     = request.form.get("brand","")
    if not video_url:
        flash("Please enter a video URL.", "danger")
        return redirect(url_for("index"))
    if brand not in BRANDS:
        flash("Please select a valid brand.", "danger")
        return redirect(url_for("index"))

    task_id = str(uuid.uuid4())
    _progress[task_id] = 0

    # kick off processing in background
    thread = threading.Thread(
        target=_simulate_real_process,
        args=(task_id, video_url, brand),
        daemon=True
    )
    thread.start()

    return render_template("processing.html", task_id=task_id)

@app.route("/progress/<task_id>")
def progress(task_id):
    pct  = _progress.get(task_id, 0)
    file = _results.get(task_id)
    return jsonify(progress=pct, filename=file)

@app.route("/download/<filename>")
def download(filename):
    # will 404 if file not found
    return send_from_directory("processed", filename, as_attachment=True)

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    # on Windows, just: python app.py
    app.run(host="0.0.0.0", port=5000, debug=True)
