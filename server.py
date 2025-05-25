from flask import Flask, request, send_file, jsonify
import os
import uuid
import random
import subprocess
import requests

app = Flask(__name__)

# Define brand-specific configurations
BRANDS = {
    "thick_asian": {
        "metadata": "brand=thick_asian",
        "lut": "Cobi_3.CUBE",
        "scroll_speed": 80,
        "captions_file": "thick_asian_captions.txt",
        "watermarks": [
            "Thick_asian_watermark.png",
            "Thick_asian_watermark_2.png",
            "Thick_asian_watermark_3.png"
        ]
    },
    "gym_baddie": {
        "metadata": "brand=gym_baddie",
        "lut": "GBW.CUBE",
        "scroll_speed": 120,
        "captions_file": "gym_baddie_captions.txt",
        "watermarks": [
            "gym_baddie_watermark.png",
            "gym_baddie_watermark_2.png"
        ]
    },
    "polishedform": {
        "metadata": "brand=polishedform",
        "lut": "minimal_lut.CUBE",
        "scroll_speed": 60,
        "captions_file": "polishedform_captions.txt",
        "watermarks": [
            "polishedform_watermark.png"
        ]
    }
}

@app.route('/process/<brand>', methods=['POST'])
def process_video(brand):
    if brand not in BRANDS:
        return "Invalid brand", 400

    # Parse JSON and download video
    data = request.get_json()
    if not data or "video_url" not in data:
        return "Missing 'video_url' in JSON", 400

    video_url = data["video_url"]
    try:
        video_data = requests.get(video_url, timeout=10)
        video_data.raise_for_status()
    except Exception as e:
        return f"Failed to download video: {str(e)}", 400

    # Save the video temporarily
    temp_id = str(uuid.uuid4())
    input_path = f"/tmp/{temp_id}.mp4"
    with open(input_path, "wb") as f:
        f.write(video_data.content)

    brand_config = BRANDS[brand]
    output_path = f"/tmp/{temp_id}_mid.mp4"

    # Random watermark
    wm_path = os.path.join("assets", random.choice(brand_config["watermarks"]))

    # Optional LUT
    lut_filter = f"lut3d='{brand_config['lut']}'" if brand_config.get("lut") else ""

    # Optional caption
    caption_text = ""
    caption_file = brand_config.get("captions_file")
    if caption_file and os.path.exists(caption_file):
        with open(caption_file, "r") as f:
            lines = f.readlines()
            caption_text = random.choice([line.strip() for line in lines if line.strip()])

    drawtext_filter = ""
    if caption_text:
        safe_caption = caption_text.replace(":", "\\:").replace("'", "\\'")
        drawtext_filter = (
            f"drawbox=y=0:x=0:w=iw:h=100:color=black@0.65:t=fill,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{safe_caption}':fontcolor=white:fontsize=36:"
            f"x=(w-text_w)/2:y=20:box=1:boxcolor=black@0.5:boxborderw=10,"
        )

    # Build full FFmpeg filter
    filter_complex = (
        f"[0:v]hflip,scale=1080:1920,setsar=1,"
        f"{drawtext_filter}"
        f"{lut_filter}[v];"
        f"movie='{wm_path}',scale=200:-1[wm];"
        f"[v][wm]overlay=W-w-30:H-h-30"
    )

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "faster",
        "-b:v", "10M",
        "-pix_fmt", "yuv420p",
        "-metadata", brand_config["metadata"],
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", "64k",
        "-shortest",
        output_path
    ]

    try:
        subprocess.run(ffmpeg_cmd, check=True)
    except subprocess.CalledProcessError as e:
        return f"FFmpeg error: {e}", 500

    return send_file(output_path, mimetype="video/mp4")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
