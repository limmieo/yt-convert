import os
import random
import subprocess
import uuid
from flask import Flask, request, jsonify, send_file
import yaml

app = Flask(__name__)

with open("config/brands.yaml", "r") as f:
    BRANDS = yaml.safe_load(f)

@app.route("/process/<brand>", methods=["POST"])
def process_video(brand):
    data = request.get_json()
    video_url = data.get("video_url")

    if not video_url or brand not in BRANDS:
        return jsonify({"error": "Missing video_url or invalid brand"}), 400

    brand_config = BRANDS[brand]
    tmp_id = str(uuid.uuid4())
    input_path = f"/tmp/{tmp_id}.mp4"
    output_path = f"/tmp/{tmp_id}_mid.mp4"

    subprocess.run(["curl", "-L", "-o", input_path, video_url], check=True)

    watermark_path = os.path.join("assets", random.choice(brand_config["watermarks"]))
    captions_file = os.path.join("assets", brand_config["captions_file"])
    lut_path = os.path.join("assets", brand_config.get("lut", ""))

    try:
        with open(captions_file, "r", encoding="utf-8") as f:
            captions = [line.strip() for line in f if line.strip()]
        caption = random.choice(captions)
    except Exception:
        caption = ""

    # Base filters
    vf_filters = [
        f"drawtext=text='{caption}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=40:box=1:boxcolor=black@0.5:boxborderw=10",
        f"movie='{watermark_path}' [wm]; [in][wm] overlay=W-w-20:H-h-20 [out]"
    ]

    # LUT check
    if brand_config.get("lut"):
        try:
            subprocess.run(
                ["ffmpeg", "-f", "lavfi", "-i", "nullsrc", "-vf", f"lut3d='{lut_path}'", "-frames:v", "1", "-f", "null", "-"],
                capture_output=True, check=True
            )
            vf_filters.insert(0, f"lut3d='{lut_path}'")
        except Exception:
            pass

    ffmpeg_command = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex", ",".join(vf_filters),
        "-map", "[out]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-b:v", "10000k",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path
    ]

    try:
        subprocess.run(ffmpeg_command, check=True)
        return send_file(output_path, mimetype="video/mp4")
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "FFmpeg failed", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
