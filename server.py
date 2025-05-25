from flask import Flask, request, send_file
import subprocess
import os
import uuid
import random
import requests

app = Flask(__name__)

# Define brand settings
BRANDS = {
    "thick_asian": {
        "lut": "Cobi_3.CUBE",
        "captions_file": "thick_asian_captions.txt",
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ]
    },
    "gym_baddie": {
        "lut": "Cobi_3.CUBE",
        "captions_file": "gym_baddie_captions.txt",
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png",
            "gym_baddie_watermark_3.png"
        ]
    }
}

@app.route("/process/<brand>", methods=["POST"])
def process_video(brand):
    if brand not in BRANDS:
        return "Brand not supported", 400

    data = request.get_json()
    video_url = data.get("video_url")

    if not video_url:
        return "Missing video_url", 400

    # Save the video to disk
    input_path = f"/tmp/{uuid.uuid4()}.mp4"
    output_path = f"/tmp/{uuid.uuid4()}.mp4"

    try:
        r = requests.get(video_url, stream=True)
        r.raise_for_status()
        with open(input_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    except Exception as e:
        return f"Failed to download video: {str(e)}", 500

    config = BRANDS[brand]
    filters = []

    # Load caption
    caption = None
    if os.path.exists(config["captions_file"]):
        with open(config["captions_file"], "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            if lines:
                caption = random.choice(lines)

    if caption:
        caption_escaped = caption.replace(":", '\\:').replace("'", "\\'")
        filters.append(
            f"drawtext=text='{caption_escaped}':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=50:box=1:boxcolor=black@0.6"
        )

    # Watermark
    selected_watermark = random.choice(config["watermarks"])
    watermark_path = os.path.join("watermarks", selected_watermark)
    has_watermark = os.path.exists(watermark_path)

    cmd = ["ffmpeg", "-y", "-i", input_path]

    if has_watermark:
        cmd += ["-i", watermark_path]
        filters.append("overlay=W-w-10:H-h-10")

    if filters:
        cmd += ["-filter_complex", ";".join(filters)]

    cmd += [
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return send_file(output_path, as_attachment=True)
    except subprocess.CalledProcessError as e:
        return f"FFmpeg error: {e.stderr.decode()}", 500
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
