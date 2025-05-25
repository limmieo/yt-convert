from flask import Flask, request, send_file
import subprocess
import uuid
import os
import random

app = Flask(__name__)

BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "lut": "Cobi_3.CUBE",
        "scroll_speed": 80,
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
        "scroll_speed": 100,
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png"
        ],
        "captions_file": "gym_baddie_captions.txt"
    },
    "polishedform": {
        "metadata": "brand=polishedform",
        "lut": "CineGreen.CUBE",
        "scroll_speed": 60,
        "watermarks": [
            "polishedform_mark.png",
            "polishedform_mark_alt.png"
        ],
        "captions_file": "polishedform_captions.txt"
    }
}

@app.route("/process/<brand>", methods=["POST"])
def process_video(brand):
    if brand not in BRANDS:
        return "Unknown brand", 400

    config = BRANDS[brand]
    file = request.files["video"]
    input_path = f"/tmp/{uuid.uuid4()}.mp4"
    output_path = f"/tmp/{uuid.uuid4()}.mp4"
    file.save(input_path)

    # Base filter chain (scale + pad + format + hflip)
    filter_chain = (
        "[0:v]scale=1080:-2:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
        "fifo,format=yuv420p,hflip[outv]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", input_path,
        "-filter_complex", filter_chain,
        "-map", "[outv]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-shortest",
        output_path
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1024:
            return "FFmpeg finished but output file is empty or corrupted.", 500

        return send_file(output_path, as_attachment=True)

    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode("utf-8") if e.stderr else "Unknown FFmpeg failure"
        return f"FFmpeg error:\n{error_message}", 500

    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
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
