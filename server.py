import os
import random
import subprocess
import uuid
from flask import Flask, request, jsonify, send_file
import yaml

app = Flask(__name__)

# Load brand config from YAML
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

    # Download video
    subprocess.run(["curl", "-L", "-o", input_path, video_url], check=True)

    watermark_path = os.path.join("assets", random.choice(brand_config["watermarks"]))
    captions_file = os.path.join("assets", brand_config["captions_file"])
    lut_path = os.path.join("assets", brand_config.get("lut", ""))

    # Pick a random caption
    try:
        with open(captions_file, "r", encoding="utf-8") as f:
            captions = [line.strip() for line in f if line.strip()]
        caption = random.choice(captions)
    except Exception:
        caption = ""

    vf_filters = [
        "hflip",
        f"drawtext=text='{caption}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=30:borderw=2",
        f"movie='{watermark_path}' [watermark]; [in][watermark] overlay=W-w-20:H-h-20"
    ]

    # Try LUT filter, skip if broken
    if brand_config.get("lut"):
        try:
            test_lut = subprocess.run(
                ["ffmpeg", "-hide_banner", "-v", "error", "-f", "lavfi", "-i", f"color=black:size=1x1", "-vf", f"lut3d='{lut_path}'", "-frames:v", "1", "-f", "null", "-"],
                capture_output=True
            )
            if test_lut.returncode == 0:
                vf_filters.append(f"lut3d='{lut_path}'")
        except Exception:
            pass

    vf = ",".join(vf_filters)

    ffmpeg_command = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-b:v", "10000k",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path
    ]

    try:
        subprocess.run(ffmpeg_command, check=True)
        return send_file(output_path, mimetype="video/mp4")
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "FFmpeg processing failed", "detail": str(e)}), 500
    except Exception as e:
        return jsonify({"error": "Unexpected error", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
