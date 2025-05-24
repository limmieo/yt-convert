import os
import uuid
import random
import subprocess
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "captions_file": "thick_asian_captions.txt",
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ]
    },
    "gym_baddie": {
        "metadata": "brand=gym_baddie",
        "captions_file": "gym_baddie_captions.txt",
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png"
        ]
    }
}

@app.route("/process/<brand>", methods=["POST"])
def process(brand):
    if brand not in BRANDS:
        return jsonify({"error": "Invalid brand"}), 400

    if "video" not in request.files:
        return jsonify({"error": "No video file uploaded"}), 400

    video_file = request.files["video"]
    video_path = f"/tmp/{uuid.uuid4()}.mp4"
    video_file.save(video_path)

    # Pick watermark
    wm_filename = random.choice(BRANDS[brand]["watermarks"])
    watermark_path = f"/opt/render/project/src/assets/{wm_filename}"
    if not os.path.exists(watermark_path):
        return jsonify({"error": f"Watermark not found: {wm_filename}"}), 500

    # Pick caption
    captions_path = f"/opt/render/project/src/assets/{BRANDS[brand]['captions_file']}"
    if not os.path.exists(captions_path):
        return jsonify({"error": "Captions file not found"}), 500

    with open(captions_path, "r", encoding="utf-8") as f:
        captions = [line.strip() for line in f if line.strip()]
    caption_text = random.choice(captions) if captions else ""

    output_path = f"/tmp/{uuid.uuid4()}_mid.mp4"

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", watermark_path,
        "-filter_complex",
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=rgba[vid];"
        f"[1:v]scale=200:-1[wm];"
        f"[vid][wm]overlay=W-w-30:H-h-30,drawtext="
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"text='{caption_text}':fontcolor=white:fontsize=40:"
        f"box=1:boxcolor=black@0.5:boxborderw=10:x=(w-text_w)/2:y=h*0.1",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "FFmpeg processing failed"}), 500

    return send_file(output_path, mimetype="video/mp4")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
