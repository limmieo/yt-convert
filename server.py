from flask import Flask, request, send_file
import subprocess
import os
import uuid
import random
import requests

app = Flask(__name__)

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

    caption = ""
    if os.path.exists(config["captions_file"]):
        with open(config["captions_file"], "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            if lines:
                caption = random.choice(lines).replace(":", "\\:").replace("'", "\\'")

    selected_watermark = random.choice(config["watermarks"])
    watermark_path = os.path.join("watermarks", selected_watermark)
    has_watermark = os.path.exists(watermark_path)

    apply_flip_v = random.choice([True, False])
    apply_flip_h = random.choice([True, False])
    apply_lut = os.path.exists(config["lut"])
    lut_path = config["lut"]

    filters = []
    input_labels = ["[0:v]"]

    if has_watermark:
        input_labels.append("[1:v]")

    label = "[v0]"
    filters.append(f"{input_labels[0]}scale=w=1080:h=-1:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black{label}")

    if apply_flip_v:
        filters.append(f"{label}vflip[v1]")
        label = "[v1]"
    if apply_flip_h:
        filters.append(f"{label}hflip[v2]")
        label = "[v2]"
    if apply_lut:
        filters.append(f"{label}lut3d=file='{lut_path}'[v3]")
        label = "[v3]"
    if caption:
        filters.append(f"{label}drawtext=text='{caption}':fontcolor=white:fontsize=36:x=(w-text_w)/2:y=50:box=1:boxcolor=black@0.6[v4]")
        label = "[v4]"
    if has_watermark:
        filters.append(f"{label}[1:v]overlay=W-w-10:H-h-10[outv]")
    else:
        filters.append(f"{label}[outv]")

    cmd = ["ffmpeg", "-y", "-i", input_path]
    if has_watermark:
        cmd += ["-i", watermark_path]

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[outv]",
        "-map", "0:a?",  # keep original audio if available
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
        return f"FFmpeg error:\n{e.stderr.decode()}", 500
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
