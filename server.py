import os
import random
import uuid
import subprocess
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "lut": "Cobi_3.CUBE",
        "captions_file": "thick_asian_captions.txt",
        "scroll_speed": 80,
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ]
    },
    "gym_baddie": {
        "metadata": "brand=gym_baddie",
        "lut": "Cobi_1.CUBE",
        "captions_file": "gym_baddie_captions.txt",
        "scroll_speed": 120,
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png",
            "gym_baddie_watermark_3.png"
        ]
    },
    "polishedform": {
        "metadata": "brand=polishedform",
        "lut": "Cinematic.CUBE",
        "captions_file": "polishedform_captions.txt",
        "scroll_speed": 100,
        "watermarks": [
            "polishedform_w1.png",
            "polishedform_w2.png"
        ]
    }
}

@app.route('/process/<brand>', methods=['POST'])
def process_video(brand):
    if brand not in BRANDS:
        return "Invalid brand", 400

    input_file = request.files['file']
    input_path = f"/tmp/{uuid.uuid4()}.mp4"
    output_path = input_path.replace(".mp4", "_out.mp4")
    input_file.save(input_path)

    brand_config = BRANDS[brand]
    watermark_path = random.choice(brand_config["watermarks"])
    caption_path = brand_config["captions_file"]
    lut_path = brand_config["lut"]

    try:
        with open(caption_path, "r", encoding="utf-8") as f:
            captions = [line.strip() for line in f if line.strip()]
            selected_caption = random.choice(captions)
    except Exception as e:
        selected_caption = "Default Caption"

    drawtext_filter = f"drawtext=text='{selected_caption}':fontcolor=white:fontsize=36:box=1:boxcolor=black@0.8:boxborderw=10:x=(w-text_w)/2:y=20"

    ffmpeg_cmd = [
        "ffmpeg",
        "-i", input_path,
        "-i", f"assets/{watermark_path}",
        "-filter_complex",
        f"[0:v]hflip,format=yuv420p,lut3d=file='assets/{lut_path}',{drawtext_filter}[v];[v][1:v]overlay=W-w-20:H-h-20",
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "veryfast",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_path
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError as e:
        return f"FFmpeg failed: {e}", 500

    return send_file(output_path, mimetype="video/mp4")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
