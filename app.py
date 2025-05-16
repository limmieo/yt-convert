import os
import uuid
import threading
import time
import subprocess
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, jsonify,
    send_from_directory
)

app = Flask(__name__)
app.secret_key = os.urandom(16)

# make sure this exists
os.makedirs("processed", exist_ok=True)

BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "lut": "Cobi_3.CUBE",
        "scroll_speed": 80,
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ]
    },
    "gym_baddie": {
        "metadata": "brand=gym_baddie",
        "lut": "Cobi_3.CUBE",
        "scroll_speed": 120,
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png",
            "gym_baddie_watermark_3.png"
        ]
    },
    "polishedform": {
        "metadata": "brand=polishedform",
        "lut": None,
        "scroll_speed": 80,
        "watermarks": [
            "polished_watermark.png",
            "polished_watermark_2.png",
            "polished_watermark_3.png"
        ]
    }
}

# In-memory storage for demo
_progress = {}   # task_id -> int percent
_results = {}    # task_id -> output filename


def _simulate_processing(task_id, video_url, brand):
    """
    Demo stub: sleeps & updates progress, but
    actually downloads the source URL into
    processed/<task_id>.mp4 so the file is non-empty.
    """
    for i in range(101):
        _progress[task_id] = i
        time.sleep(0.05)

    outname = f"{task_id}.mp4"
    outpath = os.path.join("processed", outname)

    # Try to fetch the real video; fallback to empty file on error
    try:
        subprocess.run([
            "wget", "-q", "--header=User-Agent:Mozilla/5.0",
            "-O", outpath, video_url
        ], check=True)
    except subprocess.CalledProcessError:
        # fallback so download link still works
        open(outpath, "wb").close()

    _results[task_id] = outname
    _progress[task_id] = 100


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", brands=BRANDS)


@app.route("/process", methods=["POST"])
def process_video():
    video_url = request.form.get("video_url", "").strip()
    brand     = request.form.get("brand", "")

    if not video_url:
        flash("Please enter a video URL.", "danger")
        return redirect(url_for("index"))
    if brand not in BRANDS:
        flash("Please select a valid brand.", "danger")
        return redirect(url_for("index"))

    task_id = str(uuid.uuid4())
    _progress[task_id] = 0

    thread = threading.Thread(
        target=_simulate_processing,
        args=(task_id, video_url, brand),
        daemon=True
    )
    thread.start()

    return render_template("processing.html", task_id=task_id)


@app.route("/progress/<task_id>")
def progress(task_id):
    pct      = _progress.get(task_id, 0)
    filename = _results.get(task_id)
    return jsonify(progress=pct, filename=filename)


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory("processed", filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
